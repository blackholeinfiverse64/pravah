from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ExecutionVerifier:
    def __init__(self, telemetry_client, orchestrator_client):
        self.telemetry_client = telemetry_client
        self.orchestrator_client = orchestrator_client
    
    async def execute_and_verify(self, deployment_id: str, action: str) -> Dict[str, Any]:
        pre_telemetry = await self._capture_telemetry(deployment_id)
        
        try:
            execution_result = await self.orchestrator_client.execute_action(deployment_id, action)
            execution_status = "verified" if execution_result.get("success") else "failed"
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            execution_status = "failed"
            execution_result = {"success": False, "error": str(e)}
        
        post_telemetry = await self._capture_telemetry(deployment_id)
        
        state_delta = self._compute_delta(pre_telemetry, post_telemetry)
        
        return {
            "execution_status": execution_status,
            "state_delta": state_delta,
            "pre_telemetry": pre_telemetry,
            "post_telemetry": post_telemetry,
            "execution_result": execution_result
        }
    
    async def _capture_telemetry(self, deployment_id: str) -> Dict[str, float]:
        try:
            telemetry = await self.telemetry_client.get_metrics(deployment_id)
            return {
                "cpu": telemetry.get("cpu_percent", 0.0),
                "memory": telemetry.get("memory_percent", 0.0),
                "health": telemetry.get("health_score", 1.0),
                "restarts": telemetry.get("restart_count", 0),
                "crashed": telemetry.get("crashed", False)
            }
        except Exception as e:
            logger.error(f"Telemetry capture failed: {e}")
            return {"cpu": 0.0, "memory": 0.0, "health": 0.0, "restarts": 0, "crashed": False}
    
    def _compute_delta(self, pre: Dict, post: Dict) -> Dict[str, float]:
        return {
            "cpu_delta": post["cpu"] - pre["cpu"],
            "memory_delta": post["memory"] - pre["memory"],
            "health_delta": post["health"] - pre["health"],
            "restart_delta": post["restarts"] - pre["restarts"]
        }
