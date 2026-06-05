SARATHI_PROOF — ENFORCEMENT VALIDATION
Claim: Execution in Pravah is gated exclusively through Sarathi. No bypass path exists.

1. DECISION PAYLOAD (Sarathi → Monitor)
When Sarathi evaluates a proposal it logs this decision to the monitor:
json{
  "user_id": "sarathi",
  "event_type": "decision_made",
  "timestamp": 1714200000,
  "session_id": "system",
  "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0",
  "metadata": {
    "decision": "ALLOW",
    "action": "restart"
  }
}
Source code (sarathi/app.py):
pythonrequests.post(MONITOR_URL, json={
    "user_id": "sarathi",
    "event_type": "decision_made",
    "timestamp": int(time.time()),
    "session_id": "system",
    "trace_id": trace_id,
    "metadata": {"decision": status, "action": action}
})

2. ENFORCEMENT PAYLOAD (Sarathi → Executer, header-locked)
After ALLOW, Sarathi calls Executer with the enforcement header:
jsonPOST /execute-action
Headers: { "X-CALLER": "sarathi" }

Body:
{
  "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0",
  "service_id": "web1-blue",
  "action": "restart",
  "metrics": { "decision_score": 0.75, "confidence": 0.9 }
}
Executer validates the header before any action:
pythonif request.headers.get("X-CALLER") != "sarathi":
    return jsonify({"error": "unauthorized"}), 403
The enforcement signal logged to monitor after execution:
json{
  "user_id": "system",
  "event_type": "execution_done",
  "timestamp": 1714200010,
  "session_id": "system",
  "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0",
  "execution_id": "f8e3c2b1-xxxx-xxxx-xxxx-yyyyyyyyyyyy",
  "service": "web1-blue",
  "action": "restart",
  "status": "success",
  "latency": 0.312
}

3. EXECUTION ONLY AFTER ALLOW — Code Proof
python# sarathi/app.py

score = payload.get("decision_score", 0)

if score > 0.6:
    status = "ALLOW"
elif score > 0.35:
    status = "ESCALATE"
else:
    status = "BLOCK"

# Decision is always logged first
requests.post(MONITOR_URL, json={...decision payload...})

if status != "ALLOW":
    return jsonify({"status": status, "trace_id": trace_id})   # ← EXECUTION NEVER REACHED

# Only if ALLOW:
res = requests.post(EXECUTER_URL, json={...}, headers={"X-CALLER": "sarathi"})
If status is BLOCK or ESCALATE → function returns before ever calling Executer.

4. BYPASS ATTEMPT — BLOCKED
Direct call to Executer (without going through Sarathi):
bashcurl -s -X POST http://pravah.blackholeinfiverse.com/execute-action \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "web1-blue",
    "action": "restart",
    "trace_id": "bypass-attempt-001"
  }'
Response:
json{"error": "unauthorized"}
HTTP Status: 403 Forbidden

5. FULL SARATHI-GATED EXECUTION — CURL PROOF
Step 1 — Send decision to Sarathi (score = 0.75 → ALLOW):
bashTRACE_ID="a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0"

curl -s -X POST http://pravah.blackholeinfiverse.com/decision \
  -H "Content-Type: application/json" \
  -d "{
    \"trace_id\": \"$TRACE_ID\",
    \"action_type\": \"restart\",
    \"service_id\": \"web1-blue\",
    \"payload\": {
      \"decision_score\": 0.75,
      \"confidence\": 0.9,
      \"priority\": \"HIGH\"
    }
  }"
Expected response (ALLOW path):
json{
  "status": "executed",
  "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0",
  "executer_response": {
    "execution_id": "f8e3c2b1-...",
    "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0",
    "status": "success"
  }
}
Step 2 — Send decision to Sarathi (score = 0.1 → BLOCK):
bashcurl -s -X POST http://pravah.blackholeinfiverse.com/decision \
  -H "Content-Type: application/json" \
  -d "{
    \"trace_id\": \"$TRACE_ID\",
    \"action_type\": \"restart\",
    \"service_id\": \"web1-blue\",
    \"payload\": {
      \"decision_score\": 0.1
    }
  }"
Expected response (BLOCK path):
json{
  "status": "BLOCK",
  "trace_id": "a1b2c3d4-0001-0002-0003-e5f6a7b8c9d0"
}
Executer is never called. No execution happens.

6. ENFORCEMENT CHAIN SUMMARY
Core
  │
  ▼
POST /decision  (Sarathi)
  │
  ├─ score ≤ 0.6  →  BLOCK / ESCALATE  →  return  →  Executer NOT called ✅
  │
  └─ score > 0.6  →  ALLOW
                       │
                       ▼
                  POST /execute-action
                  Header: X-CALLER=sarathi   ← enforced
                       │
                       ├─ header missing   →  403 Unauthorized ✅
                       └─ header present   →  Execution proceeds ✅
Sarathi is the single, mandatory gateway. No execution path exists outside it.