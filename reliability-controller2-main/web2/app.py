from flask import Flask, request, render_template_string
import requests
import time
import uuid

app = Flask(__name__)

MONITOR_URL = "http://monitor-service:5004/track-event"

login_page = """
<h2>Login</h2>
<form method="POST" action="/login">
  User ID: <input name="user_id"><br><br>
  <button type="submit">Login</button>
</form>
"""

dashboard_page = """
<h2>Dashboard - Web1</h2>
<p>Welcome {{user_id}}</p>
<p><b>Trace ID:</b> {{trace_id}}</p>

<form method="POST" action="/click">
  <input type="hidden" name="user_id" value="{{user_id}}">
  <input type="hidden" name="session_id" value="{{session_id}}">
  <input type="hidden" name="trace_id" value="{{trace_id}}">
  <button type="submit">Click</button>
</form>

<form method="POST" action="/logout">
  <input type="hidden" name="user_id" value="{{user_id}}">
  <input type="hidden" name="session_id" value="{{session_id}}">
  <input type="hidden" name="trace_id" value="{{trace_id}}">
  <button type="submit">Logout</button>
</form>
"""

@app.route("/")
def home():
    return login_page


@app.route("/login", methods=["POST"])
def login():
    user_id = request.form.get("user_id")

    trace_id = request.headers.get("X-TRACE-ID")

    if trace_id == "auto":
        trace_id = str(uuid.uuid4())

    if not trace_id:
        return "trace_id required", 400

    session_id = f"s_{int(time.time())}"

    for e in ["session_start", "user_login", "page_view"]:
        requests.post(MONITOR_URL, json={
            "user_id": user_id,
            "event_type": e,
            "timestamp": int(time.time()),
            "session_id": session_id,
            "trace_id": trace_id,
            "metadata": {"page": "dashboard", "source": "web1"}
        })

    return render_template_string(
        dashboard_page,
        user_id=user_id,
        session_id=session_id,
        trace_id=trace_id
    )


@app.route("/click", methods=["POST"])
def click():
    trace_id = request.headers.get("X-TRACE-ID")

    if not trace_id:
        return "trace_id required", 400

    requests.post(MONITOR_URL, json={
        "user_id": request.form.get("user_id"),
        "event_type": "interaction_click",
        "timestamp": int(time.time()),
        "session_id": request.form.get("session_id"),
        "trace_id": trace_id,
        "metadata": {"page": "dashboard", "source": "web1"}
    })

    return f"clicked (trace={trace_id})"


@app.route("/logout", methods=["POST"])
def logout():
    trace_id = request.headers.get("X-TRACE-ID")

    requests.post(MONITOR_URL, json={
        "user_id": request.form.get("user_id"),
        "event_type": "session_end",
        "timestamp": int(time.time()),
        "session_id": request.form.get("session_id"),
        "trace_id": trace_id,
        "metadata": {"source": "web1"}
    })

    return "logout"


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)