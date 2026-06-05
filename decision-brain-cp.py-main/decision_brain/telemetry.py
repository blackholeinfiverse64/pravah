"""Telemetry client — consumes Shivam's runtime telemetry signals.

Replaces any direct polling. The decision brain reads real infrastructure
metrics through this client: cpu_percent, memory_percent, health_score,
restart_count, crashed.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Shivam's telemetry and deployment registry endpoints
TELEMETRY_ENDPOINT = "http://localhost:8000/telemetry"
REGISTRY_ENDPOINT  = "http://localhost:8000/deployments"


class TelemetryClient:
    """Reads runtime telemetry from Shivam's monitoring layer."""

    def __init__(
        self,
        telemetry_url: str = TELEMETRY_ENDPOINT,
        timeout: float = 5.0,
        _source=None,
    ):
        self._url = telemetry_url
        self._timeout = timeout
        self._source = _source  # injectable for testing

    def fetch(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch latest telemetry payload for a deployment.

        Returns a dict conforming to the runtime contract or None on failure.
        """
        if callable(self._source):
            return self._source(deployment_id)

        try:
            url = f"{self._url}/{deployment_id}"
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("[TELEMETRY] fetch failed for %s: %s", deployment_id, exc)
            return None


class DeploymentRegistry:
    """Reads active deployments from Shivam's deployment registry.

    Decision brain must NOT maintain its own deployment store.
    """

    def __init__(
        self,
        registry_url: str = REGISTRY_ENDPOINT,
        timeout: float = 5.0,
        _source=None,
    ):
        self._url = registry_url
        self._timeout = timeout
        self._source = _source  # injectable for testing

    def list_active(self) -> List[Dict[str, Any]]:
        """Return list of active deployment descriptors from the control plane."""
        if callable(self._source):
            return self._source()

        try:
            with urllib.request.urlopen(self._url, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("[REGISTRY] list_active failed: %s", exc)
            return []
