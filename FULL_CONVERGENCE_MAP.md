# FULL_CONVERGENCE_MAP

**Effort estimate:** 5–8 hours (analysis + stakeholder alignment)

**Purpose:** Produce a convergence map across Rayyan (Reliability/Observability Stream), Ritesh (Sarathi Enforcement + Decision Brain), and Shivam (Multi-Agent Control Plane + Dashboard). Identify overlap, duplication, divergence, schema/contract mismatches, replay/runtime assumptions, and produce canonical recommendations and which components to retire/merge. Include before & after topology diagrams.

---

## Executive summary
- Rayyan: real-time observability streaming system designed for per-trace isolation and FIFO-ordered trace handling. Provides a high-integrity event stream for monitoring and observability.
- Ritesh: enforcement and decision systems (Sarathi enforcement, Decision Brain). Responsible for policy evaluation, deterministic governance, decision generation, and RL agent logic.
- Shivam: multi-agent control plane and dashboard stack (control_plane, integration bridge, dashboard frontend). Orchestrates agents, exposes runtime and management APIs, UI/UX for operators.

High-level conclusions:
- The three systems have complementary goals but overlapping telemetry and control concerns.
- Primary duplication: multiple dashboard/monitoring implementations and partial telemetry generators (hash-based simulators vs real collectors).
- Canonicalization: Rayyan should be the canonical observability stream (SSE/OTLP) for metrics/traces/events; Ritesh must remain canonical for enforcement and decision contracts; Shivam's control plane should be canonical for action orchestration and app registry.
- Immediate merges: routing of observability events from Shivam and Ritesh into Rayyan; standardize telemetry schema and decision/execution contracts; retire hash-based synthetic metric generators and replace with collectors.

---

## 1. What Rayyan built
(derived from project notes)
- Core capability: Real-time event stream with per-trace FIFO isolation.
- Input: instrumented services, trace-linked events.
- Output: ordered SSE events, trace-aligned telemetry, streaming signals consumed by monitoring and replay.
- Guarantees: No trace mixing (mathematical proof in CONCURRENCY_PROOF.md), high-fidelity ordering and isolation, low-latency delivery.
- Use cases: observability, live monitoring dashboards, trace-driven replay, alerting pipeline.

Evidence & artifacts:
- CONCURRENCY_PROOF.md (proof of per-trace isolation and ordering)
- Observability stream components (repo: reliability-controller2-main / pravah-integration etc.)

Primary contracts:
- Event envelope: { trace_id, timestamp, event_type, payload }
- FIFO queue semantics per trace_id
- Delivery via SSE and persisted journals for replay

Assumptions:
- All instrumented components propagate a `trace_id` header.
- Producers will not batch traces across contexts.

---

## 2. What Ritesh built
(Ritesh responsibilities in repo)
- Sarathi enforcement: header-based X-CALLER enforcement, deterministic policy checks, admission control (403 on bypass), and policy snapshotging.
- Decision Brain: RL agent (Q-table in DEV), reward engine, state encoder, action guards (DEV/ STAGE/ PROD distinctions), cooldown manager, autonomy loop.
- Execution lineage & replay support: functions to replay/verify execution lines and to build execution contracts.

Evidence & artifacts:
- `sarathi.router` integrations in `agent_runtime.py` and `agent` packages
- Decision engine in `decision_brain` repo (Q-table persistence, reward engine)
- `contracts/decision_contract.py`, `contracts/execution_contract.py`
- `control_plane/core/execution_lineage.py` (replay and verify functions)

Primary contracts:
- Decision contract: { decision_id, environment, selected_action, reason, confidence, timestamp }
- Execution contract: admission, action, signer, hash chain for lineage
- Enforcement headers: `X-CALLER`, `X-TRACE-ID`

Assumptions:
- `trace_id` always present; enforcement uses it to reason about provenance
- Control plane will call executer with signed requests (signed_post)

---

## 3. What Shivam built
(Shivam responsibilities in repo)
- Multi-Agent Control Plane (`multi-agent-control-plane-main`): agent runtime, orchestrator, executer, app registry, runtime polling, integration bridge to Decision Brain.
- Dashboard frontend (Next.js) and backend FastAPI aggregation for a single UI payload (`/live-dashboard`).
- Monitoring utilities: `monitoring/runtime_poller.py` CLI for polling health endpoints and writing runtime payloads; file-based `data/runtime_metrics.json` consumption by dashboard builder.
- Ingestion API: `/ingest-link` for adding repos to monitor (currently synthetic metadata generation).

Evidence & artifacts:
- `control_plane/backend/app/main.py` (payload builder)
- `monitoring/runtime_poller.py` (poller)
- `control_plane/config/apps_registry.json` (app registry)
- Dashboard frontend (`dashboard/frontend`) and `services/api.ts`
- `integration_bridge.py` connecting to control plane and decision brain

Primary contracts:
- Runtime payload contract in `monitoring/runtime_payload_poller.csv` and expected `data/runtime_metrics.json`
- Dashboard aggregation JSON (`/live-dashboard`) consumed by UI

Assumptions:
- In-memory ingestion acceptable for demo; runtime metrics may be file-based or injected
- Integration to control plane and decision brain is optional / best-effort in current implementation

---

## 4. Where overlap exists
- Observability telemetry: Rayyan's event stream and Shivam's runtime poller intend to capture similar runtime signals (latency, errors, health). Both claim to be sources of truth for telemetry.
- Decision records: Ritesh's Decision Brain and Shivam's dashboard both record decisions (Ritesh provides decision contracts; Shivam retains an in-memory `_RECENT_DECISIONS`).
- Dashboarding: Multiple dashboards exist (UNIFIED-DASHBOARD.PY-main, `dashboard/frontend`) with overlapping visualization responsibilities.

---

## 5. Where duplication exists
- Two monitoring/dashboard codebases (UNIFIED-DASHBOARD vs `dashboard/frontend`) — duplicate UI/UX and aggregation code.
- Synthetic telemetry generation: Shivam's `_generate_link_metadata()` duplicates the appearance of real telemetry that Rayyan would supply.
- Decision logs: In-memory `_RECENT_DECISIONS` duplicate Decision Brain's persistent decision logs (if Decision Brain persists decisions separately).

---

## 6. Where architecture diverges
- Rayyan uses a streaming-first architecture (SSE, per-trace queues) with replay and persistence.
- Shivam's control plane currently uses polling and file-based inputs (CSV/JSON) for runtime metrics and an aggregator endpoint for UI, not a streaming-first model.
- Ritesh expects synchronous decision/execution contracts with enforcement; Shivam's dashboard expects a single aggregated snapshot.

---

## 7. Where contracts mismatch
- Trace propagation: Rayyan requires `trace_id` everywhere; Shivam's runtime poller emits payloads with `app, env, state, latency_ms` but may not include `trace_id`.
- Decision contract fields: Ritesh expects full decision objects saved and replayable with cryptographic lineage; Shivam may store simple `selected_action` strings in `_RECENT_DECISIONS`.
- Event envelope format: Rayyan event envelope (trace_id, timestamp, event_type, payload) vs Shivam's dashboard objects (free-form JSON). No shared schema.

---

## 8. Where schema drift exists
- `runtime_payload` in `monitoring/runtime_poller.py` uses `app, env, state, latency_ms, errors_last_min, workers` (canonical) whereas Rayyan event envelope includes `trace_id` and richer fields.
- Dashboard payload includes many ad-hoc fields (`policy_evolution.metrics`, `enhanced_telemetry.cost`) not present in Rayyan's event model.
- Decision/execution lineage schemas differ in depth and cryptographic fields (Ritesh uses hashes, signatures) vs Shivam's simpler logs.

---

## 9. Where replay assumptions differ
- Rayyan: replay via persisted SSE/journal with per-trace FIFO, deterministic replay guaranteed.
- Shivam: replay uses `logs/decisions/decision_log.json` and `logs/orchestrator/execution_log.json` reading last lines — less formal, lacks lineage verification.
- Ritesh: replay expects verified hash chain and FSM integrity (`replay_execution_lineage` + `verify_execution_lineage`).

---

## 10. Where runtime assumptions differ
- Rayyan: live streaming, continuous trace propagation, no mixing across traces.
- Shivam: polling model, file-based runtime metrics, occasional CLI poller runs; not continuous stream.
- Ritesh: enforcement headers and synchronous decisioning with admission control; expects `X-CALLER` and `X-TRACE-ID` propagated in requests.

---

## 11. What becomes canonical
Proposed canonical division (recommended):
- Observability stream & event model: **Rayyan** (canonical producer and replayable event store). Rayyan's event envelope becomes system-wide standard.
- Enforcement / Decision contracts: **Ritesh** (Sarathi + Decision Brain) remains canonical for decision/execution contracts, policy snapshotting, and lineage verification.
- Action orchestration & registry: **Shivam** (Control Plane) is canonical for app registry, executer, and orchestration APIs.
- Dashboard & visualization: Grafana for SRE timeseries dashboards; a curated Next.js executive dashboard that reads canonical aggregated endpoints (produced by a lightweight aggregator that merges Rayyan + Ritesh + Shivam sources).

---

## 12. What gets retired
- Synthetic metric generators (e.g. `_generate_link_metadata()` and hash-based aggregates) should be retired or moved to a dev/demo toggle behind a feature flag.
- Duplicate dashboard codebases should be consolidated into one canonical visualization layer (keep one UI implementation per audience: Grafana for SREs, Next.js for execs).
- In-memory-only decision caches as sole source of truth (persist decisions to Decision Brain or canonical journal store).

---

## 13. What must merge
- Telemetry ingestion paths: merge Shivam's runtime poller output into Rayyan's ingestion pipeline (or have poller export OTLP to Rayyan collector).
- Event schema: adopt Rayyan event envelope as canonical and adapt `monitoring/runtime_poller.py` to emit the envelope (add `trace_id` when available).
- Alerts & rules: centralize alerting rules in a shared repo; merge common SLO templates.
- Dashboard aggregation: create an aggregator service that reads Rayyan (events), Decision Brain (decisions & lineage), and Control Plane (app registry) and produces a small, stable UI API consumed by Next.js.

---

## 14. Before / After topology diagrams

**Before topology** (current state — simplified):

```mermaid
flowchart LR
  subgraph Rayyan[Rayyan - Observability Stream]
    RProducers[Instrumented Services]
    RStream[SSE / per-trace queue]
    RStore[Replay Journal]
  end

  subgraph Ritesh[Decision & Enforcement]
    Sarathi[Sarathi Enforcement]
    DecisionBrain[Decision Brain]
    Lineage[Execution Lineage]
  end

  subgraph Shivam[Control Plane & Dashboard]
    Poller[Runtime Poller]
    AppRegistry[apps_registry.json]
    Dashboard[Next.js Dashboard]
    Aggregator[FastAPI Aggregator]
  end

  RProducers --> RStream --> RStore
  RProducers --> DecisionBrain
  DecisionBrain --> Sarathi
  Poller --> Aggregator
  AppRegistry --> Aggregator
  Aggregator --> Dashboard
  DecisionBrain --> Aggregator

  note right of Poller
    Poller writes CSV/JSON to disk
    Aggregator reads files if present
  end

  note left of RStream
    Rayyan provides canonical events
  end
```

**After topology** (proposed canonical integration):

```mermaid
flowchart LR
  subgraph Producers[Instrumented Services]
    Services[Services (apps)]
    SDKs[OTel SDKs/exporters]
  end

  subgraph Observability[Rayyan - Canonical Stream]
    OTLP[OTLP Collector]
    RStream[SSE / Kafka / Journal]
    Prom[Prometheus / TSDB]
    Traces[Tempo/Jaeger]
    Logs[Loki/ELK]
  end

  subgraph Control[Shivam - Control Plane]
    AppRegistry[App Registry (canonical)]
    Orchestrator[Executer/Orchestrator]
    PollerAgent[Runtime Poller (agent)]
  end

  subgraph Decision[Ritesh - Enforcement & Decision Brain]
    DecisionBrain[Decision Brain (canonical)]
    Sarathi[Sarathi Enforcement]
    Lineage[Lineage Store & Verifier]
  end

  Services --> SDKs --> OTLP
  PollerAgent --> OTLP
  OTLP --> Prom
  OTLP --> Traces
  OTLP --> Logs
  OTLP --> RStream

  DecisionBrain --> Lineage
  DecisionBrain --> Sarathi
  Lineage --> RStream

  AppRegistry --> Orchestrator
  Orchestrator --> DecisionBrain
  RStream --> Aggregator[Aggregator Service]
  Aggregator --> Dashboard[Next.js Exec Dashboard]
  Prom --> Grafana[Grafana SRE Dashboards]
  Traces --> Jaeger
  Logs --> Loki

  note right of Aggregator
    Aggregator composes curated data from Prometheus, RStream, Decision API, and App Registry
  end
```

---

## 15. Implementation roadmap (5–8 hours pilot plan)
1. Alignment session (30–60m) with Rayyan, Ritesh, Shivam: confirm endpoints, minimal schema, and pilot service.
2. Pilot: instrument `local-backend` and run `monitoring/runtime_poller.py --service local-backend --base-url http://127.0.0.1:8000 --iterations 3` to produce `runtime_payload_poller.csv` and `data/runtime_metrics.json`.
3. Modify `monitoring/runtime_poller.py` (small patch) to emit Rayyan envelope (optional dev branch) or add lightweight translator that converts CSV/JSON to Rayyan event envelope and posts to Rayyan ingestion endpoint.
4. Implement aggregator service (small FastAPI) that reads from Prometheus + Rayyan decision API + App Registry and serves a stable `/ui-aggregate` JSON for Next.js.
5. Migrate alert rules to shared Git repo and define 5 canonical rules for pilot.

Deliverables after pilot:
- `FULL_CONVERGENCE_MAP.md` (this document)
- Pilot artifacts (runtime metrics, aggregator endpoint, example alert rules)
- Meeting notes and agreed owners

---

## 16. Risks & mitigations
- Risk: differing trace_id propagation policies → Mitigation: adopt strict `X-TRACE-ID` propagation and verify at ingress.
- Risk: duplicated dashboards cause confusion → Mitigation: mark one as canonical and schedule consolidation.
- Risk: persistence differences (in-memory vs durable) → Mitigation: decision logs must be centralized in Decision Brain or lineage store.

---

## 17. Next steps & owners
- Schedule 60m alignment meeting: attendees Rayyan owner, Ritesh, Shivam Pal, SRE lead (Owner: You / Shivam Pal)
- Confirm Rayyan ingestion endpoint and example event envelope (Owner: Rayyan)
- Choose pilot service: `local-backend` (Owner: Shivam)
- Run runtime poller and wire to Rayyan for pilot (Owner: Ops / Shivam)
- Implement aggregator prototype (Owner: Integration engineer)

---

*End of FULL_CONVERGENCE_MAP.md*