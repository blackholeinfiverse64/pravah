"""RL-backed decision generator operating on Shivam's runtime signals.

Signals consumed: cpu_percent, memory_percent, health_score, restart_count, crashed.
"""
from __future__ import annotations

import logging
import time
from random import random
from typing import Tuple

from .action_scope import Action
from .schemas import RuntimePayload
from .state import AppStateStore

logger = logging.getLogger(__name__)

# Thresholds
CPU_HIGH   = 75.0
CPU_LOW    = 25.0
MEM_HIGH   = 80.0
HEALTH_LOW = 0.4
ALPHA      = 0.1   # Q-learning rate
GAMMA      = 0.9   # discount


def _bucket(p: RuntimePayload) -> str:
    if p.crashed:
        return "crashed"
    if p.health_score < HEALTH_LOW or p.restart_count >= 3:
        return "degraded"
    if p.cpu_percent >= CPU_HIGH or p.memory_percent >= MEM_HIGH:
        return "overloaded"
    if p.cpu_percent <= CPU_LOW:
        return "underloaded"
    return "normal"


class DecisionGenerator:
    def __init__(self, enable_rl: bool = True, explore_rate: float = 0.15):
        self.enable_rl = enable_rl
        self.explore_rate = explore_rate

    def _rules(self, p: RuntimePayload) -> Tuple[Action, str]:
        if p.crashed:
            return Action.RESTART, "rule:crashed"
        if p.health_score < HEALTH_LOW:
            return Action.RESTART, "rule:health_low"
        if p.restart_count >= 3:
            return Action.ROLLBACK, "rule:restart_count_high"
        if p.cpu_percent >= CPU_HIGH or p.memory_percent >= MEM_HIGH:
            return Action.SCALE_UP, "rule:resource_high"
        if p.cpu_percent <= CPU_LOW:
            return Action.SCALE_DOWN, "rule:resource_low"
        return Action.NOOP, "rule:healthy"

    def generate(self, payload: RuntimePayload, store: AppStateStore) -> Tuple[Action, str]:
        rule_action, rule_reason = self._rules(payload)

        if not self.enable_rl:
            return rule_action, rule_reason

        bucket = _bucket(payload)
        state = store.get(payload.deployment_id, payload.environment)
        q = state.rl_state.q_table.get(bucket, {})

        if random() < self.explore_rate or not q:
            return rule_action, f"rl:explore:{rule_reason}"

        best = max(q.items(), key=lambda x: x[1])[0]
        try:
            return Action(best), f"rl:exploit:{bucket}"
        except ValueError:
            return rule_action, rule_reason

    def update(
        self,
        payload: RuntimePayload,
        store: AppStateStore,
        action: Action,
        reward: float,
    ):
        if not self.enable_rl:
            return
        bucket = _bucket(payload)
        state = store.get(payload.deployment_id, payload.environment)
        table = state.rl_state.q_table.setdefault(bucket, {})
        old = table.get(action.value, 0.0)
        table[action.value] = old + ALPHA * (reward + GAMMA * max(table.values(), default=0.0) - old)
        state.rl_state.last_update = time.time()
        logger.debug(
            "[RL] Q-update deployment=%s bucket=%s action=%s reward=%.2f q=%.3f",
            payload.deployment_id, bucket, action.value, reward, table[action.value],
        )
