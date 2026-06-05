from flask import Flask, request, jsonify
import requests, os, time

app = Flask(__name__)

EXECUTER_URL = os.getenv("EXECUTER_URL", "http://executer-service:5003/execute-action")
MONITOR_URL  = os.getenv("MONITOR_URL",  "http://monitor-service:5004/track-event")


@app.route("/decision", methods=["POST"])
def decision():
    data = request.get_json()

    trace_id = data.get("trace_id")
    payload  = data.get("payload", {})
    action   = data.get("action_type")
    service  = data.get("service_id")

    if not trace_id:
        return jsonify({"error": "trace_id required"}), 400

    score = payload.get("decision_score", 0)

    # POLICY — deterministic threshold
    if score > 0.6:
        decision_status = "ALLOW"
    elif score > 0.35:
        decision_status = "ESCALATE"
    else:
        decision_status = "BLOCK"

    # SIGNAL 1 — decision signal (observed fact: decision was made)
    requests.post(MONITOR_URL, json={
        "user_id":    "sarathi",
        "event_type": "decision_made",
        "timestamp":  int(time.time()),
        "session_id": "system",
        "trace_id":   trace_id,
        "metadata": {
            "decision":         decision_status,
            "action":           action,
            "policy_reference": "score_threshold_0.6"
        }
    })

    if decision_status != "ALLOW":
        return jsonify({"status": decision_status, "trace_id": trace_id})

    # SIGNAL 2 — enforcement signal (observed fact: gate was validated before execution)
    requests.post(MONITOR_URL, json={
        "user_id":            "sarathi",
        "event_type":         "enforcement_done",
        "timestamp":          int(time.time()),
        "session_id":         "system",
        "trace_id":           trace_id,
        "enforcement_status": "validated",
        "metadata": {
            "source": "sarathi"
        }
    })

    # EXECUTION — only path after enforcement validated
    res = requests.post(EXECUTER_URL, json={
        "trace_id":   trace_id,
        "service_id": service,
        "action":     action,
        "metrics":    payload
    }, headers={"X-CALLER": "sarathi"})

    exec_res = res.json()

    if exec_res.get("status") != "success":
        return jsonify({
            "status":            "failed",
            "trace_id":          trace_id,
            "executer_response": exec_res
        })

    return jsonify({
        "status":            "executed",
        "trace_id":          trace_id,
        "executer_response": exec_res
    })


@app.route("/health")
def health():
    return {"status": "healthy"}


app.run(host="0.0.0.0", port=5001)