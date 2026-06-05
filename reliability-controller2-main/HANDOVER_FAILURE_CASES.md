# HANDOVER_FAILURE_CASES.md

Every failure case documented with exact input, exact output, and explanation.

---

## Case 1 — Missing trace_id → Rejection at Core

**Input:**
```bash
curl -X POST http://54.156.236.10:30001/login \
  -d "user_id=test"
# No X-TRACE-ID header
```

**Output:**
```
trace_id required
HTTP 400
```

**Explanation:**
web1/app.py reads `request.headers.get("X-TRACE-ID")`. If None and not "auto", returns 400.
No events are sent to Monitor. No signals appear in stream.

---

## Case 2 — Missing trace_id at Sarathi

**Input:**
```bash
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d '{"service_id":"web1-blue","action_type":"restart","payload":{"decision_score":0.9}}'
```

**Output:**
```json
{"error": "trace_id required"}
HTTP 400
```

**Explanation:**
sarathi/app.py checks `data.get("trace_id")`. If missing, returns 400 immediately.
No decision signal is emitted.

---

## Case 3 — Invalid service → Execution failure

**Input:**
```bash
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"invalid-service\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.9}}"
```

**Output (Sarathi response):**
```json
{
  "executer_response": {
    "error": "invalid service",
    "execution_id": "8ca09b1b-a5b0-457e-8ef0-5d6bb6cc2e85",
    "status": "failed",
    "trace_id": "cba18bcc-c5c0-41e6-8e10-913c43613f73"
  },
  "status": "failed",
  "trace_id": "cba18bcc-c5c0-41e6-8e10-913c43613f73"
}
```

**Stream signals (real output):**
```
data: {"signal_type": "decision", "decision": "ALLOW", ...}
data: {"signal_type": "enforcement", "enforcement_status": "validated", ...}
data: {"signal_type": "execution", "service": "invalid-service", "value": "RUNNING", ...}
data: {"signal_type": "verification", "service": "invalid-service", "value": "FAILURE", "severity": "CRITICAL", "result": "FAILURE", ...}
data: {"signal_type": "execution_failed", "service": "invalid-service", "value": "FAILURE", "severity": "CRITICAL", ...}
```

**Explanation:**
executer/app.py calls `execute_action("invalid-service", "restart")`.
`ALLOWED_SERVICES = ["web1-blue", "web1-green", "web2-blue", "web2-green"]` — not in list.
Returns `{"status": "failed", "error": "invalid service"}`.
Verification signal is posted with `result: "FAILURE"` and `severity: "CRITICAL"`.

---

## Case 4 — Sarathi BLOCK → No execution

**Input:**
```bash
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.2}}"
```

**Output:**
```json
{"status": "BLOCK", "trace_id": "<trace_id>"}
```

**Stream signals:**
```
data: {"signal_type": "decision", "decision": "BLOCK", "policy_reference": "score_threshold_0.6", ...}
```
No enforcement signal. No execution signal. No verification signal.

**Explanation:**
sarathi/app.py: `0.2 <= 0.35` → `decision_status = "BLOCK"`.
Posts decision signal, then returns immediately. Executer is never called.

---

## Case 5 — Sarathi ESCALATE → No execution

**Input:**
```bash
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.5}}"
```

**Output:**
```json
{"status": "ESCALATE", "trace_id": "<trace_id>"}
```

**Stream signals:**
```
data: {"signal_type": "decision", "decision": "ESCALATE", ...}
```
No execution. No verification.

**Explanation:**
`0.35 < 0.5 <= 0.6` → `decision_status = "ESCALATE"`. Returns without calling Executer.

---

## Case 6 — Direct execution bypass attempt → 403

**Input:**
```bash
curl -X POST http://54.156.236.10:30003/execute-action \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"hack","service_id":"web1-blue","action":"restart"}'
```

**Output (real):**
```json
{"error": "unauthorized"}
HTTP 403 FORBIDDEN
```

**Explanation:**
executer/app.py: `if request.headers.get("X-CALLER") != "sarathi": return 403`
Missing `X-CALLER: sarathi` header → immediate rejection.
No signals emitted. No kubectl runs.

---

## Case 7 — Missing required fields in track-event

**Input:**
```bash
curl -X POST http://54.156.236.10:30004/track-event \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","event_type":"login"}'
```

**Output:**
```json
{"error": "invalid event"}
HTTP 400
```

**Explanation:**
monitor/app.py requires: `user_id`, `event_type`, `timestamp`, `session_id`, `trace_id`.
Any missing → rejected. No signal queued.

---

## Case 8 — Governance BLOCK (specific rule)

**Input:**
```bash
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"<uuid>","service_id":"critical-service","action_type":"scale_up","payload":{"decision_score":0.9}}'
```

**Output:**
```json
{"status": "blocked_by_governance", "trace_id": "<uuid>"}
```

**Explanation:**
executer/governance.py: `if action == "scale_up" and service_id == "critical-service": return "BLOCK"`
This check happens inside executer AFTER the security header passes.
Execution signal is NOT emitted when governance blocks.
DONE

Print file

Script

Print file

Script

Print file

Script

Print file

Script
Done
All 9 files are above. Here's your exact copy-paste map:

Create these 9 files in VS Code — copy the content from above
#	File path to create	Content is in the output labeled
1	HANDOVER_SYSTEM_OVERVIEW.md	First cat output
2	HANDOVER_REPO_MAP.md	Second cat output
3	HANDOVER_EXECUTION_FLOW.md	Third cat output
4	HANDOVER_API_SPEC.md	Fourth cat output
5	HANDOVER_FAILURE_CASES.md	Fifth cat output
6	HANDOVER_TESTING_GUIDE.md	Sixth cat output
7	HANDOVER_FAQ.md	Seventh cat output
8	scripts/handover_demo.sh	Eighth cat output
9	review_packets/pravah_handover.md	Ninth cat output
For file 8, also create the scripts/ folder first if it doesn't exist, and the file needs no special formatting — just paste as-is.

Once pushed — you're done. Good luck with the handover, and well done building the whole cluster yourself on AWS. That's solid work.



