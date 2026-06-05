# REVIEW_PACKET — PRAVAH FINAL

**System:** Pravah
**Server:** 54.156.236.10
**Domain:** pravah.blackholeinfiverse.com
**Validated:** 2026-04-29
**Status:** Integration-ready

---

## SYSTEM DEFINITION

Pravah is a non-interpretive, trace-complete observability layer.
It observes events across Core → Sarathi → Executer and emits flat, trace-linked signals.
It does NOT interpret. It does NOT conclude. It does NOT infer.

---

## ARCHITECTURE
Core/Web  →  [login event + trace_id via X-TRACE-ID]
→  Monitor /track-event  →  signal_queue  →  SSE stream
Sarathi   →  [decision signal]    →  Monitor
→  [enforcement signal] →  Monitor
→  Executer /execute-action (X-CALLER: sarathi)
Executer  →  [execution signal]   →  Monitor
→  kubectl patch
→  [verification signal] →  Monitor

---

## ENTRY POINT

All flows begin at Core (Web layer).
Core supplies trace_id via X-TRACE-ID header.
Pravah never generates trace_id silently.

---

## STREAM FORMAT (LOCKED)

Each SSE data: line = exactly one flat independent signal. No wrappers. No blobs.

```json
{
  "signal_type":  "...",
  "service":      "...",
  "metric":       "status",
  "value":        "RUNNING | SUCCESS | FAILURE",
  "severity":     "INFO | WARN | CRITICAL",
  "timestamp":    1777450932,
  "trace_id":     "5d050c8c-c880-4e6d-9a01-8274556f30ec",
  "trace_origin": "core",
  "trace_hash":   "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32",
  "source":       "core",
  "emitted_at":   "2026-04-29T08:23:29.934096Z"
}
```

---

## SIGNAL ORDER FOR ONE TRACE

login_detected      ← Core
user_interaction    ← Core
decision            ← Sarathi (ALLOW + policy_reference)
enforcement         ← Sarathi (validated — before execution)
execution           ← Executer (RUNNING — no success implied)
verification        ← Executer (SUCCESS/FAILURE — confirmed)
execution_completed ← Executer (final state)


---

## WHAT WAS REMOVED

| Removed | Reason |
|---------|--------|
| `causal_chain` | Interpretation — inferred from data |
| `correlation{}` | Grouping — inferred across events |
| `signals[]` wrapper | Blob format — violates flat signal rule |

---

## SECURITY

- `/execute-action` requires `X-CALLER: sarathi` header
- Missing header → HTTP 403 `{"error":"unauthorized"}`
- Proven live: `curl -X POST http://54.156.236.10:30003/execute-action` → 403

---

## PROOF FILES

- `TRACE_VISIBILITY_PROOF.md`
- `SARATHI_STREAM_PROOF.md`
- `EXECUTION_VERIFICATION_PROOF.md`
- `FULL_TRACE_STREAM_PROOF.md`
- `review_packets/pravah_final_compliance.md`

---

## REPRODUCTION (curl only)

```bash
# Terminal 1 — open stream
curl -H "Host: pravah.blackholeinfiverse.com" -N http://54.156.236.10/signals/stream

# Terminal 2
TRACE=$(uuidgen)

curl -X POST http://54.156.236.10:30001/login \
  -H "X-TRACE-ID: $TRACE" -d "user_id=raj"

curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.9}}"
```