"""Runtime contract definitions and validation for Pravah decision brain.

This module defines the canonical runtime payload schema that the control plane
and decision brain agree on. All incoming runtime state is normalized according
to this schema.

The runtime contract is intentionally minimal and strict: missing required fields
raise ValidationError and are considered a malformed control plane payload.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


class ValidationError(Exception):
    """Raised when a payload does not conform to the shared runtime contract."""


@dataclass(frozen=True)
class Alert:
    type: str
    severity: str
    message: str


@dataclass(frozen=True)
class RuntimePayload:
    app_id: str
    environment: str
    timestamp: float
    signals: Dict[str, float]
    alerts: List[Alert]
    metadata: Dict[str, Any]

    @staticmethod
    def _coerce_timestamp(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Accept ISO 8601 or number string
            try:
                return float(value)
            except ValueError:
                try:
                    dt = datetime.datetime.fromisoformat(value)
                    return dt.timestamp()
                except Exception as exc:
                    raise ValidationError(f"Invalid timestamp format: {value}") from exc
        raise ValidationError(f"Invalid timestamp type: {type(value)}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimePayload":
        """Normalize an incoming runtime payload to the canonical contract."""
        missing = [k for k in ("app_id", "environment", "timestamp", "signals") if k not in data]
        if missing:
            raise ValidationError(f"Missing required runtime fields: {missing}")

        app_id = data["app_id"]
        if not isinstance(app_id, str) or not app_id:
            raise ValidationError("app_id must be a non-empty string")

        environment = data["environment"]
        if not isinstance(environment, str) or not environment:
            raise ValidationError("environment must be a non-empty string")

        timestamp = cls._coerce_timestamp(data["timestamp"])

        signals = data["signals"]
        if not isinstance(signals, dict):
            raise ValidationError("signals must be a dictionary")

        normalized_signals: Dict[str, float] = {}
        for key, value in signals.items():
            if value is None:
                continue
            try:
                normalized_signals[key] = float(value)
            except Exception as exc:
                raise ValidationError(f"Signal {key} must be numeric") from exc

        alerts_raw = data.get("alerts") or []
        if not isinstance(alerts_raw, list):
            raise ValidationError("alerts must be a list")
        alerts: List[Alert] = []
        for item in alerts_raw:
            if not isinstance(item, dict):
                raise ValidationError("alerts must be list of objects")
            if "type" not in item or "severity" not in item or "message" not in item:
                raise ValidationError("each alert must include type, severity, and message")
            alerts.append(Alert(type=str(item["type"]), severity=str(item["severity"]), message=str(item["message"])))

        metadata = data.get("metadata") or {}
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise ValidationError("metadata must be an object")

        return cls(
            app_id=app_id,
            environment=environment,
            timestamp=timestamp,
            signals=normalized_signals,
            alerts=alerts,
            metadata=metadata,
        )


def runtime_contract_schema() -> Dict[str, Any]:
    """Return a JSON-schema-like representation of the runtime contract."""
    return {
        "type": "object",
        "required": ["app_id", "environment", "timestamp", "signals"],
        "properties": {
            "app_id": {"type": "string"},
            "environment": {"type": "string"},
            "timestamp": {"oneOf": [{"type": "number"}, {"type": "string"}]},
            "signals": {"type": "object", "additionalProperties": {"type": "number"}},
            "alerts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "severity", "message"],
                    "properties": {
                        "type": {"type": "string"},
                        "severity": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
            },
            "metadata": {"type": "object"},
        },
        "additionalProperties": False,
    }
