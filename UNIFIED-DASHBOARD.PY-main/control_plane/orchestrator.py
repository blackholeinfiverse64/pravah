"""Control plane orchestrator for executing infrastructure actions.

This module receives decisions from the decision engine and executes them
on the infrastructure. In a real deployment, this would integrate with
Kubernetes, Docker Swarm, AWS ECS, etc.
"""

import logging
import time
from typing import Dict, Any
from dataclasses import dataclass
from .telemetry_collector import TelemetryCollector

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    success: bool
    message: str
    details: Dict[str, Any]


class Orchestrator:
    """Executes infrastructure actions based on decisions."""

    def __init__(self, telemetry_collector: TelemetryCollector):
        self.telemetry = telemetry_collector
        self.execution_history = []

    def execute_action(self, decision_payload: Dict[str, Any]) -> ExecutionResult:
        """Execute an action based on the decision payload."""
        decision_id = decision_payload.get("decision_id")
        app_id = decision_payload.get("app_id")
        action = decision_payload.get("action")
        requested_action = decision_payload.get("requested_action")

        logger.info(f"Executing action: {action} for app {app_id}, decision {decision_id}")

        try:
            if action == "SCALE_UP":
                # Increase replicas by 1
                current = self.telemetry.apps[app_id]["replicas"]
                new_count = current + 1
                self.telemetry.update_replicas(app_id, new_count)
                message = f"Scaled up {app_id} from {current} to {new_count} replicas"
                success = True

            elif action == "SCALE_DOWN":
                # Decrease replicas by 1, minimum 1
                current = self.telemetry.apps[app_id]["replicas"]
                new_count = max(1, current - 1)
                self.telemetry.update_replicas(app_id, new_count)
                message = f"Scaled down {app_id} from {current} to {new_count} replicas"
                success = True

            elif action == "RESTART":
                # Simulate restart
                message = f"Restarted {app_id}"
                success = True

            elif action == "NOOP":
                message = f"No action taken for {app_id}"
                success = True

            else:
                message = f"Unknown action: {action}"
                success = False

            # Record execution
            execution_record = {
                "decision_id": decision_id,
                "app_id": app_id,
                "action": action,
                "requested_action": requested_action,
                "timestamp": time.time(),
                "success": success,
                "message": message
            }
            self.execution_history.append(execution_record)

            return ExecutionResult(
                success=success,
                message=message,
                details=execution_record
            )

        except Exception as e:
            logger.error(f"Failed to execute action {action} for {app_id}: {e}")
            return ExecutionResult(
                success=False,
                message=str(e),
                details={"decision_id": decision_id, "error": str(e)}
            )

    def get_execution_history(self, app_id: str = None) -> list:
        """Get execution history, optionally filtered by app."""
        if app_id:
            return [h for h in self.execution_history if h["app_id"] == app_id]
        return self.execution_history

    def get_last_execution(self, app_id: str) -> Dict[str, Any]:
        """Get the last execution for an app."""
        history = self.get_execution_history(app_id)
        return history[-1] if history else {}