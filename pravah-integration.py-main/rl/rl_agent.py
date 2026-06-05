import random
from typing import Tuple, Dict, Optional
from rl.q_table_store import QTableStore
from rl.state_encoder import StateEncoder
from rl.reward_engine import RewardEngine
from guard.action_guard import ActionGuard
from guard.cooldown_manager import CooldownManager
import logging

logger = logging.getLogger(__name__)

class RLAgent:
    ACTIONS = ["noop", "scale_up", "scale_down", "restart", "redeploy"]
    
    def __init__(self, environment: str = "DEV", epsilon: float = 0.1, alpha: float = 0.1, gamma: float = 0.9):
        self.environment = environment.upper()
        self.epsilon = epsilon if environment == "DEV" else 0.0
        self.alpha = alpha
        self.gamma = gamma
        
        self.q_store = QTableStore(environment=environment)
        self.state_encoder = StateEncoder()
        self.reward_engine = RewardEngine()
        self.action_guard = ActionGuard(environment=environment)
        self.cooldown_manager = CooldownManager()
    
    def select_action(self, state: Tuple[str, str, str], deployment_id: str) -> Optional[str]:
        if random.random() < self.epsilon:
            action = random.choice(self.ACTIONS)
        else:
            q_values = self.q_store.get_all_actions(state)
            if not q_values:
                action = "noop"
            else:
                action = max(q_values, key=q_values.get)
        
        valid, reason = self.action_guard.validate_action(action, deployment_id)
        if not valid:
            logger.warning(f"Action blocked by guard: {reason}")
            return None
        
        can_execute, reason = self.cooldown_manager.can_execute(deployment_id, action)
        if not can_execute:
            logger.warning(f"Action blocked by cooldown: {reason}")
            return None
        
        return action
    
    def update_q_table(self, state: Tuple, action: str, reward: float, next_state: Tuple):
        if self.environment != "DEV":
            logger.info(f"Reward logged (no update): state={state}, action={action}, reward={reward}")
            return
        
        current_q = self.q_store.get_q_value(state, action)
        next_q_values = self.q_store.get_all_actions(next_state)
        max_next_q = max(next_q_values.values()) if next_q_values else 0.0
        
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.q_store.update_q_value(state, action, new_q)
        logger.info(f"Q-table updated: state={state}, action={action}, Q={new_q:.2f}")
    
    def record_action(self, deployment_id: str, action: str):
        self.cooldown_manager.record_action(deployment_id, action)
