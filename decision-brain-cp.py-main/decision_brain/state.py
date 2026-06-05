"""Per-deployment state isolation and cooldown management."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DecisionOutcome(Enum):
    NOOP = "NOOP"
    ACTION = "ACTION"


@dataclass
class DecisionRecord:
    timestamp: float
    decision_id: str
    action: str
    outcome: DecisionOutcome
    reason: str


@dataclass
class RLState:
    q_table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)


@dataclass
class DeploymentState:
    deployment_id: str
    environment: str
    history: List[DecisionRecord] = field(default_factory=list)
    rl_state: RLState = field(default_factory=RLState)
    last_decision_time: float = 0.0


class CooldownManager:
    """Prevents bursty decision loops per deployment."""

    def __init__(self, cooldown_seconds: float = 15.0):
        self._cooldown = cooldown_seconds

    def is_cooling(self, state: DeploymentState) -> bool:
        return (time.time() - state.last_decision_time) < self._cooldown


class AppStateStore:
    """Isolated state store — one DeploymentState per deployment_id."""

    def __init__(
        self,
        max_history: int = 100,
        stale_seconds: int = 3600,
        cooldown_seconds: float = 15.0,
    ):
        self._store: Dict[str, DeploymentState] = {}
        self._max_history = max_history
        self._stale_seconds = stale_seconds
        self.cooldown = CooldownManager(cooldown_seconds)

    def get(self, deployment_id: str, environment: str) -> DeploymentState:
        if deployment_id not in self._store:
            self._store[deployment_id] = DeploymentState(
                deployment_id=deployment_id, environment=environment
            )
        return self._store[deployment_id]

    def record(
        self,
        deployment_id: str,
        environment: str,
        decision_id: str,
        action: str,
        outcome: DecisionOutcome,
        reason: str,
    ):
        state = self.get(deployment_id, environment)
        state.last_decision_time = time.time()
        state.history.append(
            DecisionRecord(
                timestamp=state.last_decision_time,
                decision_id=decision_id,
                action=action,
                outcome=outcome,
                reason=reason,
            )
        )
        if len(state.history) > self._max_history:
            state.history = state.history[-self._max_history:]

    def gc(self):
        now = time.time()
        stale = [
            k for k, v in self._store.items()
            if now - v.last_decision_time > self._stale_seconds
        ]
        for k in stale:
            del self._store[k]

    def active_ids(self) -> List[str]:
        return list(self._store.keys())
