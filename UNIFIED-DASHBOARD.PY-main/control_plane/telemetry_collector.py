"""Control plane telemetry collector.

This module simulates real infrastructure monitoring by collecting metrics
from running applications. In a real deployment, this would integrate with
monitoring systems like Prometheus, CloudWatch, etc.
"""

import time
import random
from typing import Dict, List
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
            "web-app-1": {"replicas": 3},
            "api-service": {"replicas": 2},
            "data-processor": {"replicas": 1},
        }

    def collect_metrics(self, app_id: str) -> AppMetrics:
        """Collect current metrics for an application."""
        if app_id not in self.apps:
            raise ValueError(f"Unknown app: {app_id}")

        # Simulate realistic metrics with some variation
        base_cpu = random.uniform(0.1, 0.8)
        base_mem = random.uniform(0.2, 0.9)
        base_error = random.uniform(0.0, 0.1)
        base_latency = random.uniform(50, 500)

        # Add some trends (e.g., if high load, higher metrics)
        load_factor = random.uniform(0.5, 1.5)
        cpu = min(1.0, base_cpu * load_factor)
        mem = min(1.0, base_mem * load_factor)
        error = min(1.0, base_error * load_factor)
        latency = base_latency * load_factor

        return AppMetrics(
            app_id=app_id,
            cpu_usage=cpu,
            memory_usage=mem,
            error_rate=error,
            latency_ms=latency,
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