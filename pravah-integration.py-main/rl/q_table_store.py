import json
import os
from pathlib import Path
from typing import Dict, Tuple

class QTableStore:
    def __init__(self, storage_path: str = "data/q_table.json", environment: str = "DEV"):
        self.storage_path = Path(storage_path)
        self.environment = environment.upper()
        self.q_table: Dict[Tuple, Dict[str, float]] = {}
        self._ensure_storage_dir()
        self.load()
    
    def _ensure_storage_dir(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self):
        if self.storage_path.exists():
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.q_table = {eval(k): v for k, v in data.items()}
        else:
            self.q_table = {}
    
    def save(self):
        if self.environment != "DEV":
            return
        with open(self.storage_path, 'w') as f:
            data = {str(k): v for k, v in self.q_table.items()}
            json.dump(data, f, indent=2)
    
    def get_q_value(self, state: Tuple, action: str) -> float:
        return self.q_table.get(state, {}).get(action, 0.0)
    
    def update_q_value(self, state: Tuple, action: str, value: float):
        if self.environment != "DEV":
            return
        if state not in self.q_table:
            self.q_table[state] = {}
        self.q_table[state][action] = value
        self.save()
    
    def get_all_actions(self, state: Tuple) -> Dict[str, float]:
        return self.q_table.get(state, {})
