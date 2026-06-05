import time
import json
from severity_engine import classify_signal
from validator import validate_signal


def build_signal(signal_type, service, metric, value, trace_id):
    # 🔥 STRICT TRACE CHECK
    if not trace_id:
        raise Exception("trace_id is required for signal")

    if not signal_type or not service or not metric:
        if not trace_id:
            print("⚠️ Missing trace_id, skipping signal", flush=True)
            return None

    # =========================
    # BUILD SIGNAL
    # =========================
    signal = {
        "signal_type": signal_type,
        "severity": classify_signal(metric, value),
        "service": service,
        "metric": metric,
        "value": value,
        "timestamp": int(time.time()),
        "trace_id": trace_id
    }

    # =========================
    # VALIDATION (STRICT)
    # =========================
    validate_signal(signal)

    # =========================
    # LOG (STRUCTURED JSON)
    # =========================
    print(json.dumps({
        "event": "SIGNAL_EMITTED",
        "trace_id": trace_id,
        "signal_type": signal_type,
        "service": service,
        "metric": metric,
        "value": value,
        "timestamp": signal["timestamp"]
    }), flush=True)

    return signal