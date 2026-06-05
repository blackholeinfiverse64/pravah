"""Canonical decision pipeline for Pravah's decision brain.

This module defines the single pipeline that all decisions must pass through.
It is responsible for:
  1. Accepting runtime state from the control plane
  2. Normalizing it against the shared runtime contract
  3. Generating a decision (rule-based + optional RL augmentation)
  4. Enforcing action scope (downgrading illegal actions to NOOP)
  5. Relaying decisions to the orchestrator
  6. Recording state and feedback for learning (DEV only)

The pipeline is intentionally linear: there is one code path from input to output.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from action_scope import Action, ActionScopeEnforcer, EnforcementResult
from orchestrator import OrchestratorAck, OrchestratorClient
from schemas import RuntimePayload, ValidationError
from state import AppStateStore, DecisionOutcome


logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    decision_id: str
    app_id: str
    environment: str
    decision: Action
    action_allowed: bool
    orchestrator_acknowledged: Optional[bool]
    reason: str
    raw_payload: Dict[str, Any]
    action_requested: Action = Action.NOOP
    action_emitted: Action = Action.NOOP
    normalized_payload: Optional[RuntimePayload] = None
    enforcement: Optional[EnforcementResult] = None
    orchestrator_ack: Optional[OrchestratorAck] = None


class DecisionGenerator:
    """Generates decisions from normalized runtime state.

    This class combines deterministic rule-based logic with a simple
    reinforcement-learning-like state tracker. The RL component is purely
    advisory and is used only when enabled.
    """

    def __init__(
        self,
        enable_rl: bool = False,
        rl_explore_rate: float = 0.2,
        error_rate_threshold: float = 0.05,
        cpu_scale_up_threshold: float = 0.75,
        cpu_scale_down_threshold: float = 0.25,
    ):
        self.enable_rl = enable_rl
        self.rl_explore_rate = rl_explore_rate
        self.error_rate_threshold = error_rate_threshold
        self.cpu_scale_up_threshold = cpu_scale_up_threshold
        self.cpu_scale_down_threshold = cpu_scale_down_threshold

    def _rule_based_decision(self, state: RuntimePayload) -> Action:
        # Rule-based deterministic decisions.
        error_rate = state.signals.get("error_rate", 0.0)
        cpu = state.signals.get("cpu", 0.0)

        # Highest priority: severe alert -> restart
        if any(alert.severity.lower() == "critical" for alert in state.alerts):
            return Action.RESTART

        if error_rate and error_rate >= self.error_rate_threshold:
            return Action.RESTART

        if cpu >= self.cpu_scale_up_threshold:
            return Action.SCALE_UP

        if cpu <= self.cpu_scale_down_threshold:
            return Action.SCALE_DOWN

        return Action.NOOP

    def _rl_adjusted_decision(self, state: RuntimePayload, app_state: "AppStateStore") -> Action:
        from random import random

        # If not enough history to learn, fallback to rules.
        if not self.enable_rl:
            return self._rule_based_decision(state)

        if random() < self.rl_explore_rate:
            # Exploration: use the rule-based decision but allow occasional random action
            return self._rule_based_decision(state)

        # Exploitation: pick action with highest score for current signal bucket
        # For simplicity, bucket by whether cpu is high/low/ok.
        cpu = state.signals.get("cpu", 0.0)
        bucket = "high" if cpu >= self.cpu_scale_up_threshold else "low" if cpu <= self.cpu_scale_down_threshold else "normal"
        app = app_state.get_state(state.app_id, state.environment)
        q = app.rl_state.q_table.get(bucket, {})

        if not q:
            return self._rule_based_decision(state)

        best_action = max(q.items(), key=lambda it: it[1])[0]
        try:
            return Action(best_action)
        except ValueError:
            return self._rule_based_decision(state)

    def generate(self, state: RuntimePayload, app_state: AppStateStore) -> tuple[Action, str]:
        """Generate a decision for the normalized state.

        Returns a tuple of (action, reason)
        """
        # False-positive dampening: require repeated trigger for restart.
        if state.signals.get("error_rate", 0.0) >= self.error_rate_threshold:
            history = app_state.get_state(state.app_id, state.environment).history
            recent = [r for r in history if r.reason.startswith("rule:error_rate")]
            # Require 2 consecutive error_rate decisions before applying restart.
            if len(recent) < 2:
                return Action.NOOP, "rule:error_rate:dampened"

        decision = self._rl_adjusted_decision(state, app_state)
        reason = f"rule:{decision.value.lower()}"
        return decision, reason

    def update_rl_state(
        self,
        state: RuntimePayload,
        app_state: AppStateStore,
        decision: Action,
        reward: float,
    ):
        if not self.enable_rl:
            return
        cpu = state.signals.get("cpu", 0.0)
        bucket = "high" if cpu >= self.cpu_scale_up_threshold else "low" if cpu <= self.cpu_scale_down_threshold else "normal"
        app = app_state.get_state(state.app_id, state.environment)
        table = app.rl_state.q_table.setdefault(bucket, {})
        table[decision.value] = table.get(decision.value, 0.0) + reward
        app.rl_state.last_update = time.time()


class DecisionPipeline:
    """A canonical single decision pipeline for Pravah.

    This pipeline is the only path by which runtime state becomes actionable decisions.
    """

    def __init__(
        self,
        orchestrator: OrchestratorClient,
        action_scope_enforcer: ActionScopeEnforcer,
        app_state_store: AppStateStore,
        decision_generator: DecisionGenerator,
        enable_learning: bool = False,
    ):
        self.orchestrator = orchestrator
        self.action_scope_enforcer = action_scope_enforcer
        self.app_state_store = app_state_store
        self.decision_generator = decision_generator
        self.enable_learning = enable_learning

    def process_payload(self, payload: Dict[str, Any]) -> DecisionResult:
        decision_id = str(uuid.uuid4())
        result = DecisionResult(
            decision_id=decision_id,
            app_id="",
            environment="",
            decision=Action.NOOP,
            action_allowed=False,
            orchestrator_acknowledged=None,
            reason="",
            raw_payload=payload,
        )

        # 1) Normalize payload
        try:
            normalized = RuntimePayload.from_dict(payload)
            result.normalized_payload = normalized
            result.app_id = normalized.app_id
            result.environment = normalized.environment
            logger.debug(
                "Runtime payload normalized: app=%s env=%s signals=%s alerts=%s",
                normalized.app_id,
                normalized.environment,
                normalized.signals,
                [a.type for a in normalized.alerts],
            )
        except ValidationError as exc:
            result.reason = f"invalid payload: {exc}"
            logger.warning("Payload validation failed: %s", exc)
            return result

        # 2) Safety discipline: rate limiting
        if self.app_state_store.is_in_cooldown(normalized.app_id):
            result.reason = "rate limited: cooldown active"
            self.app_state_store.record_decision(
                normalized.app_id,
                normalized.environment,
                decision_id,
                Action.NOOP.value,
                DecisionOutcome.NOOP,
                result.reason,
                payload,
            )
            logger.info("Rate limiting applied for app=%s", normalized.app_id)
            return result

        # 3) Generate decision (rule / RL)
        decision, rule_reason = self.decision_generator.generate(normalized, self.app_state_store)
        result.action_requested = decision
        result.reason = rule_reason

        # 4) Enforce action scope
        enforcement = self.action_scope_enforcer.enforce(
            normalized.environment,
            decision,
            normalized.app_id,
            context={"signals": normalized.signals},
        )
        result.enforcement = enforcement
        result.action_allowed = enforcement.action_allowed
        if enforcement.action_emitted is None:
            enforcement_action = Action.NOOP
        else:
            enforcement_action = enforcement.action_emitted
        result.decision = enforcement_action
        result.action_emitted = enforcement_action

        logger.debug(
            "Action scope enforcement: requested=%s allowed=%s emitted=%s",
            enforcement.action_requested.value,
            enforcement.action_allowed,
            enforcement_action.value,
        )

        # 5) Relay to orchestrator
        orchestrator_payload = {
            "decision_id": decision_id,
            "app_id": normalized.app_id,
            "environment": normalized.environment,
            "action": enforcement_action.value,
            "requested_action": decision.value,
            "signals": normalized.signals,
            "timestamp": normalized.timestamp,
        }
        ack = self.orchestrator.send_decision(orchestrator_payload)
        result.orchestrator_ack = ack
        result.orchestrator_acknowledged = ack.acknowledged

        result.reason = (
            "enforced: action downgraded" if not enforcement.action_allowed else rule_reason
        )

        # 6) Record state (history + optional learning)
        outcome = DecisionOutcome.ACTION if enforcement_action != Action.NOOP else DecisionOutcome.NOOP
        self.app_state_store.record_decision(
            normalized.app_id,
            normalized.environment,
            decision_id,
            enforcement_action.value,
            outcome,
            result.reason,
            payload,
        )

        if self.enable_learning and enforcement_action != Action.NOOP:
            # In a real system, rewards come from observed outcomes.
            reward = 1.0 if ack.acknowledged else -1.0
            self.decision_generator.update_rl_state(normalized, self.app_state_store, enforcement_action, reward)

        logger.info(
            "decision_id=%s app_id=%s action_requested=%s action_emitted=%s orchestrator_acknowledged=%s allowed=%s reason=%s",
            decision_id,
            normalized.app_id,
            result.action_requested.value,
            result.action_emitted.value,
            ack.acknowledged,
            enforcement.action_allowed,
            result.reason,
        )
        return result
