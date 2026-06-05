"""Runtime contract — aligned to Shivam's control plane payload format.

Required fields (Day 1 contract lock):
    deployment_id, environment, cpu_percent, memory_percent,
    health_score, restart_count, crashed
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Raised when a payload does not conform to the shared runtime contract."""


REQUIRED_FIELDS = (
    "deployment_id",
    "environment",
    "cpu_percent",
    "memory_percent",
    "health_score",
    "restart_count",
    "crashed",
)


@dataclass(frozen=True)
class RuntimePayload:
    deployment_id: str
    environment: str
    cpu_percent: float
    memory_percent: float
    health_score: float
    restart_count: int
    crashed: bool
    timestamp: float
    metadata: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimePayload":
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValidationError(f"Missing required fields: {missing}")

        deployment_id = str(data["deployment_id"]).strip()
        if not deployment_id:
            raise ValidationError("deployment_id must be non-empty")

        environment = str(data["environment"]).strip()
        if not environment:
            raise ValidationError("environment must be non-empty")

        try:
            cpu = float(data["cpu_percent"])
            mem = float(data["memory_percent"])
            health = float(data["health_score"])
            restarts = int(data["restart_count"])
            crashed = bool(data["crashed"])
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid numeric field: {exc}") from exc

        return cls(
            deployment_id=deployment_id,
            environment=environment,
            cpu_percent=cpu,
            memory_percent=mem,
            health_score=health,
            restart_count=restarts,
            crashed=crashed,
            timestamp=float(data.get("timestamp", time.time())),
            metadata=data.get("metadata") or {},
        )
