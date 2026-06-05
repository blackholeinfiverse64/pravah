from flask import Flask, request, jsonify, Response
import time, json, threading, hashlib
from collections import deque
from datetime import datetime

app = Flask(__name__)

MAX_EVENTS = 1000
user_events = deque(maxlen=MAX_EVENTS)
signal_queue = deque(maxlen=MAX_EVENTS)   # each item = one flat signal dict
lock = threading.Lock()

def now_iso():
    return datetime.utcnow().isoformat() + "Z"

def trace_hash(trace_id):
    return hashlib.sha256(trace_id.encode()).hexdigest()


# =============================================================
# INGEST — /track-event
# Receives raw events from Web, Sarathi, Executer layers.
# Converts each event into ONE flat, independent signal.
# No interpretation. No grouping. No inference.
# =============================================================

EVENT_TO_SIGNAL = {
    "session_start":     ("login_detected",      "status", "RUNNING"),
    "user_login":        ("login_detected",      "status", "RUNNING"),
    "page_view":         ("user_interaction",    "status", "RUNNING"),
    "interaction_click": ("user_interaction",    "status", "RUNNING"),
    "decision_made":     ("decision",            "status", "RUNNING"),
    "enforcement_done":  ("enforcement",         "status", "RUNNING"),
    "execution_started": ("execution",           "status", "RUNNING"),
    "verification_done": ("verification",        "status", "SUCCESS"),
    "execution_done":    ("execution_completed", "status", "SUCCESS"),
    "session_end":       ("session_end",         "status", "RUNNING"),
}

def severity_for(metric, value):
    if value == "FAILURE":
        return "CRITICAL"
    if value == "SUCCESS":
        return "INFO"
    return "INFO"

def build_flat_signal(event):
    """
    Convert a raw event dict into one flat signal dict.
    No interpretation — only maps observed event fields to signal fields.
    """
    trace_id   = event.get("trace_id")
    event_type = event.get("event_type", "unknown")

    signal_type, metric, default_value = EVENT_TO_SIGNAL.get(
        event_type, (event_type, "status", "RUNNING")
    )

    value = default_value

    # execution_done carries explicit status — use it directly
    if event_type == "execution_done":
        raw_status = event.get("status", "")
        value = "SUCCESS" if raw_status == "success" else "FAILURE"
        signal_type = "execution_completed" if value == "SUCCESS" else "execution_failed"

    # verification carries explicit result
    if event_type == "verification_done":
        value = event.get("result", "SUCCESS")

    service = (
        event.get("service")
        or event.get("metadata", {}).get("source")
        or "system"
    )

    severity = severity_for(metric, value)

    signal = {
        "signal_type":  signal_type,
        "service":      service,
        "metric":       metric,
        "value":        value,
        "severity":     severity,
        "timestamp":    event.get("timestamp", int(time.time())),
        "trace_id":     trace_id,
        "trace_origin": "core",
        "trace_hash":   trace_hash(trace_id) if trace_id else None,
        "source":       "core",
    }

    # execution_id — attach if present
    if event.get("execution_id"):
        signal["execution_id"] = event["execution_id"]

    # Sarathi decision fields — flat, no nesting
    if event_type == "decision_made":
        meta = event.get("metadata", {})
        signal["decision"]         = meta.get("decision")
        signal["policy_reference"] = meta.get("policy_reference", "score_threshold_0.6")
        signal["action"]           = meta.get("action")

    # enforcement fields — flat
    if event_type == "enforcement_done":
        signal["enforcement_status"] = event.get("enforcement_status", "validated")

    # verification fields — flat
    if event_type == "verification_done":
        signal["result"]       = event.get("result", "SUCCESS")
        signal["execution_id"] = event.get("execution_id")

    return signal


@app.route("/track-event", methods=["POST"])
def track_event():
    data = request.get_json(force=True)

    required = ["user_id", "event_type", "timestamp", "session_id", "trace_id"]
    if not all(data.get(k) for k in required):
        return jsonify({"error": "invalid event"}), 400

    signal = build_flat_signal(data)

    with lock:
        user_events.append(data)
        signal_queue.append(signal)

    return jsonify({"status": "ok"})


# =============================================================
# STREAM — /signals/stream
# Emits ONE signal per SSE event.
# Each signal is flat, independent, non-interpretive.
# No blobs. No correlation objects. No causal_chain.
# =============================================================

def stream_generator():
    while True:
        try:
            with lock:
                signal = signal_queue.popleft() if signal_queue else None

            if signal:
                payload = {**signal, "emitted_at": now_iso()}
                yield f"data: {json.dumps(payload)}\n\n"
            else:
                yield ": keepalive\n\n"

        except Exception as e:
            print("[STREAM ERROR]", e)
            yield ": error\n\n"

        time.sleep(0.2)


@app.route("/signals/stream")
def stream():
    return Response(
        stream_generator(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/health")
def health():
    return {"status": "ok"}


app.run(host="0.0.0.0", port=5004)