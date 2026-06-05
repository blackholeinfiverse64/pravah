"""Per-application state management for the Pravah decision brain.

This module manages isolation between applications, ensuring that decision history
and RL state are tracked per application with memory caps and garbage collection.
"""

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
    payload: Dict[str, Any]


@dataclass
class RLState:
    # Simple table mapping (signal_state) -> action counts.
    q_table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)


@dataclass
class AppState:
    app_id: str
    environment: str
    history: List[DecisionRecord] = field(default_factory=list)
    rl_state: RLState = field(default_factory=RLState)
    last_decision_time: float = field(default_factory=lambda: 0.0)


class AppStateStore:
    """Store per-application state with caps and garbage collection."""

    def __init__(
        self,
        max_history_per_app: int = 100,
        stale_seconds: int = 60 * 60,
        decision_cooldown_seconds: float = 15.0,
    ):
        self._store: Dict[str, AppState] = {}
        self.max_history_per_app = max_history_per_app
        self.stale_seconds = stale_seconds
        self.decision_cooldown_seconds = decision_cooldown_seconds

    def get_state(self, app_id: str, environment: str) -> AppState:
        if app_id not in self._store:
            self._store[app_id] = AppState(app_id=app_id, environment=environment)
        state = self._store[app_id]
        # If environment changes, update it.
        if state.environment != environment:
            state.environment = environment
        return state

    def record_decision(
        self,
        app_id: str,
        environment: str,
        decision_id: str,
        action: str,
        outcome: DecisionOutcome,
        reason: str,
        payload: Dict[str, Any],
    ):
        state = self.get_state(app_id, environment)
        state.last_decision_time = time.time()
        record = DecisionRecord(
            timestamp=state.last_decision_time,
            decision_id=decision_id,
            action=action,
            outcome=outcome,
            reason=reason,
            payload=payload,
        )
        state.history.append(record)
        # Enforce history cap
        if len(state.history) > self.max_history_per_app:
            state.history = state.history[-self.max_history_per_app :]

    def is_in_cooldown(self, app_id: str) -> bool:
        state = self._store.get(app_id)
        if not state:
            return False
        elapsed = time.time() - state.last_decision_time
        return elapsed < self.decision_cooldown_seconds

    def garbage_collect(self):
        """Remove application state that has not been updated recently."""
        now = time.time()
        stale_apps = [
            app_id
            for app_id, state in self._store.items()
            if now - state.last_decision_time > self.stale_seconds
        ]
        for app_id in stale_apps:
            del self._store[app_id]

    def get_active_app_ids(self) -> List[str]:
        return list(self._store.keys())
