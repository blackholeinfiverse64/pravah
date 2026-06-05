"""
sovereign_bridge.py — Sarathi Integration
Sends every proposal to Sarathi (PDP) before any execution.
NO direct execution is allowed outside this bridge.
"""

import os
import requests

SARATHI_URL = os.getenv("SARATHI_URL", "http://sarathi:5001/decision")


def send_to_sarathi(proposal):
    """
    Send proposal to Sarathi for a policy decision.
    Returns: {"status": "ALLOW" | "BLOCK" | "ESCALATE", "reason": "..."}
    """
    try:
        response = requests.post(SARATHI_URL, json=proposal, timeout=3)
        return response.json()

    except requests.exceptions.ConnectionError:
        return {"status": "ERROR", "reason": "Sarathi service unreachable"}

    except requests.exceptions.Timeout:
        return {"status": "ERROR", "reason": "Sarathi request timed out"}

    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}