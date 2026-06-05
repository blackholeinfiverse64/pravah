# HANDOVER_EXECUTION_FLOW.md

This document shows exactly what happens, step by step, for one complete execution.
Every input, every output, every signal is shown using real data from the live system.

---

## Reference Trace

```
trace_id:   5d050c8c-c880-4e6d-9a01-8274556f30ec
execution_id: 4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d
date:       2026-04-29
server:     54.156.236.10
```

---

## Step 1 — Core sends login request

**Who does this:** The caller (developer, test script, browser)
**Where it goes:** `web1/app.py` → POST /login

**Input:**
```bash
curl -X POST http://54.156.236.10:30001/login \
  -H "X-TRACE-ID: 5d050c8c-c880-4e6d-9a01-8274556f30ec" \
  -d "user_id=test"
```

**What web1/app.py does internally:**
1. Reads `X-TRACE-ID` header → `trace_id = "5d050c8c-..."`
2. Creates `session_id = "s_1777450910"`
3. Posts three events to Monitor in sequence:
   - `session_start`
   - `user_login`
   - `page_view`

**Each event posted to Monitor looks like:**
```json
{
  "user_id": "test",
  "event_type": "user_login",
  "timestamp": 1777450910,
  "session_id": "s_1777450910",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "metadata": {"page": "dashboard", "source": "web1"}
}
```

**Output (HTTP response from web1):**
```html
<h2>Dashboard - Web1</h2>
<p>Welcome test</p>
<p><b>Trace ID:</b> 5d050c8c-c880-4e6d-9a01-8274556f30ec</p>
...
```

**Signals emitted to stream:**
```
data: {"signal_type": "login_detected", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450910, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:29.934096Z"}
```

---

## Step 2 — Sarathi evaluates the decision

**Who does this:** The caller (developer, test script, automation)
**Where it goes:** `sarathi/app.py` → POST /decision

**Input:**
```bash
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
    "service_id": "web1-blue",
    "action_type": "restart",
    "payload": {"decision_score": 0.9}
  }'
```

**What sarathi/app.py does internally:**
1. Reads `trace_id` from body
2. Reads `decision_score` from payload → `0.9`
3. Applies policy: `0.9 > 0.6` → `decision_status = "ALLOW"`
4. Posts `decision_made` event to Monitor

**Decision event posted to Monitor:**
```json
{
  "user_id": "sarathi",
  "event_type": "decision_made",
  "timestamp": 1777450932,
  "session_id": "system",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "metadata": {
    "decision": "ALLOW",
    "action": "restart",
    "policy_reference": "score_threshold_0.6"
  }
}
```

**Signal emitted to stream:**
```
data: {"signal_type": "decision", "service": "system", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "decision": "ALLOW", "policy_reference": "score_threshold_0.6", "action": "restart", "emitted_at": "2026-04-29T08:23:30.736409Z"}
```

---

## Step 3 — Sarathi enforces the gate

**Happens automatically** inside sarathi/app.py after ALLOW decision.
No external call needed.

**What sarathi/app.py does internally:**
1. Since `decision_status == "ALLOW"`, posts `enforcement_done` to Monitor

**Enforcement event posted to Monitor:**
```json
{
  "user_id": "sarathi",
  "event_type": "enforcement_done",
  "timestamp": 1777450932,
  "session_id": "system",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "enforcement_status": "validated",
  "metadata": {"source": "sarathi"}
}
```

**Signal emitted to stream:**
```
data: {"signal_type": "enforcement", "service": "sarathi", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "enforcement_status": "validated", "emitted_at": "2026-04-29T08:23:30.936904Z"}
```

---

## Step 4 — Executer runs the action

**Happens automatically** — Sarathi calls Executer after enforcement.
`POST http://executer-service:5003/execute-action` with `X-CALLER: sarathi` header.

**What executer/app.py does internally:**
1. Checks `X-CALLER: sarathi` header — passes
2. Reads `trace_id`, `service_id`, `action`
3. Calls `governance.validate_deployment_request("web1-blue", "restart")` → `"ALLOW"`
4. Generates `execution_id = "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d"`
5. Posts `execution_started` to Monitor
6. Runs kubectl:
   ```
   kubectl patch deployment/web1-blue -n prod -p '{"spec":{"template":{"metadata":{"annotations":{"restart-time":"..."}}}}}'
   ```

**Execution event posted to Monitor:**
```json
{
  "user_id": "system",
  "event_type": "execution_started",
  "timestamp": 1777450932,
  "session_id": "system",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d",
  "service": "web1-blue",
  "action": "restart",
  "metadata": {"source": "web1-blue"}
}
```

**Signal emitted to stream:**
```
data: {"signal_type": "execution", "service": "web1-blue", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.137373Z"}
```

---

## Step 5 — Executer verifies the outcome

**Happens automatically** inside executer/app.py after kubectl returns.

kubectl output: `deployment.apps/web1-blue patched` → returncode 0 → `status = "success"`

**Verification event posted to Monitor:**
```json
{
  "user_id": "system",
  "event_type": "verification_done",
  "timestamp": 1777450932,
  "session_id": "system",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d",
  "result": "SUCCESS",
  "service": "web1-blue",
  "metadata": {"source": "web1-blue"}
}
```

**Signal emitted to stream:**
```
data: {"signal_type": "verification", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "result": "SUCCESS", "emitted_at": "2026-04-29T08:23:31.337985Z"}
```

---

## Step 6 — Pravah emits final signal + API returns

**Final execution_completed signal emitted to stream:**
```
data: {"signal_type": "execution_completed", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.538460Z"}
```

**Final Sarathi API response (real):**
```json
{
  "status": "executed",
  "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "executer_response": {
    "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d",
    "latency": 0.6184470653533936,
    "output": "deployment.apps/web1-blue patched",
    "status": "success",
    "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec"
  }
}
```

---

## Complete Signal Timeline for This Trace

| Time | Signal | Emitted by |
|------|--------|-----------|
| 08:23:29.934Z | login_detected | Core/web1 |
| 08:23:30.335Z | user_interaction (page_view) | Core/web1 |
| 08:23:30.535Z | user_interaction (click) | Core/web1 |
| 08:23:30.736Z | decision (ALLOW) | Sarathi |
| 08:23:30.936Z | enforcement (validated) | Sarathi |
| 08:23:31.137Z | execution (RUNNING) | Executer |
| 08:23:31.337Z | verification (SUCCESS) | Executer |
| 08:23:31.538Z | execution_completed | Executer |
