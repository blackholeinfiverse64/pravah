# FAILURE DEMO

TRACE=$(uuidgen)

curl -X POST http://54.156.236.10:30005/decision \
-H "Content-Type: application/json" \
-d '{
  "trace_id": "'"$TRACE"'",
  "service_id": "invalid-service",
  "action_type": "restart",
  "payload": {"decision_score": 0.9}
}'

---

## RESULT

Stream Output:

{
  "signal_type": "execution_failed",
  "service": "invalid-service"
}

---

## VALIDATION

✔ No crash  
✔ Trace maintained  
✔ Failure visible  
✔ System stable  