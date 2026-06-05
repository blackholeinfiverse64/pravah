"""
mitra.py — Intelligence Layer
Scores proposals so Sarathi can make informed ALLOW/BLOCK/ESCALATE decisions.
decision_score = (0.5 × urgency) + (0.3 × impact) - (0.2 × risk)
"""


def calculate_score(metrics):
    urgency = metrics.get("cpu", 0)
    impact  = 0.8  # fixed for now (tier-1 services always high impact)
    risk    = metrics.get("error_rate", 0)

    score      = (0.5 * urgency) + (0.3 * impact) - (0.2 * risk)
    score      = round(max(0.0, min(1.0, score)), 2)
    confidence = round(max(0.0, 1.0 - risk), 2)

    if score >= 0.7:
        priority = "CRITICAL"
    elif score >= 0.5:
        priority = "HIGH"
    elif score >= 0.3:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    return {
        "decision_score": score,
        "confidence":     confidence,
        "priority":       priority
    }