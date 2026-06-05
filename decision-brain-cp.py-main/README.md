# Pravah — Autonomous DevOps Control Plane

![Status](https://img.shields.io/badge/status-operational-success)
![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Pravah** is a unified autonomous DevOps control plane that combines reinforcement learning decision intelligence with real-time infrastructure orchestration.

---

## 🧠 What is Pravah?

Pravah operates as a **single organism** with two integrated components:

- **Brain** (Decision Engine): RL-based decision generator with safety guards, cooldown logic, and reward learning
- **Body** (Control Plane): Runtime telemetry, deployment registry, orchestrator execution layer, monitoring loop

The brain is directly wired into the body — no parallel monitoring loops, no alternate telemetry pipelines, no independent deployment stores.

---

## 🚀 Architecture

```
Control Plane Telemetry → Decision Brain → Guard Enforcement 
    → Orchestrator Execution → Telemetry Verification → Learning Feedback
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| `schemas.py` | Runtime contract validation (deployment_id, cpu_percent, memory_percent, health_score, restart_count, crashed) |
| `action_scope.py` | ActionGuard — environment autonomy gates (blocked actions → NOOP) |
| `state.py` | Per-deployment state isolation + CooldownManager |
| `orchestrator.py` | HTTP client to orchestrator execution endpoints |
| `telemetry.py` | TelemetryClient + DeploymentRegistry integration |
| `rl_engine.py` | DecisionGenerator (rules + Q-learning) |
| `pipeline.py` | Single canonical decision pipeline |
| `loop.py` | PravahOrganismLoop — continuous reconciliation |

---

## 📋 Runtime Contract

The brain accepts **only** payloads matching this contract:

```json
{
  "deployment_id": "svc-01",
  "environment": "prod",
  "cpu_percent": 72.5,
  "memory_percent": 60.0,
  "health_score": 0.85,
  "restart_count": 1,
  "crashed": false,
  "timestamp": 1700000000.0,
  "metadata": {}
}
```

Missing required fields raise `ValidationError`.

---

## 🛡️ Safety Gates

Every decision passes through two safety layers:

### 1. CooldownManager
- Prevents decisions within `cooldown_seconds` (default 15s)
- Blocked decisions emit `NOOP`

### 2. ActionGuard (Environment Autonomy Gates)
- **prod**: `SCALE_UP`, `SCALE_DOWN`, `ALERT` only
- **staging**: `SCALE_UP`, `SCALE_DOWN`, `RESTART`, `ALERT`
- **dev**: `SCALE_UP`, `SCALE_DOWN`, `RESTART`, `ROLLBACK`, `ALERT`
- Actions outside allowed set → **downgraded to NOOP** (never `None`)

---

## 🔗 Integration Points

| Endpoint | Purpose | Client |
|----------|---------|--------|
| `GET /telemetry/{deployment_id}` | Fetch runtime metrics | `TelemetryClient` |
| `GET /deployments` | List active deployments | `DeploymentRegistry` |
| `POST /orchestrate` | Execute decisions | `OrchestratorClient` |

Default: `http://localhost:8000` (configurable)

---

## 🧪 Running Tests

```bash
cd pravah
python -m scripts.run_integration_test
```

### Test Coverage

- ✅ **Test A**: Multi-deployment stress (10 deployments, independent state isolation)
- ✅ **Test B**: Guard blocking → NOOP enforcement proof
- ✅ **Test C**: CooldownManager suppression
- ✅ **Test D**: End-to-end organism loop (crash → restart → recovery)

All tests pass. Logs saved in `logs/integration_run.log`.

---

## 📊 Dashboard

Open `dashboard.html` in your browser for real-time visualization:

- Live deployment metrics (CPU, memory, health)
- Decision pipeline logs
- System health trends chart
- Control buttons (Start/Pause/Reset)

---

## 🎯 RL Decision Logic

### Signal Bucketing

| Bucket | Condition |
|--------|-----------|
| `crashed` | `crashed == True` |
| `degraded` | `health_score < 0.4` or `restart_count >= 3` |
| `overloaded` | `cpu_percent >= 75` or `memory_percent >= 80` |
| `underloaded` | `cpu_percent <= 25` |
| `normal` | everything else |

### Rule-Based Fallback

- `crashed` → RESTART
- `health_score < 0.4` → RESTART
- `restart_count >= 3` → ROLLBACK
- `cpu/mem high` → SCALE_UP
- `cpu low` → SCALE_DOWN
- otherwise → NOOP

Q-learning updates per bucket with reward `+1.0` (success) or `-1.0` (failure).

---

## 🔧 Usage

### Standalone Loop

```python
from decision_brain.loop import PravahOrganismLoop
from decision_brain.telemetry import TelemetryClient, DeploymentRegistry
from decision_brain.orchestrator import OrchestratorClient

loop = PravahOrganismLoop(
    telemetry=TelemetryClient("http://control-plane:8000/telemetry"),
    registry=DeploymentRegistry("http://control-plane:8000/deployments"),
    orchestrator=OrchestratorClient("http://control-plane:8000/orchestrate"),
    poll_interval=10.0,
)
loop.run()  # runs forever
```

### Single Decision

```python
from decision_brain.pipeline import DecisionPipeline
from decision_brain.orchestrator import OrchestratorClient
from decision_brain.action_scope import ActionGuard
from decision_brain.state import AppStateStore
from decision_brain.rl_engine import DecisionGenerator

pipeline = DecisionPipeline(
    orchestrator=OrchestratorClient(),
    guard=ActionGuard(),
    store=AppStateStore(),
    generator=DecisionGenerator(enable_rl=True),
    enable_learning=True,
)

payload = {
    "deployment_id": "svc-01",
    "environment": "prod",
    "cpu_percent": 85.0,
    "memory_percent": 70.0,
    "health_score": 0.8,
    "restart_count": 0,
    "crashed": False,
}

result = pipeline.process(payload)
print(f"Action: {result.action.value}, Allowed: {result.action_allowed}")
```

---

## 📦 Dependencies

**None.** Pure Python standard library:
- `urllib` (HTTP client)
- `json`, `logging`, `dataclasses`, `enum`, `uuid`, `time`

---

## 📖 Documentation

See [HANDOVER.md](HANDOVER.md) for complete architecture documentation.

---

## 🤝 Contributors

- **Ritesh Yadav** — Decision Brain Engineer (RL engine, safety guards, cooldown logic, reward learning)
- **Shivam Pal** — Control Plane Architect (runtime contract, telemetry, deployment registry, orchestrator)
- **Vinayak** — QA Engineer (failure scenarios, crash detection, recovery validation)

---

## 📜 License

MIT License — see LICENSE file for details.

---

## 🎯 Outcome

Pravah operates as a **unified autonomous DevOps organism** where the brain and body continuously operate together:

```
Deployment Registered → Telemetry Captured → Decision Generated 
    → Action Validated → Orchestrator Executes → Telemetry Verifies 
    → Reward Learning Updates Q-table
```

**No parallel loops. No alternate pipelines. One organism.**
