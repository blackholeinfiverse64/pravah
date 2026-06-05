import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

app = FastAPI()

SARATHI_URL = "http://localhost:8000/decision"
EXECUTER_URL = "http://localhost:8001/execute"

class CoreRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)
    app_id: str = Field(..., min_length=1)
    proposed_action: str = Field(..., min_length=1)
    metrics: Dict[str, Any] = Field(default_factory=dict)

@app.post("/invoke")
async def invoke(req: CoreRequest):
    # Call Sarathi for decision
    async with httpx.AsyncClient() as client:
        sarathi_resp = await client.post(SARATHI_URL, json=req.dict())
    if sarathi_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Sarathi decision failed")
    decision = sarathi_resp.json()
    if decision.get("decision") != "ALLOW":
        raise HTTPException(status_code=403, detail="Action blocked by governance")
    # Forward to Executer with required header
    execute_payload = {
        "action": decision.get("action"),
        "trace_id": decision.get("trace_id"),
        "payload": {}
    }
    async with httpx.AsyncClient() as client:
        exec_resp = await client.post(
            EXECUTER_URL,
            json=execute_payload,
            headers={"X-CALLER": "sarathi"}
        )
    if exec_resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Executer failed")
    return exec_resp.json()
