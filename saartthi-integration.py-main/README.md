# Sarathi Enforcement Integration

This repository contains the enforcement proof-of-concept for the Sarathi governance flow.

## Services

- `sarathi/app.py` — governance decision service exposing `POST /decision`.
- `core/app.py` — Core service exposing `POST /invoke`, which calls Sarathi and then forwards allowed execution to Executer.
- `executer/app.py` — execution service exposing `POST /execute`, which rejects any request without `X-CALLER: sarathi`.

## Key enforcement guarantees

- No execution can happen without Sarathi approval.
- `trace_id` is required and must be propagated unchanged.
- Sarathi emits decision and enforcement signals before execution.
- Executer enforces `X-CALLER: sarathi` and rejects bypass attempts.

## Run locally

Install dependencies:

```bash
pip install fastapi uvicorn httpx pydantic
```

Start services in separate terminals:

```bash
uvicorn sarathi.app:app --host 0.0.0.0 --port 8000
uvicorn core.app:app --host 0.0.0.0 --port 8002
uvicorn executer.app:app --host 0.0.0.0 --port 8001
```

## Test flow

1. Direct `Executer` call must fail.
2. Core must call Sarathi first.
3. Sarathi must return `ALLOW` before Core forwards to Executer.

## Artifacts

- `review_packets/sarathi_enforcement.md`
- `artifacts/shivam/` — executer integration artifacts
- `artifacts/rayyan/` — core integration notes
