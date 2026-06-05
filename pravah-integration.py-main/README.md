# Pravah - Hardened Autonomous DevOps Engine

## Architecture

Pravah implements a production-safe, persistent, verified autonomy loop:

**Observe → Decide → Execute → Verify → Learn → Display**

## Core Components

### 1. Q-Table Persistence (`rl/q_table_store.py`)
- Loads Q-table on startup from `data/q_table.json`
- Persists after each update (DEV only)
- Environment-aware: DEV (read/write), STAGE/PROD (read-only)

### 2. State Encoder (`rl/state_encoder.py`)
- Converts raw telemetry floats into discrete state buckets
- CPU: low (<40%) | medium (<75%) | high (≥75%)
- Memory: safe (<60%) | elevated (<85%) | critical (≥85%)
- Health: healthy (≥0.8) | degraded (≥0.5) | failing (<0.5)

### 3. Reward Engine (`rl/reward_engine.py`)
- Automated reward calculation from telemetry deltas
- +2: health improved
- +1: CPU stabilized
- -2: restart increased
- -5: crash or execution failure

### 4. Action Guard (`guard/action_guard.py`)
Hard-coded environment constraints:
- **DEV**: All actions allowed
- **STAGE**: Deterministic only (scale_up, scale_down, noop)
- **PROD**: Scale only, no destructive actions (stop, redeploy, restart)

### 5. Cooldown Manager (`guard/cooldown_manager.py`)
- Same action blocked within 60 seconds
- Max 3 actions per 5 minutes per deployment
- Prevents action storms

### 6. RL Agent (`rl/rl_agent.py`)
- Epsilon-greedy policy (ε=0.1 in DEV, 0.0 in STAGE/PROD)
- Q-learning: α=0.1, γ=0.9
- Integrates guard, cooldown, and Q-table

### 7. Execution Verifier (`rl/execution_verifier.py`)
- Captures pre-action telemetry
- Executes action via orchestrator
- Captures post-action telemetry
- Computes state delta
- Returns verified/failed status

### 8. Autonomy Loop (`rl/autonomy_loop.py`)
Unified 30-second cycle:
1. Pull telemetry
2. Encode state
3. RL decision
4. Guard validation
5. Orchestrator execution
6. Verification
7. Reward computation
8. Q-table update (DEV only)
9. Persist snapshot

### 9. Main Service (`main.py`)
- FastAPI with background autonomy loop
- Starts on service launch
- Endpoints: `/health`, `/q-table`, `/deployments`

## Environment Behavior

| Feature | DEV | STAGE | PROD |
|---------|-----|-------|------|
| Q-table updates | ✓ | ✗ | ✗ |
| Epsilon exploration | 0.1 | 0.0 | 0.0 |
| Destructive actions | ✓ | ✗ | ✗ |
| Scale actions | ✓ | ✓ | ✓ |

## Integration Points

### Telemetry Client (`clients/telemetry_client.py`)
Interface: `get_metrics(deployment_id) -> dict`
Returns: cpu_percent, memory_percent, health_score, restart_count, crashed

### Orchestrator Client (`clients/orchestrator_client.py`)
Interface: `execute_action(deployment_id, action) -> dict`
Returns: success, action, deployment_id

### Deployment Store (`store/deployment_store.py`)
Interface: `get_active_deployments() -> list`
Returns: List of active deployment objects

## Running Pravah

```bash
# Set environment
export ENVIRONMENT=DEV  # or STAGE, PROD

# Install dependencies
pip install -r requirements.txt

# Start service
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Verification

### Check Health
```bash
curl http://localhost:8000/health
```

### View Q-Table
```bash
curl http://localhost:8000/q-table
```

### Register Deployment
```bash
curl -X POST http://localhost:8000/deployments \
  -H "Content-Type: application/json" \
  -d '{"id": "app-1", "name": "test-app"}'
```

## Stability Test

Run for 60 minutes and verify:
- Q-table persists across restarts
- Actions respect environment gates
- Cooldowns prevent storms
- Rewards auto-calculate
- Loop runs continuously

## Demo Flow

1. Inject failure (high CPU, low health)
2. RL selects action (e.g., scale_up)
3. Action verified by orchestrator
4. Reward auto-calculated from delta
5. Q-table updated (DEV only)
6. Dashboard reflects truth

## File Structure

```
pravah/
├── rl/
│   ├── q_table_store.py       # Persistent Q-table
│   ├── state_encoder.py       # Discrete state buckets
│   ├── reward_engine.py       # Automated rewards
│   ├── rl_agent.py            # Q-learning agent
│   ├── execution_verifier.py  # Pre/post verification
│   └── autonomy_loop.py       # Unified loop
├── guard/
│   ├── action_guard.py        # Environment constraints
│   └── cooldown_manager.py    # Rate limiting
├── clients/
│   ├── telemetry_client.py    # Telemetry interface
│   └── orchestrator_client.py # Orchestrator interface
├── store/
│   └── deployment_store.py    # Deployment state
├── data/
│   └── q_table.json           # Persisted Q-table
├── main.py                    # FastAPI service
├── requirements.txt
└── README.md
```

## No Simulation. Production-Safe. Truthful.
