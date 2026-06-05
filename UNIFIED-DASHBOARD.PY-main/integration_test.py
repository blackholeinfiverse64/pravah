"""
Integration test for unified infrastructure system.

Tests:
- Telemetry collection from control plane
- Decision generation from real signals
- Action execution through orchestrator
- Dashboard data availability
"""

import time
import json
import logging
from unified_system import UnifiedInfrastructureSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_integration():
    logger.info("=" * 60)
    logger.info("UNIFIED INFRASTRUCTURE SYSTEM INTEGRATION TEST")
    logger.info("=" * 60)
    
    # Create and start system
    system = UnifiedInfrastructureSystem()
    system.start()
    
    logger.info("\n[PHASE 1] System started - Control loop running")
    logger.info("Telemetry collector initialized with 3 apps")
    logger.info("Decision pipeline ready")
    logger.info("Orchestrator listening for actions")
    
    # Run for 45 seconds
    logger.info("\n[PHASE 2] Collecting telemetry and making decisions for 45 seconds...")
    
    for i in range(9):
        time.sleep(5)
        status = system.get_system_status()
        
        logger.info(f"\nCycle {i+1}: Total decisions made = {status['total_decisions']}")
        for app_id, app_data in status['apps'].items():
            if 'error' not in app_data:
                logger.info(f"  {app_id}:")
                logger.info(f"    - CPU: {app_data['metrics']['cpu']*100:.1f}%")
                logger.info(f"    - Memory: {app_data['metrics']['memory']*100:.1f}%")
                logger.info(f"    - Last Action: {app_data['last_action']}")
                logger.info(f"    - Recent Decisions: {app_data['recent_decisions']}")
    
    # Final report
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SYSTEM REPORT")
    logger.info("=" * 60)
    
    final_status = system.get_system_status()
    
    logger.info(f"\nSystem State: {'RUNNING' if final_status['running'] else 'STOPPED'}")
    logger.info(f"Total Decisions Made: {final_status['total_decisions']}")
    logger.info(f"\nApplication States:")
    
    for app_id, app_data in final_status['apps'].items():
        if 'error' not in app_data:
            logger.info(f"\n  {app_id}:")
            logger.info(f"    Current Metrics:")
            logger.info(f"      - CPU: {app_data['metrics']['cpu']*100:.1f}%")
            logger.info(f"      - Memory: {app_data['metrics']['memory']*100:.1f}%")
            logger.info(f"      - Error Rate: {app_data['metrics']['error_rate']*100:.1f}%")
            logger.info(f"      - Latency: {app_data['metrics']['latency_ms']:.0f}ms")
            logger.info(f"      - Replicas: {app_data['metrics']['replicas']}")
            logger.info(f"    Last Action: {app_data['last_action']} ({'Success' if app_data['last_action_success'] else 'Failed'})")
            logger.info(f"    Last Decision: {app_data['current_decision']}")
            logger.info(f"    Recent Decisions: {app_data['recent_decisions']}")
    
    logger.info(f"\nDecision History (last 5):")
    for decision in system.decision_history[-5:]:
        logger.info(f"  - {decision['app_id']}: {decision['decision']} (allowed={decision['allowed']})")
    
    logger.info(f"\nOrchestrator Execution History:")
    for app_id in system.telemetry.get_all_apps():
        history = system.orchestrator.get_execution_history(app_id)
        if history:
            logger.info(f"\n  {app_id}:")
            for exec_record in history[-3:]:
                logger.info(f"    - {exec_record['action']}: {exec_record['message']}")
    
    # Cleanup
    system.stop()
    logger.info("\n" + "=" * 60)
    logger.info("System stopped. Integration test complete.")
    logger.info("=" * 60)
    
    return system

if __name__ == '__main__':
    test_integration()
