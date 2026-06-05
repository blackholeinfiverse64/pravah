# Handover: Decision Brain + Control Plane Integration

## Integration Points

- `runtime_contract.py` is the shared runtime schema entrypoint for both control plane and decision engine.
- `control_plane/runtime_producer.py` emits payloads in runtime-contract format.
- `pipeline.py` consumes contract payloads and produces executable actions.
- `orchestrator_client.py` wraps orchestrator communication classes used by the decision pipeline.

## Dashboard Data Sources

- `dashboard_ui.py` reads from `UnifiedInfrastructureSystem.get_system_status()`.
- `get_system_status()` combines:
  - live telemetry snapshots from `TelemetryCollector`
  - decision records from `decision_history`
  - execution outcomes from control-plane `Orchestrator`
- Dashboard fields are sourced from real runtime loop state, not a separate monitoring loop.
- Dashboard API also accepts external runtime events:
  - `POST /api/apps/register`
  - `POST /api/telemetry/ingest`

## Orchestrator Communication Flow

1. `RuntimeProducer.get_all_payloads()` provides runtime payloads.
2. `DecisionPipeline.process_payload()` validates, decides, enforces action scope.
3. Pipeline sends action payload to `OrchestratorClient.send_decision()`.
4. `UnifiedInfrastructureSystem._send_to_orchestrator()` forwards to control-plane `Orchestrator.execute_action()`.
5. Orchestrator acknowledgement is written into decision history and exposed via dashboard APIs.

## Telemetry Ingestion Flow

1. Control-plane or external monitor posts telemetry to `POST /api/telemetry/ingest`.
2. `dashboard_ui.py` forwards data to `UnifiedInfrastructureSystem.ingest_telemetry`.
3. `TelemetryCollector.ingest_runtime_signals` updates in-memory runtime snapshots.
4. `RuntimeProducer` emits these snapshots using the runtime contract.
5. `DecisionPipeline` consumes payloads and drives orchestrator execution.

## Required Decision Log Keys

Each control-loop decision record contains:

- `decision_id`
- `app_id`
- `action_requested`
- `action_emitted`
- `orchestrator_acknowledged`

These are available in logs and via `/api/decisions`.
