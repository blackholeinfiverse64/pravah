"""
APPEND-ONLY LOGGING SYSTEM (BHIV COMPLIANT)

RULES:
- WRITE ONLY
- NO READ OPERATIONS
- NO DELETE
- NO OVERWRITE
- DOES NOT INFLUENCE SYSTEM BEHAVIOR
"""

import json
from datetime import datetime


def log_event(trace_id, event, data):
    entry = {
        "trace_id": trace_id,
        "event": event,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }

    # STRICTLY WRITE-ONLY
    print(json.dumps(entry), flush=True)