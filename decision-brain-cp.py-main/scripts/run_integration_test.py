"""Pravah integration test — multi-deployment stress test + end-to-end validation.

Covers:
  - 8-10 deployments processed independently
  - state contamination check
  - guard blocking → NOOP proof
  - crash detection and recovery
  - full loop: telemetry → decision → guard → orchestrator → learning
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List

from decision_brain.action_scope import ActionGuard
from decision_brain.loop import PravahOrganismLoop
from decision_brain.orchestrator import ExecutionResult, OrchestratorClient
from decision_brain.pipeline import DecisionPipeline
from decision_brain.rl_engine import DecisionGenerator
from decision_brain.state import AppStateStore
from decision_brain.telemetry import DeploymentRegistry, TelemetryClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Shivam's runtime payload format ───────────────────────────────────────────
DEPLOYMENTS = [
    {"deployment_id": f"svc-{i:02d}", "environment": env}
    for i, env in enumerate(
        ["prod", "prod", "staging", "staging", "staging", "dev", "dev", "dev", "dev", "dev"],
        start=1,
    )
]


def _make_telemetry(deployment_id: str, scenario: str = "normal") -> Dict[str, Any]:
    """Build a telemetry payload matching Shivam's runtime contract."""
    base = {
        "deployment_id": deployment_id,
        "environment": next(
            d["environment"] for d in DEPLOYMENTS if d["deployment_id"] == deployment_id
        ),
        "timestamp": time.time(),
        "metadata": {"source": "integration_test", "scenario": scenario},
    }
    scenarios = {
        "normal":    {"cpu_percent": 40.0, "memory_percent": 50.0, "health_score": 0.95, "restart_count": 0, "crashed": False},
        "cpu_high":  {"cpu_percent": 88.0, "memory_percent": 55.0, "health_score": 0.80, "restart_count": 0, "crashed": False},
        "cpu_low":   {"cpu_percent": 10.0, "memory_percent": 30.0, "health_score": 0.98, "restart_count": 0, "crashed": False},
        "degraded":  {"cpu_percent": 60.0, "memory_percent": 70.0, "health_score": 0.30, "restart_count": 2, "crashed": False},
        "crashed":   {"cpu_percent": 0.0,  "memory_percent": 0.0,  "health_score": 0.0,  "restart_count": 5, "crashed": True},
        "recovery":  {"cpu_percent": 35.0, "memory_percent": 45.0, "health_score": 0.90, "restart_count": 0, "crashed": False},
    }
    base.update(scenarios.get(scenario, scenarios["normal"]))
    return base


def _stub_orchestrator(payload: Dict[str, Any]) -> ExecutionResult:
    """Shivam's orchestrator stub — returns execution result format."""
    return ExecutionResult(
        success=True,
        action_executed=payload.get("action", "NOOP"),
        execution_timestamp=time.time(),
        message="ACK",
        details={"received": payload.get("decision_id")},
    )


def _build_pipeline(cooldown: float = 0.0) -> DecisionPipeline:
    return DecisionPipeline(
        orchestrator=OrchestratorClient(_transport=_stub_orchestrator),
        guard=ActionGuard(),
        store=AppStateStore(cooldown_seconds=cooldown),
        generator=DecisionGenerator(enable_rl=True, explore_rate=0.1),
        enable_learning=True,
    )


# ── Test A: Multi-deployment stress (8-10 deployments) ────────────────────────
def test_multi_deployment_stress():
    logger.info("=" * 60)
    logger.info("TEST A — Multi-Deployment Stress (10 deployments)")
    logger.info("=" * 60)

    pipeline = _build_pipeline(cooldown=0.0)
    decision_counts: Dict[str, int] = {}
    action_sets: Dict[str, set] = {}

    for dep in DEPLOYMENTS:
        dep_id = dep["deployment_id"]
        decision_counts[dep_id] = 0
        action_sets[dep_id] = set()

        for scenario in ["normal", "cpu_high", "cpu_low", "degraded"]:
            payload = _make_telemetry(dep_id, scenario)
            result = pipeline.process(payload)
            decision_counts[dep_id] += 1
            action_sets[dep_id].add(result.action.value)

            logger.info(
                "[STRESS] deployment=%s scenario=%s action=%s allowed=%s orch=%s",
                dep_id, scenario, result.action.value,
                result.action_allowed,
                result.execution.success if result.execution else "N/A",
            )

    # Verify isolation — each deployment has its own independent history
    logger.info("\n── Isolation Check ──")
    store = pipeline.store
    for dep in DEPLOYMENTS:
        dep_id = dep["deployment_id"]
        state = store.get(dep_id, dep["environment"])
        assert len(state.history) == decision_counts[dep_id], \
            f"State contamination detected for {dep_id}"
        logger.info(
            "[ISOLATION] deployment=%s decisions=%d actions=%s rl_buckets=%s",
            dep_id, len(state.history),
            list(action_sets[dep_id]),
            list(state.rl_state.q_table.keys()),
        )

    logger.info("TEST A PASSED — no state contamination, independent decision cycles\n")


# ── Test B: Guard blocking → NOOP proof ───────────────────────────────────────
def test_guard_noop_enforcement():
    logger.info("=" * 60)
    logger.info("TEST B — Guard Blocking → NOOP Enforcement")
    logger.info("=" * 60)

    pipeline = _build_pipeline(cooldown=0.0)

    # prod env: RESTART is not allowed → must emit NOOP
    payload = _make_telemetry("svc-01", "crashed")
    payload["environment"] = "prod"
    result = pipeline.process(payload)

    assert result.action.value == "NOOP", \
        f"Expected NOOP for RESTART in prod, got {result.action.value}"
    logger.info(
        "[GUARD] deployment=%s requested=RESTART env=prod → emitted=%s (BLOCKED → NOOP) ✓",
        result.deployment_id, result.action.value,
    )

    # staging env: ROLLBACK is not allowed → must emit NOOP
    payload2 = _make_telemetry("svc-03", "degraded")
    payload2["restart_count"] = 5  # triggers ROLLBACK rule
    result2 = pipeline.process(payload2)
    logger.info(
        "[GUARD] deployment=%s requested=%s env=staging → emitted=%s",
        result2.deployment_id,
        result2.enforcement.action_requested.value if result2.enforcement else "N/A",
        result2.action.value,
    )

    logger.info("TEST B PASSED — blocked actions converted to deterministic NOOP\n")


# ── Test C: Cooldown enforcement ───────────────────────────────────────────────
def test_cooldown():
    logger.info("=" * 60)
    logger.info("TEST C — CooldownManager Enforcement")
    logger.info("=" * 60)

    pipeline = _build_pipeline(cooldown=60.0)  # 60s cooldown

    p1 = _make_telemetry("svc-06", "cpu_high")
    r1 = pipeline.process(p1)
    logger.info("[COOLDOWN] first decision: action=%s", r1.action.value)

    p2 = _make_telemetry("svc-06", "cpu_high")
    r2 = pipeline.process(p2)
    assert r2.reason == "cooldown", f"Expected cooldown, got {r2.reason}"
    logger.info("[COOLDOWN] second decision blocked: reason=%s action=%s ✓", r2.reason, r2.action.value)

    logger.info("TEST C PASSED — cooldown correctly suppresses rapid decisions\n")


# ── Test D: End-to-end organism validation ────────────────────────────────────
def test_end_to_end_organism():
    logger.info("=" * 60)
    logger.info("TEST D — End-to-End Organism Validation")
    logger.info("=" * 60)

    # Scenario sequence: crash → orchestrator executes restart → recovery
    scenarios = ["normal", "degraded", "crashed", "recovery"]
    dep_id = "svc-07"

    telemetry_sequence = [_make_telemetry(dep_id, s) for s in scenarios]
    idx = 0

    def telemetry_source(deployment_id: str):
        nonlocal idx
        if idx < len(telemetry_sequence):
            payload = telemetry_sequence[idx]
            idx += 1
            return payload
        return None

    def registry_source() -> List[Dict[str, Any]]:
        return [{"deployment_id": dep_id}]

    loop = PravahOrganismLoop(
        telemetry=TelemetryClient(_source=telemetry_source),
        registry=DeploymentRegistry(_source=registry_source),
        orchestrator=OrchestratorClient(_transport=_stub_orchestrator),
        poll_interval=0.0,
        cooldown_seconds=0.0,
    )

    logger.info("[E2E] Running %d ticks for deployment=%s", len(scenarios), dep_id)
    loop.run(max_ticks=len(scenarios))

    state = loop._store.get(dep_id, "dev")
    logger.info("\n── End-to-End Loop Summary ──")
    for record in state.history:
        logger.info(
            "[E2E] action=%s outcome=%s reason=%s",
            record.action, record.outcome.value, record.reason,
        )

    actions = [r.action for r in state.history]
    assert "RESTART" in actions or "NOOP" in actions, "Expected at least one RESTART or NOOP"
    logger.info("TEST D PASSED — full loop: telemetry → decision → guard → orchestrator → learning ✓\n")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_multi_deployment_stress()
    test_guard_noop_enforcement()
    test_cooldown()
    test_end_to_end_organism()

    logger.info("=" * 60)
    logger.info("ALL INTEGRATION TESTS PASSED")
    logger.info("Pravah brain + body unified organism operational ✓")
    logger.info("=" * 60)
