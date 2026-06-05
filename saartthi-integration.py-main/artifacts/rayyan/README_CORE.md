Rayyan (Core) Integration Notes

Purpose
- Describe how Core must call Sarathi and what Core must forward to Executer.

Core endpoint
- POST /invoke on port 8002
- Request JSON (strict):
  - `trace_id` (string, required)
  - `app_id` (string, required)
  - `proposed_action` (string, required)
  - `metrics` (object)

Behavior
1. Core must call Sarathi at `POST http://localhost:8000/decision` with the same JSON.
2. If Sarathi returns `decision` != `ALLOW`, Core must stop and return 403.
3. If `ALLOW`, Core forwards to Executer at `POST http://localhost:8001/execute` with JSON:
   - `action`: value from Sarathi `action`
   - `trace_id`: value from Sarathi `trace_id` (unchanged)
   - `payload`: {}
   and include header `X-CALLER: sarathi`.

Sample curl (client -> Core):
```bash
curl -i -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "trace-123", "app_id": "core-app", "proposed_action": "run_job", "metrics": {}}'
```

Notes
- Core must never call Executer without Sarathi-approved header.
- For testing, use `artifacts/shivam/run_integration_tests.sh`.
