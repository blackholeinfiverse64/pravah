# Integration Evidence Log

## Runtime Telemetry -> Decision -> Orchestrator -> Dashboard

Validated against running dashboard instance on `http://127.0.0.1:5050`.

## Evidence Commands Used

1. Register a new application for multi-app validation:

`POST /api/apps/register`

Request:

```json
{
  "app_id": "payments-api",
  "replicas": 2,
  "signals": {
    "cpu": 0.41,
    "memory": 0.52,
    "error_rate": 0.01,
    "latency_ms": 120
  }
}
```

Response:

```json
{"app_id":"payments-api","registered":true,"replicas":2}
```

2. Ingest real runtime telemetry for that app:

`POST /api/telemetry/ingest`

Request:

```json
{
  "app_id": "payments-api",
  "signals": {
    "cpu": 0.93,
    "memory": 0.88,
    "error_rate": 0.12,
    "latency": 1430,
    "replicas": 3
  }
}
```

Response:

```json
{"app_id":"payments-api","ingested":true,"total_events":2}
```

3. Verify dashboard status uses ingested telemetry:

`GET /api/status`

Observed excerpts:

- `active_applications` includes `payments-api`
- `apps.payments-api.metrics.cpu = 0.93`
- `apps.payments-api.metrics.memory = 0.88`
- `apps.payments-api.metrics.error_rate = 0.12`
- `apps.payments-api.metrics.latency_ms = 1430.0`
- `apps.payments-api.metrics.replicas = 3`

## Required Decision Log Keys

Decision logs include:

- `decision_id`
- `app_id`
- `action_requested`
- `action_emitted`
- `orchestrator_acknowledged`

Available via:

- pipeline runtime logs
- `GET /api/decisions`
- `integration_test.py` output

## Multi-Application Validation

Applications validated:

- `web-app-1`
- `api-service`
- `data-processor`
- `payments-api` (externally registered during validation)

No cross-app state contamination observed in per-app status and decision history.
