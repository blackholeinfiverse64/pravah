import uuid
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any

app = FastAPI()

# Pydantic model for execution request
class ExecuteRequest(BaseModel):
    action: str = Field(..., min_length=1, description="Action to execute")
    trace_id: str = Field(..., min_length=1, description="Trace ID propagated from Sarathi")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Optional additional payload")

@app.post("/execute")
async def execute_endpoint(request: Request, execute_req: ExecuteRequest, x_caller: str = Header(None)):
    # Enforce that request comes from Sarathi
    if x_caller != "sarathi":
        raise HTTPException(status_code=403, detail="Missing required header X-CALLER: sarathi")
    # Here would be the actual execution logic; we mock it
    execution_id = str(uuid.uuid4())
    return {
        "execution_id": execution_id,
        "status": "started",
        "action": execute_req.action,
        "trace_id": execute_req.trace_id,
    }
