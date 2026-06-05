from typing import Tuple

class StateEncoder:
    @staticmethod
    def encode_cpu(cpu_percent: float) -> str:
        if cpu_percent < 40:
            return "low"
        elif cpu_percent < 75:
            return "medium"
        else:
            return "high"
    
    @staticmethod
    def encode_memory(memory_percent: float) -> str:
        if memory_percent < 60:
            return "safe"
        elif memory_percent < 85:
            return "elevated"
        else:
            return "critical"
    
    @staticmethod
    def encode_health(health_score: float) -> str:
        if health_score >= 0.8:
            return "healthy"
        elif health_score >= 0.5:
            return "degraded"
        else:
            return "failing"
    
    @classmethod
    def encode_state(cls, cpu: float, memory: float, health: float) -> Tuple[str, str, str]:
        return (
            cls.encode_cpu(cpu),
            cls.encode_memory(memory),
            cls.encode_health(health)
        )
