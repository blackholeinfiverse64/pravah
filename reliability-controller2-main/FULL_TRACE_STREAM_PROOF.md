# FULL_TRACE_STREAM_PROOF.md

**System:** Pravah
**Claim:** For a single trace_id, the stream shows all 6 required stages in order. Each is a flat independent signal. No stage missing. No stage inferred.

---

## Trace Under Test
trace_id:   5d050c8c-c880-4e6d-9a01-8274556f30ec
trace_hash: 3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32
date:       2026-04-29
server:     54.156.236.10

---

## Commands Used

```bash
TRACE=5d050c8c-c880-4e6d-9a01-8274556f30ec

curl -X POST http://54.156.236.10:30001/login \
  -H "X-TRACE-ID: $TRACE" -d "user_id=test"

curl -X POST http://54.156.236.10:30001/click \
  -H "X-TRACE-ID: $TRACE" -d "user_id=test&session_id=s_1"

curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.9}}"
```

---

## Full Live Stream — All Signals for This Trace (Real Output)

**Signal 1 — login_detected (Core)**
data: {"signal_type": "login_detected", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450910, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:29.934096Z"}

**Signal 2 — user_interaction (Core — page_view)**
data: {"signal_type": "user_interaction", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450910, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:30.335475Z"}

**Signal 3 — user_interaction (Core — interaction_click)**
data: {"signal_type": "user_interaction", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450917, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:30.535945Z"}

**Signal 4 — decision (Sarathi)**
data: {"signal_type": "decision", "service": "system", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "decision": "ALLOW", "policy_reference": "score_threshold_0.6", "action": "restart", "emitted_at": "2026-04-29T08:23:30.736409Z"}

**Signal 5 — enforcement (Sarathi)**
data: {"signal_type": "enforcement", "service": "sarathi", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "enforcement_status": "validated", "emitted_at": "2026-04-29T08:23:30.936904Z"}

**Signal 6 — execution (Executer — action attempted)**
data: {"signal_type": "execution", "service": "web1-blue", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.137373Z"}

**Signal 7 — verification (Executer — outcome confirmed)**
data: {"signal_type": "verification", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "result": "SUCCESS", "emitted_at": "2026-04-29T08:23:31.337985Z"}

**Signal 8 — execution_completed (Executer — final state)**
data: {"signal_type": "execution_completed", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.538460Z"}

---

## Stage Checklist

| # | Required Stage | Signal Type | emitted_at | Present |
|---|---------------|-------------|------------|---------|
| 1 | user_event | login_detected | 08:23:29.934Z | ✅ |
| 2 | decision (Sarathi) | decision | 08:23:30.736Z | ✅ |
| 3 | enforcement (Sarathi) | enforcement | 08:23:30.936Z | ✅ |
| 4 | execution | execution | 08:23:31.137Z | ✅ |
| 5 | verification | verification | 08:23:31.337Z | ✅ |
| 6 | signal emission | execution_completed | 08:23:31.538Z | ✅ |

All 6 stages present. All same trace_id. All flat. No missing stage. No inference.

---

## Format Compliance

| Rule | Status |
|------|--------|
| No `causal_chain` field | ✅ |
| No `correlation` object | ✅ |
| No `signals[]` wrapper | ✅ |
| Each `data:` line = one signal | ✅ |
| `trace_origin` on every signal | ✅ |
| `source` on every signal | ✅ |
| `trace_hash` on every signal | ✅ |