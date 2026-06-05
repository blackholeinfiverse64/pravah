import asyncio
import logging
from typing import Dict, List
from rl.rl_agent import RLAgent
from rl.state_encoder import StateEncoder
from rl.reward_engine import RewardEngine
from rl.execution_verifier import ExecutionVerifier

logger = logging.getLogger(__name__)

class AutonomyLoop:
    def __init__(self, environment: str, telemetry_client, orchestrator_client, deployment_store):
        self.environment = environment
        self.agent = RLAgent(environment=environment)
        self.state_encoder = StateEncoder()
        self.reward_engine = RewardEngine()
        self.verifier = ExecutionVerifier(telemetry_client, orchestrator_client)
        self.deployment_store = deployment_store
        self.running = False
    
    async def start(self, interval_seconds: int = 30):
        self.running = True
        logger.info(f"Autonomy loop started (interval={interval_seconds}s, env={self.environment})")
        
        while self.running:
            try:
                await self._execute_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    def stop(self):
        self.running = False
        logger.info("Autonomy loop stopped")
    
    async def _execute_cycle(self):
        deployments = await self.deployment_store.get_active_deployments()
        
        for deployment in deployments:
            deployment_id = deployment["id"]
            
            try:
                telemetry = await self.verifier.telemetry_client.get_metrics(deployment_id)
                
                state = self.state_encoder.encode_state(
                    telemetry.get("cpu_percent", 0),
                    telemetry.get("memory_percent", 0),
                    telemetry.get("health_score", 1.0)
                )
                
                action = self.agent.select_action(state, deployment_id)
                
                if not action:
                    continue
                
                logger.info(f"Executing: deployment={deployment_id}, state={state}, action={action}")
                
                result = await self.verifier.execute_and_verify(deployment_id, action)
                
                self.agent.record_action(deployment_id, action)
                
                reward = self.reward_engine.calculate_reward(
                    result["pre_telemetry"],
                    result["post_telemetry"],
                    result["execution_status"]
                )
                
                next_telemetry = result["post_telemetry"]
                next_state = self.state_encoder.encode_state(
                    next_telemetry["cpu"],
                    next_telemetry["memory"],
                    next_telemetry["health"]
                )
                
                self.agent.update_q_table(state, action, reward, next_state)
                
                logger.info(f"Cycle complete: status={result['execution_status']}, reward={reward}")
                
            except Exception as e:
                logger.error(f"Deployment {deployment_id} cycle failed: {e}")
