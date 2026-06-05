from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from rl.autonomy_loop import AutonomyLoop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

autonomy_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global autonomy_loop
    
    environment = os.getenv("ENVIRONMENT", "DEV")
    
    from clients.telemetry_client import TelemetryClient
    from clients.orchestrator_client import OrchestratorClient
    from store.deployment_store import DeploymentStore
    
    telemetry_client = TelemetryClient()
    orchestrator_client = OrchestratorClient()
    deployment_store = DeploymentStore()
    
    autonomy_loop = AutonomyLoop(
        environment=environment,
        telemetry_client=telemetry_client,
        orchestrator_client=orchestrator_client,
        deployment_store=deployment_store
    )
    
    import asyncio
    loop_task = asyncio.create_task(autonomy_loop.start(interval_seconds=30))
    
    import webbrowser
    webbrowser.open('http://127.0.0.1:8000')
    
    logger.info(f"Pravah started: environment={environment}")
    
    yield
    
    autonomy_loop.stop()
    loop_task.cancel()
    logger.info("Pravah shutdown complete")

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "running", "autonomy": autonomy_loop.running if autonomy_loop else False}

@app.get("/q-table")
async def get_q_table():
    if autonomy_loop:
        return {"q_table": {str(k): v for k, v in autonomy_loop.agent.q_store.q_table.items()}}
    return {"q_table": {}}

@app.post("/deployments")
async def register_deployment(deployment: dict):
    logger.info(f"Deployment registered: {deployment}")
    return {"status": "registered", "deployment_id": deployment.get("id")}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    try:
        dashboard_path = Path(__file__).parent / "dashboard.html"
        return dashboard_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"<h1>Error loading dashboard: {e}</h1>"
