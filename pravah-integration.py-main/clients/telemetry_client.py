class TelemetryClient:
    async def get_metrics(self, deployment_id: str):
        return {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "health_score": 0.9,
            "restart_count": 0,
            "crashed": False
        }
