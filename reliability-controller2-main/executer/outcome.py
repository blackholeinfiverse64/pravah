"""
outcome.py — Outcome & Feedback Loop
Records results of every execution.
In production, this feeds back into Mitra scoring to improve future decisions.
"""

import json
from datetime import datetime


# In-memory outcome store (in production: use a database)
_outcome_history = []


def record_outcome(trace_id, success, latency, action=None, service_id=None):
    """Record the result of an execution for feedback."""
    outcome = {
        "trace_id":   trace_id,
        "success":    success,
        "latency":    round(latency, 4),
        "action":     action,
        "service_id": service_id,
        "recorded_at": datetime.utcnow().isoformat() + "Z"
    }

    _outcome_history.append(outcome)

    # Keep only last 100 outcomes in memory
    if len(_outcome_history) > 100:
        _outcome_history.pop(0)

    return outcome


def get_failure_rate(service_id):
    """Used by Mitra to adjust future risk scores."""
    relevant = [o for o in _outcome_history if o.get("service_id") == service_id]
    if not relevant:
        return 0.0
    failures = sum(1 for o in relevant if not o["success"])
    return round(failures / len(relevant), 2)