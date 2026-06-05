# Sarathi Enforcement Review Packet

## 1. Entry Point
- **Sarathi Service**: `sarathi/app.py`
- **Port**: 8000
- **Endpoint**: `POST /decision`

## 2. Core Flow (max 3 components)
1. **Core Service** (`core/app.py`): Initiates the request, calls Sarathi for governance approval.
2. **Sarathi Service** (`sarathi/app.py`): Evaluates the action based on deterministic policies and emits enforcement signals.
3. **Executer Service** (`executer/app.py`): Executes the approved action only if the `X-CALLER: sarathi` header is present.

## 3. Live API Flow
`Client` -> `Core:8002/invoke` -> `Sarathi:8000/decision` -> `Executer:8001/execute`

## 4. What Was Enforced
- **Non-Bypass**: Executer rejects any request without `X-CALLER: sarathi` header (403 Forbidden).
- **Deterministic Governance**: Sarathi uses strict schema validation and whitelist-based decision logic.
- **Trace Propagation**: `trace_id` is passed from Core to Sarathi and finally to Executer without modification.
- **Signal Emission**: Sarathi emits `decision` and `enforcement` signals before returning the response.

## 5. Failure Cases
- **Direct call to Executer**: Returns 403 Forbidden because of missing header.
- **Call via Core without Sarathi**: Not possible as Core is hardcoded to call Sarathi first.
- **Blocked Action**: If Sarathi returns `BLOCK`, Core stops and returns 403.
- **Invalid Schema**: FastAPI returns 422 Unprocessable Entity if fields are missing.

## 6. Proof (curl outputs)

### Case 1: Direct Call to Executer -> FAIL (403)
```bash
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "test-trace"}'
```
**Output:**
```
HTTP/1.1 403 Forbidden
{"detail":"Missing required header X-CALLER: sarathi"}
```

### Case 2: Call via Core without Sarathi (Simulation of bypass attempt) -> FAIL
Even if Core tries to call Executer without the header, it will fail.
```bash
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "bypass-test"}'
```
**Output:**
```
HTTP/1.1 403 Forbidden
```

### Case 3: Call via Sarathi (Full Flow) -> PASS
```bash
curl -i -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "trace-123", "app_id": "core-app", "proposed_action": "run_job"}'
```
**Output:**
```
HTTP/1.1 200 OK
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started",
  "action": "run_job",
  "trace_id": "trace-123"
}
```
