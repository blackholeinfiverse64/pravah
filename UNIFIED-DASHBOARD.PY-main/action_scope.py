"""Enforces action scope for the Pravah decision brain.

This module ensures that any decision emitted by the decision pipeline is within the
allowed set of actions for the given application/environment. Illegal actions are
downgraded to NOOP.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


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
    reason: Optional[str] = None
    context: Dict[str, Any] = None


# Allowed actions per environment.
# This is the central definition of what the decision brain is allowed to request.
# Add or remove actions here to change the permitted scope.
DEFAULT_ENVIRONMENT_ACTION_SCOPE = {
    "prod": {Action.SCALE_UP, Action.SCALE_DOWN, Action.ALERT},
    "staging": {Action.SCALE_UP, Action.SCALE_DOWN, Action.RESTART, Action.ALERT},
    "dev": {Action.SCALE_UP, Action.SCALE_DOWN, Action.RESTART, Action.ROLLBACK, Action.ALERT},
}


class ActionScopeEnforcer:
    def __init__(self, environment_action_scope: Optional[Dict[str, set[Action]]] = None):
        self.environment_action_scope = environment_action_scope or DEFAULT_ENVIRONMENT_ACTION_SCOPE

    def enforce(
        self,
        environment: str,
        action: Action,
        app_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EnforcementResult:
        """Enforce that the action is permitted in the given environment."""
        allowed = self.environment_action_scope.get(environment, set())
        action_allowed = action in allowed
        if action_allowed:
            return EnforcementResult(
                action_requested=action,
                action_allowed=True,
                action_emitted=action,
                context=context or {},
            )

        # Not allowed: downgrade to NOOP
        return EnforcementResult(
            action_requested=action,
            action_allowed=False,
            action_emitted=Action.NOOP,
            reason=f"Action {action.value} not allowed in environment {environment}",
            context=context or {},
        )
