from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any

app = FastAPI()

# ---- Pydantic models for strict schema validation ----
class DecisionRequest(BaseModel):
    trace_id: str = Field(..., min_length=1, description="Unique identifier propagated through the system")
    app_id: str = Field(..., min_length=1, description="Identifier of the calling application")
    proposed_action: str = Field(..., min_length=1, description="Action the caller wants to perform")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Optional additional metrics")

class DecisionResponse(BaseModel):
    trace_id: str
    decision: str
    action: str
    policy_reference: str
    reason: str

# ---- Simple deterministic policy engine ----
# For demonstration we define a static whitelist of allowed actions.
ALLOWED_ACTIONS = {
    "run_job": {
        "policy_reference": "policy-001",
        "reason": "Whitelisted action"
    },
    "generate_report": {
        "policy_reference": "policy-002",
        "reason": "Whitelisted action"
    }
}

def evaluate_policy(req: DecisionRequest) -> DecisionResponse:
    if req.proposed_action in ALLOWED_ACTIONS:
        decision = "ALLOW"
        action = req.proposed_action
        policy_ref = ALLOWED_ACTIONS[req.proposed_action]["policy_reference"]
        reason = ALLOWED_ACTIONS[req.proposed_action]["reason"]
    else:
        decision = "BLOCK"
        action = req.proposed_action
        policy_ref = "policy-000"
        reason = "Action not permitted by governance rules"
    return DecisionResponse(
        trace_id=req.trace_id,
        decision=decision,
        action=action,
        policy_reference=policy_ref,
        reason=reason,
    )

# ---- Helper to emit signals matching Pravah schema ----
def emit_signal(signal_type: str, payload: Dict[str, Any]):
    # In a real system this would publish to a message bus. Here we simply print JSON.
    import json
    signal = {
        "signal_type": signal_type,
        "trace_id": payload.get("trace_id"),
        "payload": payload,
    }
    print(json.dumps(signal))

# ---- API endpoint ----
@app.post("/decision", response_model=DecisionResponse)
def decision_endpoint(request: DecisionRequest):
    # Enforce strict schema – FastAPI/Pydantic already validates.
    # Emit decision signal before any execution.
    decision_resp = evaluate_policy(request)
    emit_signal("decision", decision_resp.dict())
    # If decision is ALLOW we also emit an enforcement signal.
    if decision_resp.decision == "ALLOW":
        emit_signal("enforcement", decision_resp.dict())
    return decision_resp

# ---- Health check ----
@app.get("/health")
def health_check():
    return {"status": "ok"}
