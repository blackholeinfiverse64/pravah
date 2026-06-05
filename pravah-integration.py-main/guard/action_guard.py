from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ActionGuard:
    DESTRUCTIVE_ACTIONS = {"stop", "redeploy", "restart"}
    DETERMINISTIC_ACTIONS = {"scale_up", "scale_down", "noop"}
    
    def __init__(self, environment: str = "DEV"):
        self.environment = environment.upper()
    
    def validate_action(self, action: str, deployment_id: str) -> tuple[bool, Optional[str]]:
        if self.environment == "DEV":
            return True, None
        
        if self.environment == "STAGE":
            if action not in self.DETERMINISTIC_ACTIONS:
                msg = f"STAGE: Destructive action '{action}' blocked"
                logger.warning(msg)
                return False, msg
            return True, None
        
        if self.environment == "PROD":
            if action in self.DESTRUCTIVE_ACTIONS:
                msg = f"PROD: Destructive action '{action}' blocked"
                logger.warning(msg)
                return False, msg
            
            if action not in {"scale_up", "scale_down", "noop"}:
                msg = f"PROD: Unsafe action '{action}' blocked"
                logger.warning(msg)
                return False, msg
            
            return True, None
        
        return False, f"Unknown environment: {self.environment}"
