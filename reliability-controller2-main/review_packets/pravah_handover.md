# review_packets/pravah_handover.md

**System:** Pravah
**Server:** 54.156.236.10
**Domain:** pravah.blackholeinfiverse.com
**Validated:** 2026-04-29
**Purpose:** Final handover review packet — complete system knowledge transfer

---

## 1. Entry Point

All flows start at Core (web1/app.py). The caller provides `trace_id` via `X-TRACE-ID` header.

```bash
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30001/login \
  -H "X-TRACE-ID: $TRACE" -d "user_id=raj"
```

This is the only way to start a trace. Pravah never creates trace_ids.

---

## 2. Core Execution Flow

```
Caller
  → POST /login with X-TRACE-ID header
  → web1/app.py posts 3 events to Monitor (session_start, user_login, page_view)

Caller
  → POST /decision to Sarathi with trace_id + score
  → sarathi/app.py posts decision signal to Monitor
  → sarathi/app.py posts enforcement signal to Monitor
  → sarathi/app.py calls executer/app.py with X-CALLER: sarathi

executer/app.py
  → posts execution signal to Monitor (before kubectl)
  → runs kubectl patch deployment/<service> -n prod
  → posts verification signal to Monitor (after kubectl)
  → posts execution_done signal to Monitor

monitor/app.py
  → receives all events via /track-event
  → converts each to one flat signal via build_flat_signal()
  → queues signals in memory
  → streams them out via /signals/stream (SSE)
```

---

## 3. Live System Flow — Real Output (2026-04-29)

Full trace `5d050c8c-c880-4e6d-9a01-8274556f30ec`:

```
data: {"signal_type": "login_detected", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450910, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:29.934096Z"}

data: {"signal_type": "user_interaction", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450910, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:30.335475Z"}

data: {"signal_type": "user_interaction", "service": "web1", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450917, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "emitted_at": "2026-04-29T08:23:30.535945Z"}

data: {"signal_type": "decision", "service": "system", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "decision": "ALLOW", "policy_reference": "score_threshold_0.6", "action": "restart", "emitted_at": "2026-04-29T08:23:30.736409Z"}

data: {"signal_type": "enforcement", "service": "sarathi", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "enforcement_status": "validated", "emitted_at": "2026-04-29T08:23:30.936904Z"}

data: {"signal_type": "execution", "service": "web1-blue", "metric": "status", "value": "RUNNING", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.137373Z"}

data: {"signal_type": "verification", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "result": "SUCCESS", "emitted_at": "2026-04-29T08:23:31.337985Z"}

data: {"signal_type": "execution_completed", "service": "web1-blue", "metric": "status", "value": "SUCCESS", "severity": "INFO", "timestamp": 1777450932, "trace_id": "5d050c8c-c880-4e6d-9a01-8274556f30ec", "trace_origin": "core", "trace_hash": "3ba9693acb64c1ca8124e49458b96723e9e5afb199a10226cf5e88872762ed32", "source": "core", "execution_id": "4a8e2bb4-bb4a-427e-a142-0f0e8e69eb9d", "emitted_at": "2026-04-29T08:23:31.538460Z"}
```

---

## 4. What Exists

| Component | What it does | Port |
|-----------|-------------|------|
| web1/app.py | Core — login, click, logout, sends events to Monitor | 30001 |
| sarathi/app.py | Policy — ALLOW/BLOCK/ESCALATE, posts decision + enforcement | 30005 |
| executer/app.py | Action — kubectl patch, posts execution + verification | 30003 |
| monitor/app.py | Observer — receives events, emits flat signals via SSE | 30004 |
| executer/governance.py | Secondary BLOCK rules (critical-service, scale_up) | — |
| monitor/signal_schema.json | Defines valid signal structure | — |
| k8s/executer-rbac.yml | kubectl access for executer pod | — |

---

## 5. Failure Cases

| Failure | Trigger | Output |
|---------|---------|--------|
| Missing trace_id at Core | No X-TRACE-ID header | HTTP 400, no signals |
| Missing trace_id at Sarathi | No trace_id in body | HTTP 400, no signals |
| Invalid service | service_id not in ALLOWED_SERVICES | verification FAILURE signal, severity CRITICAL |
| Score too low (BLOCK) | decision_score <= 0.35 | decision signal only, no execution |
| Score mid-range (ESCALATE) | 0.35 < score <= 0.6 | decision signal only, no execution |
| Direct execution bypass | No X-CALLER: sarathi | HTTP 403 unauthorized |
| Governance BLOCK | scale_up on critical-service | blocked_by_governance response |

---

## 6. Proof — Demo Script Output

Run to reproduce:
```bash
bash scripts/handover_demo.sh
```

Or manually:
```bash
# Terminal 1
curl -H "Host: pravah.blackholeinfiverse.com" -N http://54.156.236.10/signals/stream

# Terminal 2
TRACE=$(uuidgen)
curl -X POST http://54.156.236.10:30001/login -H "X-TRACE-ID: $TRACE" -d "user_id=test"
curl -X POST http://54.156.236.10:30005/decision \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\":\"$TRACE\",\"service_id\":\"web1-blue\",\"action_type\":\"restart\",\"payload\":{\"decision_score\":0.9}}"
```

Real output confirmed on 2026-04-29: 8 signals all sharing trace_id `5d050c8c-...`, `trace_origin: "core"`, `trace_hash: "3ba9693a..."`.

---

## 7. Handover Documents Index

| File | Owner | Purpose |
|------|-------|---------|
| HANDOVER_SYSTEM_OVERVIEW.md | All | What the system is, architecture |
| HANDOVER_REPO_MAP.md | All | Folder structure, entry points |
| HANDOVER_EXECUTION_FLOW.md | Shivam, Raj | Step-by-step flow with real JSON |
| HANDOVER_API_SPEC.md | All | Every endpoint documented |
| scripts/handover_demo.sh | Vinayak | Copy-paste runnable demo |
| HANDOVER_FAILURE_CASES.md | Vinayak | All failure paths with outputs |
| HANDOVER_TESTING_GUIDE.md | Vinayak | 9 tests, pass/fail criteria |
| HANDOVER_FAQ.md | All | 15 real developer questions |
| review_packets/pravah_handover.md | All | This file — master review packet |