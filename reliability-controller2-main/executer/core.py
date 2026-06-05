"""
core.py — Execution Layer
Deterministic action execution. Only called after Sarathi ALLOW.
Supports: kubernetes mode (real kubectl) and simulation mode (for testing).
"""

import os
import subprocess

EXECUTION_MODE = os.getenv("EXECUTION_MODE", "simulate")  # "kubernetes" or "simulate"

MAX_RETRIES = 3


def execute_action(service_id, action):
    """
    Execute the given action for service_id.
    Returns: result string (success message or error).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = _run_action(service_id, action)

            if result.startswith("ERROR") and attempt < MAX_RETRIES:
                continue  # retry

            return result

        except Exception as e:
            if attempt == MAX_RETRIES:
                return f"ERROR: exception after {MAX_RETRIES} retries — {str(e)}"

    return f"ERROR: all {MAX_RETRIES} retries exhausted"


def _run_action(service_id, action):
    if EXECUTION_MODE == "kubernetes":
        return _kubectl_action(service_id, action)
    else:
        return _simulate_action(service_id, action)


def _kubectl_action(service_id, action):
    if action == "restart":
        cmd = ["kubectl", "rollout", "restart", f"deployment/{service_id}"]

    elif action == "scale_up":
        cmd = ["kubectl", "scale", f"deployment/{service_id}", "--replicas=2"]

    elif action == "scale_down":
        cmd = ["kubectl", "scale", f"deployment/{service_id}", "--replicas=1"]

    else:
        return "noop — no action required"

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    if result.returncode == 0:
        return result.stdout.strip() or f"{action} on {service_id} succeeded"
    else:
        return f"ERROR: {result.stderr.strip()}"


def _simulate_action(service_id, action):
    """Used in Docker Compose / test mode (no real kubectl)."""
    if action == "noop":
        return "noop — no action required"
    return f"SIMULATED: {action} on {service_id} completed successfully"


def verify_deployment(service_id):
    """Check if service pod is running."""
    if EXECUTION_MODE != "kubernetes":
        return True  # simulation always passes

    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-l", f"app={service_id}"],
            capture_output=True, text=True, timeout=5
        )
        return "Running" in result.stdout
    except Exception:
        return False