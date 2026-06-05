# curl_examples.md

## Test Cases for Sarathi Enforcement

### 1. Direct call to Executer (should FAIL with 403)
```bash
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "test-trace"}'
```
Expected response:
```
HTTP/1.1 403 Forbidden
... 
{"detail":"Missing required header X-CALLER: sarathi"}
```

### 2. Call via Core without Sarathi (should FAIL with 403)
Assuming Core forwards the request directly to Executer:
```bash
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -H "X-TRACE-ID: abc123" \
  -d '{"action": "run_job"}'
```
Expected response same as above (403).

### 3. Call via Sarathi (should PASS)
First obtain a decision from Sarathi:
```bash
curl -i -X POST http://localhost:8000/decision \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "abc123", "app_id": "core", "proposed_action": "run_job", "metrics": {}}
```
Assuming response contains `decision": "ALLOW"`.
Then forward to Executer with required header:
```bash
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -H "X-CALLER: sarathi" \
  -d '{"action": "run_job", "trace_id": "abc123"}'
```
Expected response (200 OK) with execution result, e.g.:
```
HTTP/1.1 200 OK
... 
{"execution_id": "exec-12345", "status": "started"}
```

These commands can be saved as a shell script `run_tests.sh` for convenience.
