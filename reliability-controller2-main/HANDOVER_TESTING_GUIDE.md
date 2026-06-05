# HANDOVER_TESTING_GUIDE.md

This guide lets you run the full system in under 10 minutes and validate every layer.

---

## Prerequisites

- `curl` installed
- `uuidgen` installed (Linux: `apt install uuid-runtime`)
- Access to server `54.156.236.10`
- Two terminal windows

---

## Setup — Open Stream in Terminal 1

Keep this running throughout all tests.

```bash
curl -H "Host: pravah.blackholeinfiverse.com" \
  -N http://54.156.236.10/signals/stream
```

Expected: stream stays open, prints `keepalive` every few seconds.

---

## TEST 1 — Health Check

**Command:**
```bash
curl -s http://54.156.236.10/health
```

**Expected:**
```json
{"status": "ok"}
```

**Pass:** JSON returned with `"status": "ok"`
**Fail:** Connection refused or HTML error page

---

## TEST 2 — Trace ID Generation + Login

**Command:**
```bash
TRACE=$(uuidgen)
echo "TRACE: $TRACE"

curl -X POST http://54.156.236.10:30001/login \
  -H "X-TRACE-ID: $TRACE" \
  -d "user_id=vinayak"
```

**Expected terminal 1 stream output:**
```
data: {"signal_type": "login_detected", "service": "web1", "trace_id": "<your-TRACE>", "trace_origin": "core", ...}
```

**Pass:** Stream shows `login_detected` with matching `trace_id`
**Fail:** No signal appears in stream, or `trace_id` does not match

---

## TEST 3 — Interaction Click

```bash
curl -X POST http://54.156.236.10:30001/click \
  -H "X-TRACE-ID: $TRACE" \
  -d "user_id=vinayak&session_id=s_1"
```

**Expected response:**
```
clicked (trace=<your-TRACE>)
```

**Expected stream:**
```
data: {"signal_type": "user_interaction", "trace_id": "<your-TRACE>", ...}
```

**Pass:** `user_interaction` signal appears in stream
**Fail:** No signal, or wrong trace_id

---

## TEST 4 — Full Decision Flow (Happy Path)

```bash
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{
    \"trace_id\": \"$TRACE\",
    \"service_id\": \"web1-blue\",
    \"action_type\": \"restart\",
    \"payload\": {\"decision_score\": 0.9}
  }"
```

**Expected API response:**
```json
{
  "status": "executed",
  "trace_id": "<your-TRACE>",
  "executer_response": {
    "output": "deployment.apps/web1-blue patched",
    "status": "success",
    ...
  }
}
```

**Expected stream — 5 signals in this order:**
```
data: {"signal_type": "decision", "decision": "ALLOW", ...}
data: {"signal_type": "enforcement", "enforcement_status": "validated", ...}
data: {"signal_type": "execution", "value": "RUNNING", ...}
data: {"signal_type": "verification", "value": "SUCCESS", ...}
data: {"signal_type": "execution_completed", "value": "SUCCESS", ...}
```

**Pass criteria:**
- [ ] decision signal present with `"decision": "ALLOW"`
- [ ] enforcement signal present with `"enforcement_status": "validated"`
- [ ] execution signal present with `"value": "RUNNING"` (not SUCCESS)
- [ ] verification signal present with `"value": "SUCCESS"`
- [ ] execution_completed signal present
- [ ] All 5 share same `trace_id` as your TRACE
- [ ] All have `trace_origin: "core"`

---

## TEST 5 — Failure Case (Invalid Service)

```bash
TRACE2=$(uuidgen)
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{
    \"trace_id\": \"$TRACE2\",
    \"service_id\": \"invalid-service\",
    \"action_type\": \"restart\",
    \"payload\": {\"decision_score\": 0.9}
  }"
```

**Expected API response:**
```json
{"status": "failed", "trace_id": "<TRACE2>", "executer_response": {"status": "failed", "error": "invalid service", ...}}
```

**Expected stream:**
```
data: {"signal_type": "decision", "decision": "ALLOW", ...}
data: {"signal_type": "enforcement", "enforcement_status": "validated", ...}
data: {"signal_type": "execution", "service": "invalid-service", "value": "RUNNING", ...}
data: {"signal_type": "verification", "value": "FAILURE", "severity": "CRITICAL", ...}
data: {"signal_type": "execution_failed", "value": "FAILURE", "severity": "CRITICAL", ...}
```

**Pass criteria:**
- [ ] verification shows `"value": "FAILURE"` and `"severity": "CRITICAL"`
- [ ] execution_failed appears (not execution_completed)

---

## TEST 6 — Security Lock (Direct Execution Bypass)

```bash
curl -v -X POST http://54.156.236.10:30003/execute-action \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"hack","service_id":"web1-blue","action":"restart"}'
```

**Expected:**
```
HTTP/1.1 403 FORBIDDEN
{"error":"unauthorized"}
```

**Pass:** HTTP 403 + unauthorized body
**Fail:** Any 200 response or execution happening

---

## TEST 7 — BLOCK Decision (Low Score)

```bash
TRACE3=$(uuidgen)
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE3\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.2}}"
```

**Expected API response:**
```json
{"status": "BLOCK", "trace_id": "<TRACE3>"}
```

**Expected stream:** Only ONE signal:
```
data: {"signal_type": "decision", "decision": "BLOCK", ...}
```

**Pass:** No enforcement, no execution, no verification signals for TRACE3

---

## TEST 8 — Concurrency (5 Parallel Traces)

```bash
for i in {1..5}; do
  TRACE=$(uuidgen)
  curl -X POST http://54.156.236.10:30001/login \
    -H "X-TRACE-ID: $TRACE" \
    -d "user_id=test$i" &
done
```

**Expected stream:** 5 separate login_detected signals, each with unique trace_id and trace_hash.

**Pass criteria:**
- [ ] 5 signals appear
- [ ] All have different trace_id values
- [ ] No trace_id appears on another user's signal

---

## TEST 9 — Trace Continuity Check

For any trace you ran in TEST 4, verify continuity:

1. Find your TRACE value
2. In stream output, filter for signals with that trace_id
3. Verify each signal has:
   - `"trace_origin": "core"`
   - `"source": "core"`
   - Same `trace_hash` value on ALL signals

**Pass:** trace_hash is identical across all 8 signals for one trace

---

## Full Pass Criteria Summary

| Test | What it validates | Pass |
|------|------------------|------|
| 1 | System is up | `{"status":"ok"}` |
| 2 | Trace flows from Core to stream | login_detected with matching trace_id |
| 3 | Click events tracked | user_interaction in stream |
| 4 | Full happy path | 5 signals in order, execution_completed |
| 5 | Failure visible | verification FAILURE + CRITICAL severity |
| 6 | Security lock works | HTTP 403 |
| 7 | BLOCK policy works | Only decision signal, no execution |
| 8 | Concurrency isolated | 5 independent trace_ids |
| 9 | Trace continuity | Same trace_hash on all signals |