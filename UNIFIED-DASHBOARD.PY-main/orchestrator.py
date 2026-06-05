"""Orchestrator communication client for the Pravah decision brain.

This module defines the interface used by the decision pipeline to deliver
validated decisions to the orchestrator. The orchestrator is expected to
acknowledge receipt.

In a real deployment this would be an HTTP client or a message bus publisher;
for the purposes of this integration, we provide a lightweight stub that can be
replaced with a real transport implementation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


@dataclass
class OrchestratorAck:
    acknowledged: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class OrchestratorClient:
    def __init__(
        self,
        endpoint_url: str = "http://localhost:8000/orchestrate",
        timeout_seconds: float = 5.0,
        transport: Optional[Any] = None,
    ):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def send_decision(self, decision_payload: Dict[str, Any]) -> OrchestratorAck:
        """Deliver a decision payload to the orchestrator.

        For integration testing, this method can be monkeypatched or the transport
        can be injected.
        """
        payload = json.dumps(decision_payload)
        logger.debug("Sending decision to orchestrator: %s", payload)

        # In a real system, this would be an HTTP POST (or similar) to the orchestrator.
        # Here, we simulate reliable delivery and acknowledgement.
        try:
            # If a mock transport is provided, use it (e.g., a function)
            if callable(self.transport):
                ok, message, details = self.transport(decision_payload)
                return OrchestratorAck(acknowledged=ok, message=message, details=details)

            # Default stub: always acknowledge.
            return OrchestratorAck(acknowledged=True, message="ACK (stub)", details={})
        except Exception as exc:
            logger.exception("Failed to send decision to orchestrator")
            return OrchestratorAck(acknowledged=False, message=str(exc), details={})
