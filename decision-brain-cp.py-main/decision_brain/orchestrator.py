"""Orchestrator client — wired to Shivam's orchestrator execution endpoints.

Sends validated decisions and returns execution results containing:
    success, action_executed, execution_timestamp
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Shivam's orchestrator execution endpoint
ORCHESTRATOR_ENDPOINT = "http://localhost:8000/orchestrate"


@dataclass
class ExecutionResult:
    success: bool
    action_executed: str
    execution_timestamp: float
    message: str
    details: Dict[str, Any]


class OrchestratorClient:
    """HTTP client for Shivam's orchestrator execution layer."""

    def __init__(
        self,
        endpoint: str = ORCHESTRATOR_ENDPOINT,
        timeout: float = 5.0,
        _transport=None,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self._transport = _transport  # injectable for testing

    def execute(self, decision_payload: Dict[str, Any]) -> ExecutionResult:
        """Transmit decision to orchestrator immediately after guard validation.

        Returns ExecutionResult with success, action_executed, execution_timestamp.
        """
        ts = time.time()
        action = decision_payload.get("action", "NOOP")

        logger.info(
            "[ORCHESTRATOR] → sending decision_id=%s deployment=%s action=%s",
            decision_payload.get("decision_id"),
            decision_payload.get("deployment_id"),
            action,
        )

        if callable(self._transport):
            result = self._transport(decision_payload)
            logger.info(
                "[ORCHESTRATOR] ← ack decision_id=%s success=%s action_executed=%s ts=%s",
                decision_payload.get("decision_id"),
                result.success,
                result.action_executed,
                result.execution_timestamp,
            )
            return result

        # Real HTTP POST to Shivam's orchestrator
        try:
            body = json.dumps(decision_payload).encode()
            req = urllib.request.Request(
                self.endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = json.loads(resp.read().decode())
                result = ExecutionResult(
                    success=raw.get("success", True),
                    action_executed=raw.get("action_executed", action),
                    execution_timestamp=raw.get("execution_timestamp", ts),
                    message=raw.get("message", "OK"),
                    details=raw,
                )
        except (urllib.error.URLError, Exception) as exc:
            logger.warning("[ORCHESTRATOR] HTTP failed (%s) — recording as executed", exc)
            result = ExecutionResult(
                success=False,
                action_executed=action,
                execution_timestamp=ts,
                message=str(exc),
                details={},
            )

        logger.info(
            "[ORCHESTRATOR] ← ack decision_id=%s success=%s action_executed=%s ts=%.3f",
            decision_payload.get("decision_id"),
            result.success,
            result.action_executed,
            result.execution_timestamp,
        )
        return result
