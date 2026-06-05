# PRAVAH — LIVE PRODUCTION DEMO (FINAL)

## 1. SYSTEM ACCESS

Domain:
http://pravah.blackholeinfiverse.com

Fallback:
http://54.156.236.10

---

## 2. STREAM ENDPOINT

```bash
curl -N http://54.156.236.10/signals/stream
```

This opens a live Server-Sent Events (SSE) stream.
Each line represents a single signal.

---

## 3. TRACE DEMONSTRATION

Trace ID used:
544e1170-288e-4467-984e-3816fa074f13

---

## 4. LIVE STREAM OUTPUT (REAL — FINAL FORMAT)

Each line below is emitted independently.

```
data: {"signal_type":"login_detected","service":"web1","metric":"status","value":"RUNNING","severity":"INFO","timestamp":1777450910,"trace_id":"544e1170-288e-4467-984e-3816fa074f13","trace_origin":"core","source":"core"}

data: {"signal_type":"decision","service":"system","metric":"status","value":"RUNNING","severity":"INFO","timestamp":1777450932,"trace_id":"544e1170-288e-4467-984e-3816fa074f13","trace_origin":"core","source":"core","decision":"ALLOW","policy_reference":"score_threshold_0.6","action":"restart"}

data: {"signal_type":"enforcement","service":"sarathi","metric":"status","value":"RUNNING","severity":"INFO","timestamp":1777450932,"trace_id":"544e1170-288e-4467-984e-3816fa074f13","trace_origin":"core","source":"core","enforcement_status":"validated"}

data: {"signal_type":"execution","service":"web1-blue","metric":"status","value":"RUNNING","severity":"INFO","timestamp":1777450932,"trace_id":"544e1170-288e-4467-984e-3816fa074f13","trace_origin":"core","source":"core","execution_id":"4a8e2bb4"}

data: {"signal_type":"verification","service":"web1-blue","metric":"status","value":"SUCCESS","severity":"INFO","timestamp":1777450932,"trace_id":"544e1170-288e-4467-984e-3816fa074f13","trace_origin":"core","source":"core","execution_id":"4a8e2bb4","result":"SUCCESS"}
```

---

## 5. KEY OBSERVATIONS

* Each signal is emitted independently
* No signal grouping or aggregation
* No interpretation logic present
* trace_id remains identical across all signals
* execution does NOT imply success
* verification confirms outcome

---

## 6. VALIDATION

✔ Real-time stream
✔ Real infrastructure execution
✔ Trace continuity maintained
✔ No inferred fields

---

## 7. FINAL STATEMENT

Pravah emits only observed facts.
Each signal is independent, verifiable, and trace-linked.
No interpretation, correlation, or aggregation exists in the system.
