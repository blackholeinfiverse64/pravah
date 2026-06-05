# DEMO STEPS — FULL REPRODUCIBLE FLOW (FINAL)

## STEP 1 — START STREAM

```bash
curl -N http://pravah.blackholeinfiverse.com/signals/stream
```

---

## STEP 2 — GENERATE TRACE

```bash
TRACE=$(uuidgen)
echo $TRACE
```

---

## STEP 3 — LOGIN EVENT

```bash
curl -X POST http://pravah.blackholeinfiverse.com/track-event \
-H "Content-Type: application/json" \
-d "{
  \"user_id\":\"demo\",
  \"event_type\":\"user_login\",
  \"timestamp\":$(date +%s),
  \"session_id\":\"sess-demo\",
  \"trace_id\":\"$TRACE\"
}"
```

---

## STEP 4 — EXECUTION VIA SARATHI

```bash
curl -X POST http://pravah.blackholeinfiverse.com/decision \
-H "Content-Type: application/json" \
-d "{
  \"trace_id\":\"$TRACE\",
  \"service_id\":\"web1-blue\",
  \"action_type\":\"restart\",
  \"payload\":{\"decision_score\":0.9}
}"
```

---

## STEP 5 — OBSERVE STREAM

Expected sequence:

```
data: {login_detected}
data: {decision}
data: {enforcement}
data: {execution}
data: {verification}
```

---

## RULE

Each signal appears independently.
No nested or grouped payloads exist.
