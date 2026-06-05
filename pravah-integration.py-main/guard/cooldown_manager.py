import time
from collections import defaultdict, deque
from typing import Dict, Deque
import logging

logger = logging.getLogger(__name__)

class CooldownManager:
    def __init__(self, cooldown_seconds: int = 60, max_actions: int = 3, window_seconds: int = 300):
        self.cooldown_seconds = cooldown_seconds
        self.max_actions = max_actions
        self.window_seconds = window_seconds
        
        self.last_action_time: Dict[tuple, float] = {}
        self.action_history: Dict[str, Deque[float]] = defaultdict(lambda: deque())
    
    def can_execute(self, deployment_id: str, action: str) -> tuple[bool, str]:
        now = time.time()
        key = (deployment_id, action)
        
        if key in self.last_action_time:
            elapsed = now - self.last_action_time[key]
            if elapsed < self.cooldown_seconds:
                msg = f"Cooldown: {action} blocked for {deployment_id} ({self.cooldown_seconds - elapsed:.0f}s remaining)"
                logger.warning(msg)
                return False, msg
        
        history = self.action_history[deployment_id]
        while history and now - history[0] > self.window_seconds:
            history.popleft()
        
        if len(history) >= self.max_actions:
            msg = f"Rate limit: {deployment_id} exceeded {self.max_actions} actions in {self.window_seconds}s"
            logger.warning(msg)
            return False, msg
        
        return True, ""
    
    def record_action(self, deployment_id: str, action: str):
        now = time.time()
        key = (deployment_id, action)
        self.last_action_time[key] = now
        self.action_history[deployment_id].append(now)
