# PRAVAH — LIVE OBSERVABILITY SYSTEM

Pravah is a real-time observability layer that streams trace-linked system behavior across user, decision, and execution layers.

---

## ARCHITECTURE

Core/Web → Monitor → Sarathi → Executer → Monitor → Stream

---

## COMPONENTS

- Web Layer → user interaction
- Monitor → event ingestion + streaming
- Sarathi → policy decision (ALLOW/BLOCK)
- Executer → real infrastructure actions (Kubernetes)

---

## FEATURES

- Real-time streaming (SSE)
- Trace-linked observability
- Policy enforcement layer (Sarathi)
- Infrastructure execution (kubectl)
- Failure visibility
- Concurrency support

---

## RUN SYSTEM

### Stream
curl -H "Host: pravah.blackholeinfiverse.com" \
-N http://54.156.236.10/signals/stream

---

### Trigger Flow

TRACE=$(uuidgen)

curl -X POST http://54.156.236.10:30001/login \
-H "X-TRACE-ID: $TRACE" \
-d "user_id=test"

curl -X POST http://54.156.236.10:30001/click \
-H "X-TRACE-ID: $TRACE" \
-d "user_id=test&session_id=s_1"

curl -X POST http://54.156.236.10:30005/decision \
-H "Content-Type: application/json" \
-d '{
  "trace_id": "'"$TRACE"'",
  "service_id": "web1-blue",
  "action_type": "restart",
  "payload": {"decision_score": 0.9}
}'

---

## RESULT

Stream shows:

- login_detected
- user_interaction
- decision_made
- execution_completed

---

## SECURITY

Direct execution is blocked:
/execute-action → requires X-CALLER=sarathi

---

## STATUS

Production-demo ready.