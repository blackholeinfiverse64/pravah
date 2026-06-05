from flask import Flask, jsonify
from flask import request
import time
import threading
import json
import uuid
from datetime import datetime

app = Flask(__name__)

start_time = time.time()
request_count = 0
failure_state = False


def log_event(event, level="INFO", extra=None):
    log = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "event": event
    }

    if extra:
        log.update(extra)

    print(json.dumps(log), flush=True)


@app.route("/health")
def health():
    global failure_state

    if failure_state:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/metrics")
def metrics():
    global request_count

    request_count += 1
    uptime = time.time() - start_time

    return jsonify({
        "requests": request_count,
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/simulate-failure", methods=["POST"])
def simulate_failure():
    global failure_state

    failure_state = True

    log_event(
        "failure_simulated",
        "WARN",
        {"failure_type": "manual_simulation"}
    )

    return jsonify({
        "status": "failure_simulated"
    })


def monitor_service():
    global failure_state

    while True:
        time.sleep(5)

        if failure_state:
            detection_time = datetime.utcnow().isoformat()

            log_event(
                "service_unhealthy_detected",
                "WARN",
                {
                    "failure_type": "health_check_failed",
                    "detection_time": detection_time
                }
            )

            recover_service(detection_time)


def recover_service(detection_time):
    global failure_state

    log_event(
        "recovery_attempt",
        "INFO",
        {"action_taken": "restart_service"}
    )

    time.sleep(2)

    failure_state = False

    recovery_time = datetime.utcnow().isoformat()

    log_event(
        "recovery_successful",
        "INFO",
        {
            "detection_time": detection_time,
            "recovery_time": recovery_time,
            "action_taken": "restart_service"
        }
    )


if __name__ == "__main__":
    monitor_thread = threading.Thread(target=monitor_service)
    monitor_thread.daemon = True
    monitor_thread.start()

    log_event("monitoring_service_started")

    app.run(host="0.0.0.0", port=5000)

def log_event(event, level="INFO", extra=None):

    log = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "event": event,
        "source_ip": request.remote_addr if request else "internal"
    }

    if extra:
        log.update(extra)

    print(json.dumps(log), flush=True)
