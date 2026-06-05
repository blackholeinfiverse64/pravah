# HANDOFF TESTING — FINAL

## STREAM

```bash
curl -N http://54.156.236.10/signals/stream
```

---

## FLOW

1. Generate trace
2. Send login
3. Trigger execution

---

## EXPECTED OUTPUT

```
data: {"signal_type":"login_detected"}
data: {"signal_type":"decision"}
data: {"signal_type":"execution"}
data: {"signal_type":"verification"}
```

---

## VALIDATION

✔ Same trace_id across all signals
✔ Execution does not imply success
✔ Verification confirms result
✔ No grouped signals

---

## FINAL CONDITION

System is valid if all signals appear independently.
