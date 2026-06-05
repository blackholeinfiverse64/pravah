"""Unified Infrastructure Control System.

This is the main orchestrator that combines:
- Control plane (telemetry + orchestration)
- Decision brain (intelligence layer)  
- Monitoring dashboard (visibility)

The system runs a continuous control loop:
Runtime Telemetry -> Decision Brain -> Action Enforcement -> Orchestrator Execution
"""

import time
import logging
import threading
import json
from typing import Dict, Any, List

from control_plane.telemetry_collector import TelemetryCollector
from control_plane.orchestrator import Orchestrator
from control_plane.runtime_producer import RuntimeProducer

from orchestrator import OrchestratorClient
from action_scope import ActionScopeEnforcer
from state import AppStateStore
from pipeline import DecisionPipeline, DecisionGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedInfrastructureSystem:
    """Integrated infrastructure monitoring and control."""

    def __init__(self):
        # Control plane
        self.telemetry = TelemetryCollector()
        self.orchestrator = Orchestrator(self.telemetry)
        self.runtime_producer = RuntimeProducer(self.telemetry)

        # Decision layer
        self.app_state_store = AppStateStore()
        self.action_scope_enforcer = ActionScopeEnforcer()
        self.decision_generator = DecisionGenerator()
        
        # Orchestrator client with transport to real orchestrator
        self.orchestrator_client = OrchestratorClient(
            transport=self._send_to_orchestrator
        )
        
        # Decision pipeline
        self.decision_pipeline = DecisionPipeline(
            orchestrator=self.orchestrator_client,
            action_scope_enforcer=self.action_scope_enforcer,
            app_state_store=self.app_state_store,
            decision_generator=self.decision_generator,
            enable_learning=False
        )

        self.running = False
        self.decision_history = []
        self.processing_thread = None
        self.started_at = time.time()
        self.telemetry_events_ingested = 0

    def _send_to_orchestrator(self, decision_payload: Dict[str, Any]) -> tuple:
        """Transport: send decision to real orchestrator."""
        try:
            result = self.orchestrator.execute_action(decision_payload)
            return (result.success, result.message, result.details)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return (False, str(e), {})

    def process_telemetry_loop(self):
        """Main control loop: collect telemetry, make decisions, execute."""
        logger.info("Starting telemetry processing loop")
        
        while self.running:
            try:
                # Get all runtime payloads
                payloads = self.runtime_producer.get_all_payloads()
                
                for payload in payloads:
                    # Process through decision pipeline
                    result = self.decision_pipeline.process_payload(payload)
                    
                    # Record
                    self.decision_history.append({
                        'timestamp': time.time(),
                        'app_id': result.app_id,
                        'decision_id': result.decision_id,
                        'action_requested': result.action_requested.value,
                        'action_emitted': result.action_emitted.value,
                        'decision': result.decision.value,
                        'allowed': result.action_allowed,
                        'reason': result.reason,
                        'orchestrator_acknowledged': result.orchestrator_acknowledged,
                    })
                    
                    logger.info(
                        f"Decision: app={result.app_id} "
                        f"decision={result.decision.value} "
                        f"allowed={result.action_allowed}"
                    )
                
                time.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                logger.error(f"Telemetry loop error: {e}")
                time.sleep(1)

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system state for dashboard."""
        apps_data = {}
        active_apps = self.telemetry.get_all_apps()
        
        for app_id in active_apps:
            try:
                metrics = self.telemetry.collect_metrics(app_id)
                last_exec = self.orchestrator.get_last_execution(app_id)
                recent_decisions = [
                    d for d in self.decision_history[-20:]
                    if d['app_id'] == app_id
                ]
                
                apps_data[app_id] = {
                    'metrics': {
                        'cpu': round(metrics.cpu_usage, 3),
                        'memory': round(metrics.memory_usage, 3),
                        'error_rate': round(metrics.error_rate, 3),
                        'latency_ms': round(metrics.latency_ms, 1),
                        'replicas': metrics.replica_count
                    },
                    'last_action': last_exec.get('action', 'NONE'),
                    'last_action_success': last_exec.get('success', False),
                    'recent_decisions': len(recent_decisions),
                    'current_decision': recent_decisions[-1]['action_emitted'] if recent_decisions else 'NONE',
                    'last_decision_status': (
                        'success'
                        if recent_decisions and recent_decisions[-1].get('orchestrator_acknowledged') is True
                        else 'failed' if recent_decisions and recent_decisions[-1].get('orchestrator_acknowledged') is False
                        else 'not_executed'
                    ) if recent_decisions else 'unknown',
                    'decision_history': recent_decisions[-10:],
                }
            except Exception as e:
                logger.error(f"Status error for {app_id}: {e}")
                apps_data[app_id] = {'error': str(e)}

        return {
            'running': self.running,
            'total_decisions': len(self.decision_history),
            'active_applications': active_apps,
            'telemetry_events_ingested': self.telemetry_events_ingested,
            'apps': apps_data,
            'uptime_seconds': round(time.time() - self.started_at, 2),
        }

    def register_application(
        self,
        app_id: str,
        replicas: int = 1,
        initial_signals: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Register app in control plane registry for multi-app runtime."""
        self.telemetry.register_app(
            app_id=app_id,
            replicas=replicas,
            initial_metrics=initial_signals or {},
        )
        return {
            "app_id": app_id,
            "replicas": replicas,
            "registered": True,
        }

    def ingest_telemetry(self, app_id: str, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest runtime telemetry directly from control-plane emitters."""
        self.telemetry.ingest_runtime_signals(app_id=app_id, signals=signals)
        self.telemetry_events_ingested += 1
        return {
            "app_id": app_id,
            "ingested": True,
            "total_events": self.telemetry_events_ingested,
        }

    def start(self):
        """Start the unified system."""
        logger.info("Starting unified infrastructure system")
        self.running = True
        
        self.processing_thread = threading.Thread(
            target=self.process_telemetry_loop,
            daemon=True
        )
        self.processing_thread.start()

    def stop(self):
        """Stop the system."""
        logger.info("Stopping system")
        self.running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)


def main():
    """Test the system."""
    system = UnifiedInfrastructureSystem()
    system.start()
    
    logger.info("System running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(10)
            status = system.get_system_status()
            logger.info(f"System status: {json.dumps(status, indent=2)}")
    except KeyboardInterrupt:
        system.stop()
        logger.info("System stopped")


if __name__ == '__main__':
    main()
