import uuid
from bucket import log_event

def process(metrics):
    trace_id = str(uuid.uuid4())

    log_event(trace_id, "monitor", metrics)

    proposal = {
        "trace_id": trace_id,
        "action": "scale_up" if metrics["cpu"] > 0.7 else "none",
        "metrics": metrics
    }

    log_event(trace_id, "proposal_created", proposal)

    # ✅ NO EXECUTION HERE (BHIV CORRECT)
    log_event(trace_id, "signal_emitted", proposal)

    return {"status": "signal_only"}