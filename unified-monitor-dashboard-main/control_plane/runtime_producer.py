"""Runtime telemetry producer for the control plane.

This module produces runtime payloads in the shared contract format
and sends them to the decision engine.
"""

import time
import logging
from typing import Dict, Any, List
from .telemetry_collector import TelemetryCollector, AppMetrics

logger = logging.getLogger(__name__)


class RuntimeProducer:
    """Produces runtime telemetry payloads for the decision engine."""

    def __init__(self, telemetry_collector: TelemetryCollector, environment: str = "production"):
        self.telemetry = telemetry_collector
        self.environment = environment

    def create_payload(self, metrics: AppMetrics) -> Dict[str, Any]:
        """Create a runtime payload from metrics."""
        alerts = []

        # Generate alerts based on thresholds
        if metrics.cpu_usage > 0.8:
            alerts.append({
                "type": "high_cpu",
                "severity": "warning",
                "message": f"CPU usage at {metrics.cpu_usage:.1%}"
            })

        if metrics.memory_usage > 0.9:
            alerts.append({
                "type": "high_memory",
                "severity": "critical",
                "message": f"Memory usage at {metrics.memory_usage:.1%}"
            })

        if metrics.error_rate > 0.05:
            alerts.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"Error rate at {metrics.error_rate:.1%}"
            })

        if metrics.latency_ms > 1000:
            alerts.append({
                "type": "high_latency",
                "severity": "warning",
                "message": f"Latency at {metrics.latency_ms:.0f}ms"
            })

        return {
            "app_id": metrics.app_id,
            "environment": self.environment,
            "timestamp": metrics.timestamp,
            "signals": {
                "cpu": metrics.cpu_usage,
                "memory": metrics.memory_usage,
                "error_rate": metrics.error_rate,
                "latency": metrics.latency_ms,
                "replicas": metrics.replica_count
            },
            "alerts": alerts,
            "metadata": {
                "source": "control_plane_monitoring",
                "version": "1.0"
            }
        }

    def get_all_payloads(self) -> List[Dict[str, Any]]:
        """Get payloads for all registered applications."""
        payloads = []
        for app_id in self.telemetry.get_all_apps():
            try:
                metrics = self.telemetry.collect_metrics(app_id)
                payload = self.create_payload(metrics)
                payloads.append(payload)
            except Exception as e:
                logger.error(f"Failed to collect metrics for {app_id}: {e}")
        return payloads

    def get_payload(self, app_id: str) -> Dict[str, Any]:
        """Get payload for a specific application."""
        metrics = self.telemetry.collect_metrics(app_id)
        return self.create_payload(metrics)