from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Mapping

_key = os.getenv("LINEAGE_SIGNING_KEY")
if not _key:
    if os.getenv("ENVIRONMENT", "").strip().lower() == "prod":
        raise ValueError("LINEAGE_SIGNING_KEY must be set in production")
    _key = "pravah-sovereign-lineage-key"
SECRET_KEY = _key.encode("utf-8")


def make_canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: make_canonical(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, (list, tuple)):
        return [make_canonical(x) for x in obj]
    elif isinstance(obj, set):
        return [make_canonical(x) for x in sorted(list(obj), key=str)]
    elif hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return make_canonical(obj.model_dump(mode="json"))
    elif hasattr(obj, "__dict__"):
        return make_canonical(obj.__dict__)
    return obj

def canonicalize(payload: Any) -> str:
    return json.dumps(make_canonical(payload), separators=(",", ":"), default=str)


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonicalize(payload).encode("utf-8")).hexdigest()


def sign_trace(trace_data: str) -> str:
    return hmac.new(SECRET_KEY, trace_data.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class SignedTrace:
    trace_id: str
    execution_id: str
    parent_hash: str
    payload_hash: str
    timestamp: float
    signer: str
    signature: str


def _trace_material(trace: Mapping[str, Any]) -> str:
    return canonicalize(
        {
            "trace_id": trace["trace_id"],
            "execution_id": trace["execution_id"],
            "parent_hash": trace["parent_hash"],
            "payload_hash": trace["payload_hash"],
            "timestamp": trace["timestamp"],
            "signer": trace["signer"],
        }
    )


def trace_hash(trace: SignedTrace | Mapping[str, Any]) -> str:
    trace_dict = asdict(trace) if isinstance(trace, SignedTrace) else dict(trace)
    return hashlib.sha256(_trace_material(trace_dict).encode("utf-8")).hexdigest()


def build_signed_trace(
    trace_id: str,
    execution_id: str,
    payload: Mapping[str, Any],
    parent_hash: str,
    signer: str,
    timestamp: float | None = None,
) -> SignedTrace:
    envelope_timestamp = time.time() if timestamp is None else float(timestamp)
    trace_payload_hash = payload_hash(payload)
    unsigned_trace = {
        "trace_id": trace_id,
        "execution_id": execution_id,
        "parent_hash": parent_hash,
        "payload_hash": trace_payload_hash,
        "timestamp": envelope_timestamp,
        "signer": signer,
    }
    signature = sign_trace(_trace_material(unsigned_trace))
    return SignedTrace(signature=signature, **unsigned_trace)


def serialize_signed_trace(trace: SignedTrace) -> dict[str, Any]:
    return asdict(trace)


class SignedTraceBuilder:
    @staticmethod
    def create_event(
        payload: Mapping[str, Any],
        execution_id: str | None = None,
        trace_id: str | None = None,
        parent_hash: str = "",
        signer: str = "runtime",
        timestamp: float | None = None,
    ) -> SignedTrace:
        resolved_execution_id = execution_id or str(uuid.uuid4())
        resolved_trace_id = trace_id or str(uuid.uuid4())
        return build_signed_trace(
            trace_id=resolved_trace_id,
            execution_id=resolved_execution_id,
            payload=payload,
            parent_hash=parent_hash,
            signer=signer,
            timestamp=timestamp,
        )

    @staticmethod
    def serialize(trace: SignedTrace) -> dict[str, Any]:
        return serialize_signed_trace(trace)