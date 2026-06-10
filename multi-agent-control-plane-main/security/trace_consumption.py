#!/usr/bin/env python3
"""Pravah Security - Trace Consumption Registry for Single-Use Trace Protection"""
import os
import json
import time
from typing import Set

class TraceConsumptionRegistry:
    """Stores consumed trace IDs to prevent duplicate actions using the same trace context."""
    
    def __init__(self, store_file: str = 'security/trace_consumption.json', ttl: int = 86400):
        # Resolve store file path relative to multi-agent-control-plane-main root if needed,
        # but absolute/relative workspace paths are fine.
        self.store_file = store_file
        self.ttl = ttl  # Trace retention in seconds (default 24 hours)
        self.consumed_traces: Set[str] = set()
        self.timestamps = {}
        self._load_store()
    
    def _load_store(self):
        """Load consumed traces from disk."""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, 'r') as f:
                    data = json.load(f)
                    self.consumed_traces = set(data.get('traces', []))
                    self.timestamps = data.get('timestamps', {})
                    self._cleanup_expired()
            except Exception:
                pass
    
    def _save_store(self):
        """Save consumed traces to disk."""
        os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
        try:
            with open(self.store_file, 'w') as f:
                json.dump({
                    'traces': list(self.consumed_traces),
                    'timestamps': self.timestamps
                }, f)
        except Exception:
            pass
    
    def _cleanup_expired(self):
        """Remove trace IDs older than TTL."""
        current_time = time.time()
        expired = [
            trace_id for trace_id, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        for trace_id in expired:
            self.consumed_traces.discard(trace_id)
            self.timestamps.pop(trace_id, None)
    
    def is_consumed(self, trace_id: str) -> bool:
        """Check if a trace ID has already been consumed."""
        if not trace_id:
            return True
        self._cleanup_expired()
        return trace_id in self.consumed_traces
    
    def consume(self, trace_id: str) -> bool:
        """
        Record trace ID consumption.
        Returns True if successfully consumed (first time), False if already consumed.
        """
        if not trace_id:
            return False
        
        self._cleanup_expired()
        if trace_id in self.consumed_traces:
            return False
        
        self.consumed_traces.add(trace_id)
        self.timestamps[trace_id] = time.time()
        self._save_store()
        return True

# Global registry instance
_registry = None

def get_trace_registry() -> TraceConsumptionRegistry:
    """Get or create global trace consumption registry."""
    global _registry
    if _registry is None:
        _registry = TraceConsumptionRegistry()
    return _registry

def is_trace_consumed(trace_id: str) -> bool:
    """Check if a trace has already been consumed."""
    return get_trace_registry().is_consumed(trace_id)

def consume_trace(trace_id: str) -> bool:
    """Record trace ID as consumed."""
    return get_trace_registry().consume(trace_id)
