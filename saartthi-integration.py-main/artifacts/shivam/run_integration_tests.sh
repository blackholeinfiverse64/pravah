#!/bin/bash
set -e

echo "Test 1: Direct to Executer (should FAIL 403)"
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "direct-trace"}' || true

echo -e "\nTest 2: Bypass attempt (should FAIL 403)"
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "bypass-trace"}' || true

echo -e "\nTest 3: Full flow via Core -> Sarathi -> Executer (should PASS)"
# Core invoke (port 8002) will call Sarathi and then Executer. Replace trace if needed.
curl -i -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "valid-trace-789", "app_id": "core-app", "proposed_action": "run_job", "metrics": {}}'
