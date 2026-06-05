# Pravah — Decision Brain Integration Handover

This document explains the complete integrated Pravah system for a new developer with no prior knowledge.

---

## What Pravah Is

Pravah is a unified autonomous DevOps control plane. It has two parts:

- **Body** (Shivam's control plane): runtime telemetry, deployment registry, orchestrator execution layer, monitoring loop, dashboard
- **Brain** (Ritesh's decision engine): reinforcement learning decisions, safety guards, cooldown logic, reward learning

This document covers how the brain is wired into the body.

---

## 1. Decision Brain Architecture

All decisions flow through a single linear pipeline — no alternative paths exist.

```
RuntimePayload (from Shivam's telemetry)
    ↓
schemas.py — validate against runtime contract
    ↓
state.py — CooldownManager check
    ↓
rl_engine.py — DecisionGenerator (rules + Q-learning)
    ↓
action_scope.py — ActionGuard (env autonomy gate)
    ↓
orchestrator.py — OrchestratorClient → Shivam's endpoint
    ↓
state.py — record outcome
    ↓
rl_engine.py — Q-table reward update
```

### Files

| File | Responsibility |
|------|---------------|
| `decision_brain/schemas.py` | Runtime contract — validates Shivam's payload fields |
| `decision_brain/action_scope.py` | ActionGuard — env autonomy gates, blocked → NOOP |
| `decision_brain/state.py` | AppStateStore + CooldownManager — per-deployment isolation |
| `decision_brain/orchestrator.py` | OrchestratorClient — HTTP POST to Shivam's endpoint |
| `decision_brain/telemetry.py` | TelemetryClient + DeploymentRegistry — reads Shivam's data |
| `decision_brain/rl_engine.py` | DecisionGenerator — rules + Q-learning on telemetry signals |
| `decision_brain/pipeline.py` | DecisionPipeline — single canonical loop |
| `decision_brain/loop.py` | PravahOrganismLoop — continuous reconciliation across deployments |

---

## 2. Runtime Contract (Shivam's Payload Format)

The brain accepts **only** payloads that match this contract. Any missing field raises `ValidationError`.

```json
{
  "deployment_id": "svc-01",
  "environment":   "prod",
  "cpu_percent":   72.5,
  "memory_percent": 60.0,
  "health_score":  0.85,
  "restart_count": 1,
  "crashed":       false,
  "timestamp":     1700000000.0,
  "metadata":      {}
}
```

---

## 3. Control Plane Integration Points

| Integration Point | Shivam's Endpoint | Brain Component |
|-------------------|-------------------|-----------------|
| Telemetry signals | `GET /telemetry/{deployment_id}` | `TelemetryClient` |
| Deployment registry | `GET /deployments` | `DeploymentRegistry` |
| Orchestrator execution | `POST /orchestrate` | `OrchestratorClient` |

All three default to `http://localhost:8000`. Override by passing `endpoint` to each client constructor.

### Orchestrator Response Format

```json
{
  "success": true,
  "action_executed": "SCALE_UP",
  "execution_timestamp": 1700000001.2
}
```

---

## 4. Safety Gates

Every decision passes through two safety layers before reaching the orchestrator:

### CooldownManager
- Prevents decisions within `cooldown_seconds` (default 15s) of the last decision for the same deployment
- Blocked decisions emit `NOOP` and are recorded

### ActionGuard (Environment Autonomy Gates)
- `prod`: only `SCALE_UP`, `SCALE_DOWN`, `ALERT` allowed
- `staging`: `SCALE_UP`, `SCALE_DOWN`, `RESTART`, `ALERT`
- `dev`: `SCALE_UP`, `SCALE_DOWN`, `RESTART`, `ROLLBACK`, `ALERT`
- Any action outside the allowed set is **downgraded to NOOP** — never returns `None`

Log proof of blocked actions:
```
[GUARD] BLOCKED deployment=svc-01 requested=RESTART → NOOP reason=RESTART blocked in prod → NOOP
```

---

## 5. Autonomy Loop Explanation

`PravahOrganismLoop` runs the reconciliation loop:

1. Calls `DeploymentRegistry.list_active()` — reads from Shivam's registry
2. For each deployment, calls `TelemetryClient.fetch(deployment_id)` — reads real metrics
3. Passes payload to `DecisionPipeline.process()` — full brain pipeline
4. Orchestrator executes the action
5. Q-table updated with reward based on execution success

```python
loop = PravahOrganismLoop(
    telemetry=TelemetryClient(),       # Shivam's telemetry
    registry=DeploymentRegistry(),     # Shivam's registry
    orchestrator=OrchestratorClient(), # Shivam's orchestrator
    poll_interval=10.0,
)
loop.run()  # runs forever
```

---

## 6. Multi-Deployment State Isolation

Each deployment has completely isolated state in `AppStateStore`:
- Separate decision history (capped at 100 records)
- Separate Q-table
- Separate cooldown timer
- Garbage collected after 1 hour of inactivity

Decisions for `svc-01` cannot influence `svc-02`.

---

## 7. RL Decision Logic

Signals used for bucketing:

| Bucket | Condition |
|--------|-----------|
| `crashed` | `crashed == True` |
| `degraded` | `health_score < 0.4` or `restart_count >= 3` |
| `overloaded` | `cpu_percent >= 75` or `memory_percent >= 80` |
| `underloaded` | `cpu_percent <= 25` |
| `normal` | everything else |

Rule-based decisions (deterministic fallback):
- `crashed` → RESTART
- `health_score < 0.4` → RESTART
- `restart_count >= 3` → ROLLBACK
- `cpu/mem high` → SCALE_UP
- `cpu low` → SCALE_DOWN
- otherwise → NOOP

Q-learning updates the Q-table per bucket per deployment using reward `+1.0` (success) or `-1.0` (failure).

---

## 8. Running the Integration Tests

```bash
cd "task no 19/pravah"
python scripts/run_integration_test.py
```

Four tests run:
- **Test A**: 10 deployments × 4 scenarios — verifies isolation
- **Test B**: Guard blocking → NOOP enforcement proof
- **Test C**: CooldownManager suppression proof
- **Test D**: Full end-to-end organism loop (crash → restart → recovery)

---

## 9. Connecting to Shivam's Live Control Plane

When Shivam's server is running, no code changes are needed. Just run:

```python
from decision_brain.loop import PravahOrganismLoop
from decision_brain.telemetry import TelemetryClient, DeploymentRegistry
from decision_brain.orchestrator import OrchestratorClient

loop = PravahOrganismLoop(
    telemetry=TelemetryClient("http://<shivam-host>:8000/telemetry"),
    registry=DeploymentRegistry("http://<shivam-host>:8000/deployments"),
    orchestrator=OrchestratorClient("http://<shivam-host>:8000/orchestrate"),
    poll_interval=10.0,
)
loop.run()
```

---

## 10. What Ritesh Built (Cumulative)

| Task | Contribution |
|------|-------------|
| Prior tasks | RL engine, Q-learning, safety guards, cooldown logic, reward system |
| Task 19 | Full integration — brain wired to Shivam's body. Pravah now operates as a unified autonomous DevOps organism |
