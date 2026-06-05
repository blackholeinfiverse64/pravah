Shivam — Executer Integration Artifacts

Purpose
- Provide the executer API contract, expected headers, and a quick test script to prove non-bypass enforcement.

Files
- `SARATHI_API_CONTRACT.md` — full Sarathi request/response schema and signal format.
- `run_integration_tests.sh` — three curl tests (direct, bypass, full flow).
- `requirements.txt` — minimal Python deps used across services.

Quick facts for `executer/app.py`
- Endpoint: POST /execute on port 8001
- Required header: `X-CALLER: sarathi` (exact value)
- Request JSON schema:
  - `action`: string (non-empty)
  - `trace_id`: string (non-empty)
  - `payload`: object (optional)
- Response on success: JSON containing `execution_id`, `status`, `action`, `trace_id`.
- Failure: 403 if header missing (enforcement lock).

Run tests (linux/mac/bash):

```bash
chmod +x run_integration_tests.sh
./run_integration_tests.sh
```

If you prefer PowerShell I can add a `.ps1` version.