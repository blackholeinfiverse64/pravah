# HANDOVER_SYSTEM_OVERVIEW.md

---

## What Pravah Is

Pravah is an observability layer that watches what happens across a set of microservices and streams it out in real time as structured signals.
It sits passively — it never makes decisions, never triggers actions, never modifies anything.
Every signal it emits is a direct record of something that already happened.

---

## What Pravah Does

1. Receives raw events from three layers: Core (Web), Sarathi (Decision), Executer (Action)
2. Converts each event into one flat, structured signal
3. Streams those signals out in real time over HTTP (SSE — Server-Sent Events)
4. Every signal carries the original trace_id so every event across all layers can be linked

---

## What Pravah Does NOT Do

- Does NOT make any decisions
- Does NOT trigger any actions
- Does NOT generate trace_ids (they come from Core)
- Does NOT interpret, infer, group, or summarize events
- Does NOT store data permanently (in-memory queue only)
- Does NOT modify any deployment directly

---

## Architecture — Full Flow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1 — User hits web app (Core)                          │
│  web1/app.py receives login request                         │
│  trace_id comes from caller via X-TRACE-ID header           │
│  Web sends login events to Monitor                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2 — Sarathi decides (Policy Engine)                   │
│  sarathi/app.py receives POST /decision                     │
│  Evaluates decision_score against threshold (0.6)           │
│  ALLOW / BLOCK / ESCALATE                                   │
│  Emits: decision signal → Monitor                           │
│  Emits: enforcement signal → Monitor (if ALLOW)             │
└──────────────────────┬──────────────────────────────────────┘
                       │ (only if ALLOW)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3 — Executer runs the action                          │
│  executer/app.py receives POST /execute-action              │
│  Only accepts calls with X-CALLER: sarathi header           │
│  Runs: kubectl patch deployment/... -n prod                 │
│  Emits: execution signal → Monitor (before kubectl)         │
│  Emits: verification signal → Monitor (after kubectl)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4 — Monitor streams signals                           │
│  monitor/app.py receives all events via POST /track-event   │
│  Converts each event into one flat signal                   │
│  Pushes to in-memory queue                                  │
│  GET /signals/stream emits them one per SSE event           │
└─────────────────────────────────────────────────────────────┘
```

---

## Layers Explained

### Core (web1, web2)
The user-facing web application. Handles login, click, logout.
Generates or receives trace_id from the caller. Sends user events to Monitor.
Files: `web1/app.py`, `web2/app.py`

### Sarathi
The policy engine. Receives a decision request with a score.
Decides ALLOW / BLOCK / ESCALATE based on `score > 0.6`.
If ALLOW: posts decision signal, posts enforcement signal, then calls Executer.
If not ALLOW: posts decision signal only, returns status — no execution happens.
Files: `sarathi/app.py`

### Executer
The action runner. Runs `kubectl patch` to restart or scale a deployment.
Will only accept requests that come with `X-CALLER: sarathi` header.
Posts execution signal before running, verification signal after.
Files: `executer/app.py`, `executer/governance.py`

### Monitor (Pravah)
The observer. Receives all events from all layers via `/track-event`.
Converts them to flat signals and queues them.
Streams them out one at a time via `/signals/stream`.
Files: `monitor/app.py`, `monitor/signal_schema.json`

---

## Live System

| Component | Internal Port | External NodePort |
|-----------|-------------|-------------------|
| Web1      | 5001        | 30001             |
| Sarathi   | 5001        | 30005             |
| Executer  | 5003        | 30003             |
| Monitor   | 5004        | 30004             |

Server IP: `54.156.236.10`
Domain: `pravah.blackholeinfiverse.com`