"""Action scope enforcement — environment autonomy gates.

Blocked actions are always emitted as NOOP (never None).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Set


class Action(Enum):
    NOOP = "NOOP"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"
    RESTART = "RESTART"
    ROLLBACK = "ROLLBACK"
    ALERT = "ALERT"


@dataclass(frozen=True)
class EnforcementResult:
    action_requested: Action
    action_allowed: bool
    action_emitted: Action
    reason: str = ""
    context: Dict[str, Any] = field(default_factory=dict)


# Environment autonomy gates — central policy definition
ENV_ACTION_SCOPE: Dict[str, Set[Action]] = {
    "prod":    {Action.SCALE_UP, Action.SCALE_DOWN, Action.ALERT},
    "staging": {Action.SCALE_UP, Action.SCALE_DOWN, Action.RESTART, Action.ALERT},
    "dev":     {Action.SCALE_UP, Action.SCALE_DOWN, Action.RESTART, Action.ROLLBACK, Action.ALERT},
}


class ActionGuard:
    """Enforces environment autonomy gates. Blocked → NOOP (never None)."""

    def __init__(self, scope: Optional[Dict[str, Set[Action]]] = None):
        self._scope = scope or ENV_ACTION_SCOPE

    def enforce(
        self,
        environment: str,
        action: Action,
        deployment_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EnforcementResult:
        allowed_set = self._scope.get(environment, set())
        ctx = context or {}

        if action in allowed_set:
            return EnforcementResult(
                action_requested=action,
                action_allowed=True,
                action_emitted=action,
                reason="allowed",
                context=ctx,
            )

        return EnforcementResult(
            action_requested=action,
            action_allowed=False,
            action_emitted=Action.NOOP,
            reason=f"{action.value} blocked in {environment} → NOOP",
            context=ctx,
        )
