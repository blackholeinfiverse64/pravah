from typing import Dict

class RewardEngine:
    @staticmethod
    def calculate_reward(pre_telemetry: Dict, post_telemetry: Dict, execution_status: str) -> float:
        if execution_status == "failed":
            return -5.0
        
        reward = 0.0
        
        health_delta = post_telemetry.get("health", 0) - pre_telemetry.get("health", 0)
        if health_delta > 0.1:
            reward += 2.0
        elif health_delta < -0.1:
            reward -= 2.0
        
        cpu_delta = post_telemetry.get("cpu", 0) - pre_telemetry.get("cpu", 0)
        if cpu_delta < -10:
            reward += 1.0
        elif cpu_delta > 20:
            reward -= 1.0
        
        restart_delta = post_telemetry.get("restarts", 0) - pre_telemetry.get("restarts", 0)
        if restart_delta > 0:
            reward -= 2.0
        
        if post_telemetry.get("crashed", False):
            reward -= 5.0
        
        return reward
