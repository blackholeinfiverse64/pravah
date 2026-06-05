import asyncio
import logging
import time
from datetime import datetime
from rl.autonomy_loop import AutonomyLoop
from clients.telemetry_client import TelemetryClient
from clients.orchestrator_client import OrchestratorClient
from store.deployment_store import DeploymentStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stability_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def stability_test(duration_minutes: int = 60):
    logger.info(f"Starting {duration_minutes}-minute stability test")
    
    telemetry_client = TelemetryClient()
    orchestrator_client = OrchestratorClient()
    deployment_store = DeploymentStore()
    
    deployment_store.add_deployment({"id": "test-app-1", "name": "stability-test"})
    
    autonomy_loop = AutonomyLoop(
        environment="DEV",
        telemetry_client=telemetry_client,
        orchestrator_client=orchestrator_client,
        deployment_store=deployment_store
    )
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    loop_task = asyncio.create_task(autonomy_loop.start(interval_seconds=30))
    
    try:
        while time.time() < end_time:
            elapsed = time.time() - start_time
            remaining = end_time - time.time()
            logger.info(f"Elapsed: {elapsed/60:.1f}m | Remaining: {remaining/60:.1f}m")
            await asyncio.sleep(60)
        
        logger.info("Stability test completed successfully")
        
    except Exception as e:
        logger.error(f"Stability test failed: {e}")
    finally:
        autonomy_loop.stop()
        loop_task.cancel()
        
        logger.info(f"Q-table size: {len(autonomy_loop.agent.q_store.q_table)}")
        logger.info("Test complete")

if __name__ == "__main__":
    asyncio.run(stability_test(duration_minutes=60))
