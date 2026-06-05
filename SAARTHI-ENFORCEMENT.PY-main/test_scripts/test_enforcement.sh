#!/bin/bash

echo "Running Test Case 1: Direct call to Executer (Expected: 403)"
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "direct-trace"}'

echo -e "\n\nRunning Test Case 2: Call via Core without Sarathi (Directly to Executer) (Expected: 403)"
curl -i -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"action": "run_job", "trace_id": "bypass-trace"}'

echo -e "\n\nRunning Test Case 3: Full Valid Flow via Core -> Sarathi -> Executer (Expected: 200)"
curl -i -X POST http://localhost:8002/invoke \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "valid-trace-789", "app_id": "core-app", "proposed_action": "run_job"}'
