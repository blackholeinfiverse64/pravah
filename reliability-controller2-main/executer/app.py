from flask import Flask, request, jsonify
import time, subprocess, uuid, requests, os
from governance import validate_deployment_request

app = Flask(__name__)

MONITOR_URL = os.getenv("MONITOR_URL", "http://monitor-service:5004/track-event")

ALLOWED_SERVICES = ["web1-blue", "web1-green", "web2-blue", "web2-green"]
ALLOWED_ACTIONS  = ["restart", "scale"]


def execute_action(service, action):
    if service not in ALLOWED_SERVICES:
        return {"status": "failed", "error": "invalid service"}

    if action not in ALLOWED_ACTIONS:
        return {"status": "failed", "error": "invalid action"}

    cmd = [
        "kubectl", "patch", f"deployment/{service}", "-n", "prod",
        "-p", '{"spec":{"template":{"metadata":{"annotations":{"restart-time":"' + str(time.time()) + '"}}}}}'
    ]

    start = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "status":  "success" if res.returncode == 0 else "failed",
        "output":  res.stdout.strip(),
        "error":   res.stderr.strip(),
        "latency": time.time() - start
    }


@app.route("/execute-action", methods=["POST"])
def execute():

    # SECURITY LOCK — only sarathi can call this
    if request.headers.get("X-CALLER") != "sarathi":
        return jsonify({"error": "unauthorized"}), 403

    data = request.get_json(force=True)

    trace_id = data.get("trace_id")
    service  = data.get("service_id")
    action   = data.get("action")

    if not trace_id:
        return jsonify({"error": "trace_id required"}), 400

    if validate_deployment_request(service, action) == "BLOCK":
        return jsonify({"status": "blocked_by_governance", "trace_id": trace_id})

    execution_id = str(uuid.uuid4())

    # SIGNAL 3 — execution signal (observed fact: action was attempted)
    # Does NOT imply success — that comes from verification
    requests.post(MONITOR_URL, json={
        "user_id":      "system",
        "event_type":   "execution_started",
        "timestamp":    int(time.time()),
        "session_id":   "system",
        "trace_id":     trace_id,
        "execution_id": execution_id,
        "service":      service,
        "action":       action,
        "metadata":     {"source": service}
    })

    result = execute_action(service, action)

    # SIGNAL 4 — verification signal (observed fact: outcome confirmed)
    # Separate from execution — verification confirms what actually happened
    verification_result = "SUCCESS" if result["status"] == "success" else "FAILURE"

    requests.post(MONITOR_URL, json={
        "user_id":      "system",
        "event_type":   "verification_done",
        "timestamp":    int(time.time()),
        "session_id":   "system",
        "trace_id":     trace_id,
        "execution_id": execution_id,
        "result":       verification_result,
        "service":      service,
        "metadata":     {"source": service}
    })

    # Legacy execution_done for backward compat
    requests.post(MONITOR_URL, json={
        "user_id":      "system",
        "event_type":   "execution_done",
        "timestamp":    int(time.time()),
        "session_id":   "system",
        "trace_id":     trace_id,
        "execution_id": execution_id,
        "service":      service,
        "action":       action,
        "status":       result["status"],
        "latency":      result.get("latency"),
        "metadata":     {"source": service}
    })

    return jsonify({
        "execution_id": execution_id,
        "trace_id":     trace_id,
        **result
    })


@app.route("/health")
def health():
    return {"status": "ok"}


app.run(host="0.0.0.0", port=5003)