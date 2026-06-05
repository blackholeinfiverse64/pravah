Sarathi API Contract

Endpoint: POST /decision (port 8000)

Request JSON (strict schema — all fields required):
- `trace_id` (string, non-empty) — must be provided by Core and propagated unchanged.
- `app_id` (string, non-empty)
- `proposed_action` (string, non-empty)
- `metrics` (object) — optional contents, may be empty object

Example request:
```json
{
  "trace_id": "trace-123",
  "app_id": "core-app",
  "proposed_action": "run_job",
  "metrics": {}
}
```

Response JSON (deterministic):
- `trace_id` (string)
- `decision` ("ALLOW" | "BLOCK" | "MODIFY")
- `action` (string) — action to execute (same as proposed or modified)
- `policy_reference` (string)
- `reason` (string)

Example response:
```json
{
  "trace_id": "trace-123",
  "decision": "ALLOW",
  "action": "run_job",
  "policy_reference": "policy-001",
  "reason": "Whitelisted action"
}
```

Signals (Pravah-like schema) — Sarathi emits both BEFORE any execution is requested:
- Decision signal
  - `signal_type`: "decision"
  - `trace_id`: same trace
  - `payload`: decision response object
- Enforcement signal (only for `ALLOW`)
  - `signal_type`: "enforcement"
  - `trace_id`: same trace
  - `payload`: decision response object

Non-bypass enforcement
- Executer accepts execution ONLY when request includes header `X-CALLER: sarathi`.
- Core must call Sarathi, then forward to Executer using the returned `action` and `trace_id` and include the header exactly as above.

Trace rules
- Sarathi MUST NOT generate `trace_id`.
- Any request missing `trace_id` will be rejected with 422.

Notes for implementer
- Deterministic policy engine — no ML, no scoring.
- Use strict validation (Pydantic / JSON Schema).
- Emit signals to logs/stdout for proof if no message bus present.