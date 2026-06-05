"""Canonical decision pipeline — the single path from telemetry to orchestrator.

Loop:
  Control Plane Telemetry → Decision Brain → Guard Enforcement
  → Orchestrator Execution → Telemetry Verification → Learning Feedback
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .action_scope import Action, ActionGuard, EnforcementResult
from .orchestrator import ExecutionResult, OrchestratorClient
from .rl_engine import DecisionGenerator
from .schemas import RuntimePayload, ValidationError
from .state import AppStateStore, DecisionOutcome

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    decision_id: str
    deployment_id: str
    environment: str
    action: Action
    action_allowed: bool
    reason: str
    enforcement: Optional[EnforcementResult]
    execution: Optional[ExecutionResult]


class DecisionPipeline:
    """Single linear pipeline — no alternative code paths."""

    def __init__(
        self,
        orchestrator: OrchestratorClient,
        guard: ActionGuard,
        store: AppStateStore,
        generator: DecisionGenerator,
        enable_learning: bool = True,
    ):
        self.orchestrator = orchestrator
        self.guard = guard
        self.store = store
        self.generator = generator
        self.enable_learning = enable_learning

    def process(self, raw: Dict[str, Any]) -> DecisionResult:
        decision_id = str(uuid.uuid4())

        # ── 1. Normalize against runtime contract ──────────────────────────
        try:
            payload = RuntimePayload.from_dict(raw)
        except ValidationError as exc:
            logger.warning("[PIPELINE] invalid payload: %s", exc)
            return DecisionResult(
                decision_id=decision_id,
                deployment_id=raw.get("deployment_id", "unknown"),
                environment=raw.get("environment", "unknown"),
                action=Action.NOOP,
                action_allowed=False,
                reason=f"invalid_payload:{exc}",
                enforcement=None,
                execution=None,
            )

        dep_id = payload.deployment_id
        env    = payload.environment

        logger.info(
            "[TELEMETRY] deployment=%s env=%s cpu=%.1f mem=%.1f health=%.2f restarts=%d crashed=%s",
            dep_id, env,
            payload.cpu_percent, payload.memory_percent,
            payload.health_score, payload.restart_count, payload.crashed,
        )

        # ── 2. CooldownManager check ───────────────────────────────────────
        state = self.store.get(dep_id, env)
        if self.store.cooldown.is_cooling(state):
            logger.info("[COOLDOWN] deployment=%s still cooling → NOOP", dep_id)
            self.store.record(dep_id, env, decision_id, Action.NOOP.value, DecisionOutcome.NOOP, "cooldown")
            return DecisionResult(
                decision_id=decision_id,
                deployment_id=dep_id,
                environment=env,
                action=Action.NOOP,
                action_allowed=False,
                reason="cooldown",
                enforcement=None,
                execution=None,
            )

        # ── 3. Generate decision (RL + rules) ──────────────────────────────
        action, reason = self.generator.generate(payload, self.store)
        logger.info("[DECISION] deployment=%s action=%s reason=%s", dep_id, action.value, reason)

        # ── 4. ActionGuard + env autonomy gate ────────────────────────────
        enforcement = self.guard.enforce(env, action, dep_id, context={"cpu": payload.cpu_percent})
        final_action = enforcement.action_emitted  # always Action, never None

        if not enforcement.action_allowed:
            logger.info(
                "[GUARD] BLOCKED deployment=%s requested=%s → NOOP reason=%s",
                dep_id, action.value, enforcement.reason,
            )

        # ── 5. Transmit to orchestrator ────────────────────────────────────
        orch_payload = {
            "decision_id": decision_id,
            "deployment_id": dep_id,
            "environment": env,
            "action": final_action.value,
            "requested_action": action.value,
            "cpu_percent": payload.cpu_percent,
            "memory_percent": payload.memory_percent,
            "health_score": payload.health_score,
            "restart_count": payload.restart_count,
            "crashed": payload.crashed,
            "timestamp": payload.timestamp,
        }
        execution = self.orchestrator.execute(orch_payload)

        # ── 6. Record state ────────────────────────────────────────────────
        outcome = DecisionOutcome.ACTION if final_action != Action.NOOP else DecisionOutcome.NOOP
        self.store.record(dep_id, env, decision_id, final_action.value, outcome, reason)

        # ── 7. Reward learning feedback ────────────────────────────────────
        if self.enable_learning and final_action != Action.NOOP:
            reward = 1.0 if execution.success else -1.0
            self.generator.update(payload, self.store, final_action, reward)

        logger.info(
            "[RESULT] decision_id=%s deployment=%s action=%s allowed=%s orch_success=%s",
            decision_id, dep_id, final_action.value,
            enforcement.action_allowed, execution.success,
        )

        return DecisionResult(
            decision_id=decision_id,
            deployment_id=dep_id,
            environment=env,
            action=final_action,
            action_allowed=enforcement.action_allowed,
            reason=reason,
            enforcement=enforcement,
            execution=execution,
        )
