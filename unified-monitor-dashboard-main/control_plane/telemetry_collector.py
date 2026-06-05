"""Control plane telemetry collector.

This collector keeps the latest runtime telemetry per application.
It is intentionally contract-aligned and deterministic:
- no random metric generation
- supports direct telemetry ingestion from a control plane source
- exposes current snapshots to the decision pipeline
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AppMetrics:
    app_id: str
    cpu_usage: float  # 0-1
    memory_usage: float  # 0-1
    error_rate: float  # 0-1
    latency_ms: float
    replica_count: int
    timestamp: float


class TelemetryCollector:
    """Collects real-time metrics from infrastructure."""

    def __init__(self):
        self.apps = {
            "web-app-1": {
                "replicas": 3,
                "metrics": {"cpu": 0.72, "memory": 0.61, "error_rate": 0.01, "latency_ms": 180.0},
            },
            "api-service": {
                "replicas": 2,
                "metrics": {"cpu": 0.35, "memory": 0.48, "error_rate": 0.07, "latency_ms": 420.0},
            },
            "data-processor": {
                "replicas": 1,
                "metrics": {"cpu": 0.22, "memory": 0.57, "error_rate": 0.0, "latency_ms": 95.0},
            },
        }

    def register_app(
        self,
        app_id: str,
        replicas: int = 1,
        initial_metrics: Optional[Dict[str, float]] = None,
    ):
        """Register a new application in the control plane telemetry registry."""
        metrics = initial_metrics or {
            "cpu": 0.0,
            "memory": 0.0,
            "error_rate": 0.0,
            "latency_ms": 0.0,
        }
        self.apps[app_id] = {
            "replicas": max(1, int(replicas)),
            "metrics": {
                "cpu": float(metrics.get("cpu", 0.0)),
                "memory": float(metrics.get("memory", 0.0)),
                "error_rate": float(metrics.get("error_rate", 0.0)),
                "latency_ms": float(metrics.get("latency_ms", 0.0)),
            },
        }

    def ingest_runtime_signals(self, app_id: str, signals: Dict[str, float]):
        """Update app metrics from control-plane runtime telemetry."""
        if app_id not in self.apps:
            self.register_app(app_id)

        current = self.apps[app_id]["metrics"]
        current["cpu"] = float(signals.get("cpu", current["cpu"]))
        current["memory"] = float(signals.get("memory", current["memory"]))
        current["error_rate"] = float(signals.get("error_rate", current["error_rate"]))
        current["latency_ms"] = float(signals.get("latency", signals.get("latency_ms", current["latency_ms"])))
        if "replicas" in signals:
            self.apps[app_id]["replicas"] = max(1, int(signals["replicas"]))

    def collect_metrics(self, app_id: str) -> AppMetrics:
        """Collect current metrics for an application."""
        if app_id not in self.apps:
            raise ValueError(f"Unknown app: {app_id}")

        metrics = self.apps[app_id]["metrics"]

        return AppMetrics(
            app_id=app_id,
            cpu_usage=float(metrics["cpu"]),
            memory_usage=float(metrics["memory"]),
            error_rate=float(metrics["error_rate"]),
            latency_ms=float(metrics["latency_ms"]),
            replica_count=self.apps[app_id]["replicas"],
            timestamp=time.time()
        )

    def get_all_apps(self) -> List[str]:
        """Get list of all registered applications."""
        return list(self.apps.keys())

    def update_replicas(self, app_id: str, new_count: int):
        """Update replica count after scaling action."""
        if app_id in self.apps:
            self.apps[app_id]["replicas"] = new_count