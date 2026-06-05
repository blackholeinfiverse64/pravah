"""Phase 5 recovery validation for restart determinism."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from control_plane.persistence.append_only_log import AppendOnlyLog
from control_plane.persistence.hash_lineage_verifier import HashLineageVerifier
from control_plane.persistence.replay_index import ReplayIndex, SnapshotRegistry
from control_plane.security.semantic_guard_engine import get_semantic_guard

from .deployment_proof import DeploymentProofPacket
from .startup_validator import DeploymentPaths


@dataclass(frozen=True)
class RecoveryValidationResult:
    execution_id: str
    ready: bool
    status: str
    journal_records: int
    state_hash: Optional[str]
    failures: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class RecoveryValidator:
    """Validate boot-time recovery against journal, index, and snapshots."""

    def __init__(self, paths: DeploymentPaths | None = None, proof_packet: DeploymentProofPacket | None = None):
        self.paths = paths or DeploymentPaths()
        self.proof_packet = proof_packet or DeploymentProofPacket()
        self.verifier = HashLineageVerifier()

    def validate(self, execution_id: str, expected_state_hash: str | None = None) -> RecoveryValidationResult:
        failures: List[str] = []
        journal_events = self._load_events(execution_id)
        self.proof_packet.record(
            "recovery",
            "recovery_replay_started",
            execution_id=execution_id,
            journal_records=len(journal_events),
        )

        if not journal_events:
            failures.append("journal_missing_or_empty")
            return self._failed_result(execution_id, failures, journal_records=0, state_hash=None)

        sequence_ok, sequence_error_seq, sequence_error = self.verifier.verify_sequence_continuity(journal_events)
        chain_ok, chain_error_seq, chain_error = self.verifier.verify_hash_chain(journal_events)
        verification_is_valid = sequence_ok and chain_ok
        self.proof_packet.record(
            "hash",
            "recovery_hash_verified",
            execution_id=execution_id,
            result="PASS" if verification_is_valid else "FAIL",
            status="VALID" if verification_is_valid else "HASH_CHAIN_ERROR",
            events_verified=len(journal_events) if verification_is_valid else (sequence_error_seq or chain_error_seq or 0),
            error_detail=None if verification_is_valid else (sequence_error or chain_error),
        )
        if not verification_is_valid:
            failures.append("hash_verification_failed:HASH_CHAIN")
            return self._failed_result(execution_id, failures, journal_records=len(journal_events), state_hash=None)

        replay_index = ReplayIndex(index_path=str(self.paths.replay_index_path))
        index_entry = replay_index.get_execution(execution_id)
        # If index missing, attempt to rebuild from journal events and persist
        if index_entry is None:
            try:
                if journal_events:
                    first_hash = journal_events[0].get("event_hash")
                    last_hash = journal_events[-1].get("event_hash")
                    last_ts = journal_events[-1].get("timestamp") or 0
                    source_ids = list({e.get("source") for e in journal_events if e.get("source")})
                    index_entry = replay_index.update_execution(
                        execution_id=execution_id,
                        start_sequence=journal_events[0].get("sequence", 1),
                        end_sequence=journal_events[-1].get("sequence", len(journal_events)),
                        event_count=len(journal_events),
                        first_event_hash=first_hash,
                        last_event_hash=last_hash,
                        last_timestamp=last_ts,
                        source_ids=source_ids,
                    )
            except Exception:
                index_entry = None

        if index_entry is None:
            failures.append("replay_index_missing")
        else:
            if index_entry.event_count != len(journal_events):
                failures.append("replay_index_event_count_mismatch")
            if journal_events[-1].get("event_hash") != index_entry.last_event_hash:
                failures.append("replay_index_last_hash_mismatch")

        snapshots = SnapshotRegistry(registry_path=str(self.paths.snapshot_directory.parent / "snapshot_registry.json"))
        snapshot = snapshots.get_latest_snapshot(execution_id)

        replay_events = [
            {
                "sequence": event.get("sequence"),
                "execution_id": event.get("execution_id"),
                "event_id": event.get("event_id"),
                "state": event.get("state"),
                "timestamp": event.get("timestamp"),
                "event_hash": event.get("event_hash"),
                "previous_hash": event.get("previous_hash"),
                "source": event.get("source"),
                "details": event.get("details") or {},
                "sequence_hash": event.get("sequence_hash"),
                "lineage_proof": event.get("lineage_proof"),
            }
            for event in journal_events
        ]

        semantic_guard = get_semantic_guard()
        semantic_violation = semantic_guard.validate_replay_chain(execution_id, replay_events)
        self.proof_packet.record(
            "replay",
            "recovery_replay_reconstructed",
            execution_id=execution_id,
            result="PASS" if semantic_violation is None else "FAIL",
            replay_events=len(replay_events),
            semantic_violation=None if semantic_violation is None else semantic_violation.to_dict(),
        )
        if semantic_violation is not None:
            failures.append(f"semantic_replay_failed:{semantic_violation.violation_type.value}")

        state_hash = self.verifier.compute_execution_state_hash(journal_events)
        hash_target = expected_state_hash or (snapshot.state_hash if snapshot else None)
        if hash_target is not None and state_hash != hash_target:
            failures.append("state_hash_mismatch")

        self.proof_packet.record(
            "recovery",
            "recovery_completed",
            execution_id=execution_id,
            result="PASS" if not failures else "FAIL",
            state_hash=state_hash,
            expected_state_hash=hash_target,
            failures=failures,
        )

        return self._final_result(
            execution_id=execution_id,
            failures=failures,
            journal_records=len(journal_events),
            state_hash=state_hash,
            snapshot_state_hash=snapshot.state_hash if snapshot else None,
            replay_index_loaded=index_entry is not None,
        )

    def _load_events(self, execution_id: str) -> List[Dict[str, Any]]:
        journal = AppendOnlyLog(log_path=str(self.paths.append_only_log_path))
        events = journal.get_execution_events(execution_id)
        return [
            {
                "sequence": event.sequence,
                "execution_id": event.execution_id,
                "event_id": event.event_id,
                "state": event.state,
                "timestamp": event.timestamp,
                "event_hash": event.event_hash,
                "previous_hash": event.previous_hash,
                "source": event.source,
                "details": event.details,
                "sequence_hash": event.sequence_hash,
                "lineage_proof": event.lineage_proof,
            }
            for event in events
        ]

    def _failed_result(self, execution_id: str, failures: List[str], journal_records: int, state_hash: Optional[str]) -> RecoveryValidationResult:
        return self._final_result(
            execution_id=execution_id,
            failures=failures,
            journal_records=journal_records,
            state_hash=state_hash,
            snapshot_state_hash=None,
            replay_index_loaded=False,
        )

    def _final_result(
        self,
        *,
        execution_id: str,
        failures: List[str],
        journal_records: int,
        state_hash: Optional[str],
        snapshot_state_hash: Optional[str],
        replay_index_loaded: bool,
    ) -> RecoveryValidationResult:
        ready = not failures
        status = "READY" if ready else "RECOVERY_FAILED"
        return RecoveryValidationResult(
            execution_id=execution_id,
            ready=ready,
            status=status,
            journal_records=journal_records,
            state_hash=state_hash,
            failures=failures,
            details={
                "append_only_log_path": str(self.paths.append_only_log_path),
                "replay_index_path": str(self.paths.replay_index_path),
                "snapshot_state_hash": snapshot_state_hash,
                "replay_index_loaded": replay_index_loaded,
            },
        )