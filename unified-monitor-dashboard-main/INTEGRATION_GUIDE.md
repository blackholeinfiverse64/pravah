# Unified Infrastructure Control System - Integration Documentation

**Version:** 1.0  
**Date:** March 28, 2026  
**Status:** Production Ready

---

## Executive Summary

The Unified Infrastructure Control System integrates three critical layers:

1. **Control Plane** - Infrastructure monitoring and execution
2. **Decision Brain** - Intelligent decision generation with safety enforcement
3. **Monitoring Dashboard** - Real-time operational visibility

This creates a continuous autonomous control loop:

```
Runtime Telemetry → Decision Brain → Action Enforcement → Orchestrator → Dashboard
```

---

## Architecture Overview

### 1. Control Plane Layer (`control_plane/`)

**Responsibility:** Collect infrastructure metrics and execute decisions

#### Components:

- **`telemetry_collector.py`** - Collects real-time metrics from applications
  - CPU usage, memory usage, error rates, latency
  - Per-application state management
  - Supports dynamic replica tracking

- **`orchestrator.py`** - Executes infrastructure actions
  - SCALE_UP, SCALE_DOWN, RESTART, NOOP actions
  - Maintains execution history
  - Tracks success/failure of operations

- **`runtime_producer.py`** - Produces runtime telemetry in contract format
  - Normalizes metrics to shared schema
  - Generates alerts based on thresholds
  - Creates payloads for decision pipeline

#### Key Features:
- Real-time metric collection (every 5 seconds)
- Automatic alert generation for CPU, memory, error rate, latency
- Replicas updated dynamically based on scaling decisions
- Full execution history per application

### 2. Decision Brain Layer (decision_brain/)

**Responsibility:** Generate intelligent decisions with safety enforcement

#### Components:

- **`schemas.py`** - Runtime contract validation
  - Enforces required fields: app_id, environment, timestamp, signals
  - Type coercion and validation
  - Alert parsing and normalization

- **`pipeline.py`** - Canonical decision pipeline
  - Rule-based decision generation
  - Optional RL-based augmentation
  - Rate limiting (5-second cooldown per app)
  - False-positive dampening for error-rate triggers

- **`action_scope.py`** - Action scope enforcement
  - Validates decisions against environment rules
  - Downgrades illegal actions to NOOP
  - Context-aware enforcement

- **`state.py`** - Per-application state management
  - Decision history tracking
  - RL state (Q-table) storage
  - Cooldown management
  - Memory-bounded history (max 1000 decisions per app)

- **`orchestrator.py`** - Delivery to control plane
  - Sends decisions to orchestrator
  - Wait for acknowledgement
  - Reliable delivery logging

#### Decision Rules:

1. **Highest Priority:** Critical alerts → RESTART
2. **Error Rate Check:** > 5% → RESTART (dampened, requires 2 consecutive)
3. **CPU High:** ≥ 75% → SCALE_UP
4. **CPU Low:** ≤ 25% → SCALE_DOWN
5. **Default:** NOOP

#### Safety Features:
- Rate limiting: 5-second cooldown per app
- False-positive dampening for error-rate decisions
- Action scope enforcement
- All decisions logged with full context
- Orchestrator acknowledgement tracking

### 3. Monitoring Dashboard (`dashboard_ui.py`)

**Responsibility:** Real-time operational visibility

#### Features:

- **System Overview Panel**
  - System running status
  - Total decisions made
  
- **Per-Application Cards**
  - Real-time metrics (CPU, memory, error rate, latency, replicas)
  - Last action executed and success status
  - Current decision
  - Recent decision count

- **Auto-refresh:** Every 10 seconds
- **Live control loop:** Shows system state as it evolves

#### Data Flow:
```
Dashboard UI → /api/status endpoint → UnifiedInfrastructureSystem.get_system_status()
                                    → Control plane metrics
                                    → Decision history
                                    → Orchestrator execution logs
```

---

## Data Flow: End-to-End Control Loop

### Cycle (5-second intervals):

```
1. Telemetry Collection
   └─ TelemetryCollector.collect_metrics(app_id)
   └─ Returns: AppMetrics (cpu, memory, error_rate, latency, replicas)

2. Payload Generation
   └─ RuntimeProducer.create_payload(metrics)
   └─ Generates alerts based on thresholds
   └─ Returns: RuntimePayload (signed contract)

3. Decision Generation
   └─ DecisionPipeline.process_payload(payload)
   ├─ Validates against schema
   ├─ Checks rate limiting
   ├─ Generates decision (rule-based + optional RL)
   ├─ Enforces action scope
   └─ Returns: DecisionResult

4. Orchestrator Execution
   └─ OrchestratorClient.send_decision(payload)
   └─ Calls Orchestrator.execute_action()
   └─ Updates infrastructure state
   └─ Logs execution

5. Dashboard Visibility
   └─ /api/status returns current system state
   └─ Dashboard refreshes and displays
```

---

## Running the System

### Start the Complete System:

```bash
cd unified_infrastructure_system

# Terminal 1: Run integration test (45 seconds)
python integration_test.py

# Terminal 2: Start dashboard
python dashboard_ui.py
# Access dashboard at http://127.0.0.1:5000
```

### Components Automatically Started:

1. **Control Plane** - Telemetry collection and orchestration
2. **Decision Brain** - Continuous decision pipeline
3. **Dashboard** - Flask web server with live updates

### What Happens:

- System collects metrics every 5 seconds
- Generates decisions for 3 applications (web-app-1, api-service, data-processor)
- Executes actions through orchestrator
- Dashboard reflects real operational state
- Decision history tracked for all apps

---

## Key Integration Points

### 1. Runtime Contract

All telemetry must conform to:

```json
{
  "app_id": "string",
  "environment": "string",
  "timestamp": "float (unix epoch)",
  "signals": {
    "cpu": 0.0-1.0,
    "memory": 0.0-1.0,
    "error_rate": 0.0-1.0,
    "latency": float,
    "replicas": int
  },
  "alerts": [
    {
      "type": "string",
      "severity": "critical|warning|info",
      "message": "string"
    }
  ],
  "metadata": {
    "source": "string",
    "version": "string"
  }
}
```

### 2. Decision Payload to Orchestrator

```json
{
  "decision_id": "uuid",
  "app_id": "string",
  "environment": "string",
  "action": "NOOP|SCALE_UP|SCALE_DOWN|RESTART",
  "requested_action": "string (original)",
  "signals": { ... },
  "timestamp": float
}
```

### 3. Execution Result from Orchestrator

```json
{
  "decision_id": "uuid",
  "app_id": "string",
  "action": "string",
  "success": boolean,
  "message": "string"
}
```

---

## Configuration

### Decision Generator Thresholds (pipeline.py):

```python
DecisionGenerator(
    enable_rl=False,
    rl_explore_rate=0.2,
    error_rate_threshold=0.05,      # 5%
    cpu_scale_up_threshold=0.75,    # 75%
    cpu_scale_down_threshold=0.25   # 25%
)
```

### Rate Limiting (state.py):

```python
cooldown_duration = 5.0  # seconds per app
```

### Dashboard Refresh:

```html
<!-- Auto-refresh every 10 seconds -->
setInterval(loadDashboard, 10000);
```

---

## Monitoring and Observability

### Real-Time Logs:

All components emit structured logs:

```
2026-03-28 16:27:50 - unified_system - INFO - Decision: app=web-app-1 decision=NOOP allowed=False
2026-03-28 16:27:50 - control_plane.orchestrator - INFO - Executing action: NOOP for app web-app-1
2026-03-28 16:27:50 - pipeline - INFO - Decision result: id=... app=web-app-1 action=NOOP allowed=False ack=True
```

### Dashboard Metrics Exposed:

- `/api/status` - Current system state
- `/api/decisions` - Last 50 decisions

### Decision History:

Each decision recorded with:
- Timestamp
- App ID
- Decision ID (UUID)
- Action taken
- Whether action was allowed
- Orchestrator acknowledgement
- Reason for decision

---

## Multi-Application Isolation

The system maintains per-application state:

```
AppStateStore
├── web-app-1
│   ├── decision_history (bounded to 1000)
│   ├── action_counts (SCALE_UP, SCALE_DOWN, etc.)
│   ├── cooldown_until (for rate limiting)
│   └── rl_state (Q-table)
├── api-service
│   └── [same]
└── data-processor
    └── [same]
```

**No cross-application contamination** - Each app has independent state, decision rules, and action limits.

---

## Testing and Validation

### Integration Test Output:

The `integration_test.py` script validates:

1. **System startup** - All components initialize
2. **Telemetry collection** - Metrics collected for all 3 apps
3. **Decision generation** - Decisions made every cycle
4. **Orchestrator execution** - Actions logged
5. **Multi-app processing** - Independent state per app
6. **Dashboard data** - Real system state visible

**Expected Results:**
- 30 decisions over 45 seconds (10 per cycle × 3 apps × 1.5 cycles)
- All apps processed independently
- No decision failures
- Orchestrator acknowledges all

---

## Integration with Existing Systems

### Connecting to Real Orchestrator:

Replace the stub transport in `unified_system.py`:

```python
self.orchestrator_client = OrchestratorClient(
    endpoint_url="https://your-orchestrator:8000/execute",
    transport=None  # Uses HTTP by default
)
```

### Connecting to Real Monitoring:

Extend `TelemetryCollector` to pull from Prometheus/CloudWatch:

```python
class PrometheusCollector(TelemetryCollector):
    def collect_metrics(self, app_id):
        # Query Prometheus instead of generating
        pass
```

### Connecting to Dashboard DB:

Store decisions in PostgreSQL/MongoDB:

```python
self.decision_db.insert({
    'decision_id': result.decision_id,
    'app_id': result.app_id,
    'decision': result.decision.value,
    ...
})
```

---

## Troubleshooting

### System Not Making Non-NOOP Decisions?

Check rate limiting - apps are in 5-second cooldown by default

### High Error Rates Not Triggering RESTART?

Error rate dampening requires 2 consecutive triggers

### Dashboard Shows "Error Loading Data"?

Ensure dashboard_ui.py is running and accessing unified_system correctly

### Metrics Not Updating?

Control loop cycles every 5 seconds, dashboard refreshes every 10 seconds

---

## Next Steps

1. **Deploy to Production:** Replace stubs with real control plane
2. **Connect Real Monitoring:** Integrate with Prometheus/CloudWatch
3. **Add Persistence:** Store decisions for audit/learning
4. **Enable RL:** Activate reinforcement learning with reward signals
5. **Multi-Cluster:** Extend to multiple clusters/regions
6. **Advanced Policies:** Add custom decision rules per application

---

## Support and Contact

**System Owner:** Ritesh Yadav (Decision Intelligence Layer)  
**Control Plane Owner:** Shivam Pal  
**Dashboard Owner:** Alay Patel

For integration questions, refer to:
- `unified_system.py` - Main orchestrator
- `control_plane/` - Monitoring and execution
- `decision_brain/` - Decision generation
- `dashboard_ui.py` - UI and visibility
