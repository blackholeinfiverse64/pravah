# HANDOVER_REPO_MAP.md

---

## Folder Structure

```
reliability-controller2/
│
├── web1/                        # Core layer — user-facing web app (instance 1)
│   ├── app.py                   # Flask app — /login /click /logout /health
│   ├── Dockerfile               # Container build for web1
│   └── requirements.txt         # flask, requests
│
├── web2/                        # Core layer — user-facing web app (instance 2)
│   ├── app.py                   # Same structure as web1
│   ├── Dockerfile
│   └── requirements.txt
│
├── sarathi/                     # Policy engine — decision + enforcement
│   ├── app.py                   # Flask app — /decision /health
│   ├── Dockerfile
│   └── requirements.txt         # flask, requests
│
├── executer/                    # Action runner — kubectl + signal emission
│   ├── app.py                   # Flask app — /execute-action /health
│   ├── governance.py            # validate_deployment_request() — ALLOW/BLOCK rules
│   ├── core.py                  # (legacy support)
│   ├── outcome.py               # (legacy support)
│   ├── bucket.py                # (legacy support)
│   ├── mitra.py                 # (legacy support)
│   ├── sovereign_bridge.py      # (legacy support)
│   ├── workflow_service.py      # (legacy support)
│   ├── Dockerfile
│   └── requirements.txt         # flask, requests
│
├── monitor/                     # Pravah — observability layer
│   ├── app.py                   # Flask app — /track-event /signals/stream /health
│   ├── signal_schema.json       # JSON schema — validates signal structure
│   ├── signal_builder.py        # (legacy — not used in current app.py)
│   ├── aggregator.py            # (legacy — not used in current app.py)
│   ├── streamer.py              # (legacy — not used in current app.py)
│   ├── severity_engine.py       # (legacy — not used in current app.py)
│   ├── validator.py             # (legacy — not used in current app.py)
│   ├── deployment_status.py     # (legacy — not used in current app.py)
│   ├── sources/                 # (legacy — not used in current app.py)
│   │   ├── app_metrics.py
│   │   ├── cicd.py
│   │   ├── executer_logs.py
│   │   ├── infra.py
│   │   └── __init__.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── k8s/                         # Kubernetes manifests
│   ├── monitor.yml              # Monitor Deployment + NodePort Service (port 30004)
│   ├── sarathi.yml              # Sarathi Deployment + NodePort Service (port 30005)
│   ├── executer.yml             # Executer Deployment + NodePort Service (port 30003)
│   ├── executer-rbac.yml        # ServiceAccount + ClusterRole for kubectl access
│   ├── web1-blue.yml            # web1-blue Deployment
│   ├── web1-green.yml           # web1-green Deployment
│   ├── web1-service.yml         # web1 Service
│   ├── web2-blue.yml            # web2-blue Deployment
│   ├── web2-green.yml           # web2-green Deployment
│   ├── web2-service.yml         # web2 Service
│   └── staging/                 # Staging variants
│
├── review_packets/              # Compliance and review documents
│   ├── pravah_final_compliance.md
│   ├── pravah_handover.md
│   ├── pravah_live_demo.md
│   └── pravah_reality_validation.md
│
├── scripts/                     # Runnable demo scripts
│   └── handover_demo.sh
│
├── docker-compose.yml           # Local dev compose (not used in production)
│
├── HANDOVER_SYSTEM_OVERVIEW.md  # What the system is (this task)
├── HANDOVER_REPO_MAP.md         # This file
├── HANDOVER_EXECUTION_FLOW.md   # Step-by-step execution flow
├── HANDOVER_API_SPEC.md         # All endpoints documented
├── HANDOVER_FAILURE_CASES.md    # Failure + edge cases
├── HANDOVER_TESTING_GUIDE.md    # Testing guide for Vinayak
├── HANDOVER_FAQ.md              # 15 real developer questions
├── TRACE_VISIBILITY_PROOF.md    # Proof: trace_id comes from Core
├── SARATHI_STREAM_PROOF.md      # Proof: Sarathi signals in stream
├── EXECUTION_VERIFICATION_PROOF.md  # Proof: execution vs verification split
├── FULL_TRACE_STREAM_PROOF.md   # Proof: full 6-stage chain
└── REVIEW_PACKET.md             # Master review packet
```

---

## Entry Points — What to Run

| Service | File | Command | Port |
|---------|------|---------|------|
| Web1 (Core) | `web1/app.py` | `python app.py` | 5001 |
| Sarathi | `sarathi/app.py` | `python app.py` | 5001 |
| Executer | `executer/app.py` | `python app.py` | 5003 |
| Monitor | `monitor/app.py` | `python app.py` | 5004 |

---

## Active Endpoints Per Service

### web1/app.py
| Method | Path | What it does |
|--------|------|-------------|
| GET | `/` | Returns login page HTML |
| POST | `/login` | Accepts user_id + X-TRACE-ID, emits 3 events to Monitor |
| POST | `/click` | Accepts user_id + X-TRACE-ID, emits interaction_click to Monitor |
| POST | `/logout` | Emits session_end to Monitor |
| GET | `/health` | Returns `{"status": "ok"}` |

### sarathi/app.py
| Method | Path | What it does |
|--------|------|-------------|
| POST | `/decision` | Evaluates score, emits decision+enforcement, calls Executer if ALLOW |
| GET | `/health` | Returns `{"status": "healthy"}` |

### executer/app.py
| Method | Path | What it does |
|--------|------|-------------|
| POST | `/execute-action` | Runs kubectl, emits execution+verification signals |
| GET | `/health` | Returns `{"status": "ok"}` |

### monitor/app.py
| Method | Path | What it does |
|--------|------|-------------|
| POST | `/track-event` | Receives events, converts to signals, queues them |
| GET | `/signals/stream` | SSE stream — emits one signal per event |
| GET | `/health` | Returns `{"status": "ok"}` |

---

## Key Files to Know

| File | Why it matters |
|------|---------------|
| `monitor/app.py` | Core of Pravah — all signal logic lives here |
| `monitor/signal_schema.json` | Defines what a valid signal looks like |
| `sarathi/app.py` | Only place decisions are made |
| `executer/app.py` | Only place kubectl runs |
| `executer/governance.py` | Secondary ALLOW/BLOCK check before execution |
| `k8s/executer-rbac.yml` | Without this, executer cannot call kubectl |