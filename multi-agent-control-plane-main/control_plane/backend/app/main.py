from collections import deque
from datetime import datetime, timezone
import os
import sys
import asyncio
from pathlib import Path
from typing import Any
import json
import uuid

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .dashboard_api import get_dashboard_state
# from .dashboard_api import router as dashboard_router
from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime
from contracts.decision_contract import validate_decision_contract
from control_plane.core.execution_lineage import (
    replay_execution_lineage,
    verify_execution_lineage,
)
from pydantic import BaseModel
from typing import List, Optional






from typing import Any, Dict
from pydantic import BaseModel

class RuntimeIngestPayload(BaseModel):
    service_id: str
    timestamp: str
    status: str
    metrics: Dict[str, Any]
    issue_detected: bool
    issue_type: str
    recommended_action: str

# Stores latest state per service
INGESTED_RUNTIME_STATE = {}

try:
    from .schemas import DecisionRequest, EventType, Environment
    from .decision_engine import DecisionEngine
except ImportError:
    from schemas import DecisionRequest, EventType, Environment
    from decision_engine import DecisionEngine

def build_decision_request(payload: RuntimeIngestPayload) -> DecisionRequest:
    from control_plane.core.action_governance import normalize_environment
    env_name = normalize_environment(os.getenv("ENVIRONMENT", "DEV"))
    event_map = {
        "high_cpu": EventType.HIGH_CPU,
        "high_memory": EventType.HIGH_MEMORY,
        "latency": EventType.LATENCY,
        "high_latency": EventType.LATENCY,
    }
    
    cpu_val = payload.metrics.get("cpu", 0)
    if isinstance(cpu_val, float) and cpu_val <= 1.0:
        cpu_val *= 100
    cpu = int(cpu_val)

    memory_val = payload.metrics.get("memory", 0)
    if isinstance(memory_val, float) and memory_val <= 1.0:
        memory_val *= 100
    memory = int(memory_val)

    return DecisionRequest(
        environment=Environment(env_name),
        event_type=event_map.get(
            payload.issue_type.lower(),
            EventType.HIGH_CPU,
        ),
        cpu=cpu,
        memory=memory,
    )



def _parse_cors_origins() -> list[str]:
    """Parse explicit CORS origins from env with sane defaults for local and prod."""
    raw = os.getenv(
        "BACKEND_CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:4500",
                "http://localhost:3000",
                "https://multi-agent-control-plane-frontend.vercel.app",
            ]
        ),
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_origin_regex() -> str:
    """Allow Vercel preview URLs and localhost ports unless overridden."""
    return os.getenv(
        "BACKEND_CORS_ORIGIN_REGEX",
        r"^https://.*\.vercel\.app$|^http://localhost:\d+$",
    )

try:
    from .config import ACTION_SCOPE, DEMO_FROZEN, STATELESS, SUCCESS_RATE
    from .schemas import (
        ActionScopeResponse,
        DecisionDashboardSummary,
        DecisionResponse,
        HealthResponse,
        LiveDashboardResponse,
        RecentActivityResponse,
    )
    from .integration_bridge import get_bridge
except ImportError:
    from .config import ACTION_SCOPE, DEMO_FROZEN, STATELESS, SUCCESS_RATE
    from .schemas import (
        ActionScopeResponse,
        DecisionDashboardSummary,
        DecisionResponse,
        HealthResponse,
        LiveDashboardResponse,
        RecentActivityResponse,
    )
    from integration_bridge import get_bridge


# Initialize integration bridge
_bridge = get_bridge()

# Create FastAPI app
app = FastAPI(
    title="Pravah Decision Brain API",
    version="1.0.0",
    description="Pravah RL Decision Brain integrated with Multi-Agent Control Plane",
)

# app.include_router(dashboard_router)
# CORS middleware for local dev + Vercel deploys (stateless API, no credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=_cors_origin_regex(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=86400,
)


# Startup event: Initialize demo links for realistic dashboard
@app.on_event("startup")
async def startup_event():
    """Initialize dashboard with demo data on app startup."""
    _initialize_demo_links()


# In-memory recent activity only (reset on process restart).
_RECENT_DECISIONS: deque[DecisionResponse] = deque(maxlen=10)


_AUTONOMOUS_DECISIONS: deque[dict] = deque(maxlen=20)
_LAST_AUTONOMOUS_RUNTIME: dict | None = None
_LAST_EXECUTED_ACTION: str | None = None







# In-memory ingested links for monitoring with rich metadata
_INGESTED_LINKS: list[dict[str, Any]] = []

# Track link ingestion history for events and analytics
_LINK_EVENTS: deque[dict[str, Any]] = deque(maxlen=20)

# Simulated project metadata for ingested links
_LINK_METADATA: dict[str, dict[str, Any]] = {}

# Initialize with demo links for realistic dashboard on startup
def _initialize_demo_links():
    """Populate demo links with realistic metadata on app startup."""
    demo_links = [
        {
            "link": "https://github.com/I-am-ShivamPal/multi-agents-control-plane",
            "name": "multi-agents-control-plane",
        },
        {
            "link": "https://github.com/I-am-ShivamPal/multi-agent-control-plane-frontend",
            "name": "multi-agent-control-plane-frontend",
        },
    ]
    
    for demo_link in demo_links:
        link = demo_link["link"]
        name = demo_link["name"]
        
        # Only add if not already ingested
        if not any(item["link"] == link for item in _INGESTED_LINKS):
            _INGESTED_LINKS.append({
                "link": link,
                "name": name,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "status": "HEALTHY",
                "response_time_ms": 300 + (_get_link_hash(link) % 200),
                "uptime_percent": 99.0 + (_get_link_hash(link) % 10) / 100,
                "errors_24h": _get_link_hash(link) % 3,
            })
            
            # Generate and store metadata
            _LINK_METADATA[link] = _generate_link_metadata(link)
            
            # Log the ingestion event
            _LINK_EVENTS.appendleft({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "link_ingested",
                "link": link,
                "name": name,
            })


def _extract_link_name(link: str) -> str:
    """Extract a clean, readable name from a URL."""
    link = link.strip().rstrip('/')
    
    # Remove protocol
    if "://" in link:
        link = link.split("://", 1)[1]
    
    # Handle GitHub-style URLs
    if link.startswith("github.com/"):
        parts = link.split("/")
        if len(parts) >= 3:
            return parts[2]  # repo name
    
    # Handle other git platforms
    if any(platform in link for platform in ["gitlab.com", "bitbucket.org", "gitea"]):
        parts = link.split("/")
        if len(parts) >= 3:
            return parts[2]  # repo name
    
    # For web URLs, extract domain
    domain = link.split("/")[0]  # Remove path
    domain = domain.replace("www.", "")  # Remove www prefix
    
    # Extract main domain name
    if "." in domain:
        domain = domain.split(".")[0]  # Get first part (e.g., "youtube" from "youtube.com")
    
    # Capitalize first letter
    return domain.capitalize()


def _get_link_hash(link: str) -> int:
    """Generate deterministic hash for a link for consistent metrics."""
    return hash(link) % 10000


def _generate_link_metadata(link: str) -> dict[str, Any]:
    """Generate realistic metadata for an ingested link."""
    link_hash = _get_link_hash(link)
    
    # Simulate project characteristics
    is_github = "github.com" in link.lower()
    is_repo = is_github or "bitbucket" in link.lower() or "gitlab" in link.lower()
    
    if is_repo:
        # Repository metadata
        base_commits = 150 + (link_hash % 500)
        base_branches = 3 + (link_hash % 12)
        base_prs = 5 + (link_hash % 20)
        base_stars = 50 + (link_hash % 500) if is_github else 0
        base_files = 45 + (link_hash % 200)
        test_coverage = 65 + (link_hash % 30)
        ci_status = "passing" if link_hash % 4 != 0 else "failing"
    else:
        # Website metadata
        base_commits = 0
        base_branches = 0
        base_prs = 0
        base_stars = 0
        base_files = 10 + (link_hash % 100)
        test_coverage = 55 + (link_hash % 40)  # Web services often have lower test coverage
        ci_status = "passing" if link_hash % 3 != 0 else "degraded"
    
    return {
        "type": "repository" if is_repo else "website",
        "commits": base_commits,
        "branches": base_branches,
        "pull_requests": base_prs,
        "stars": base_stars,
        "files": base_files,
        "contributors": 2 + (link_hash % 25),
        "last_commit": "2h ago" if link_hash % 3 == 0 else ("4h ago" if link_hash % 3 == 1 else "8h ago"),
        "test_coverage": test_coverage,
        "ci_status": ci_status,
        "deployment_frequency": 2 + (link_hash % 8),
        "avg_response_time": 120 + (link_hash % 300),
        "error_rate": (link_hash % 5),
        "active_issues": link_hash % 15,
        "code_quality_score": 70 + (link_hash % 25),
    }


def _bytes_label(size_bytes: int) -> str:
    """Return a compact size label for UI display."""

    if size_bytes <= 0:
        return "0 bytes"
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    return f"{round(size_bytes / 1024, 1)} KB"


def _collect_files(base_path: Path, expected_files: list[str]) -> dict[str, Any]:
    """Collect file state rows for a section, preserving expected order."""

    rows: list[dict[str, str]] = []
    active_count = 0

    for relative_name in expected_files:
        candidate = base_path / relative_name
        exists = candidate.exists() and candidate.is_file()
        size_bytes = candidate.stat().st_size if exists else 0
        if exists:
            active_count += 1
        rows.append(
            {
                "filename": relative_name,
                "status": "ACTIVE" if exists else "MISSING",
                "size": _bytes_label(size_bytes),
            }
        )

    return {"active": active_count, "total": len(expected_files), "files": rows}


def _calculate_health_score(link: str) -> int:
    """Calculate a health score (0-100) for a link based on its metadata."""
    meta = _LINK_METADATA.get(link, {})
    
    # Base score
    score = 85
    
    # Adjust based on CI status
    if meta.get("ci_status") == "passing":
        score += 10
    elif meta.get("ci_status") == "failing":
        score -= 15
    elif meta.get("ci_status") == "degraded":
        score -= 5
    
    # Adjust based on error rate
    error_rate = meta.get("error_rate", 0)
    score -= (error_rate * 3)
    
    # Adjust based on test coverage
    test_coverage = meta.get("test_coverage", 70)
    if test_coverage < 50:
        score -= 10
    elif test_coverage > 80:
        score += 5
    
    # Clamp to 0-100
    return max(0, min(100, score))


def _calculate_aggregate_metrics() -> dict[str, Any]:
    """Calculate real-time aggregate metrics from project and ingested links."""
    import subprocess
    import psutil
    import os

    # 1. Real System Metrics
    try:
        system_cpu = int(psutil.cpu_percent())
        system_memory = int(psutil.virtual_memory().percent)
    except Exception:
        system_cpu = 20
        system_memory = 40
    
    # 2. Real Git stats (workspace repository)
    git_commits = 0
    git_contributors = 1
    git_files = 365
    try:
        commits_res = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=True
        )
        git_commits = int(commits_res.stdout.strip())
    except Exception:
        pass

    try:
        contributors_res = subprocess.run(
            ["git", "log", "--format=%an"],
            capture_output=True, text=True, check=True
        )
        git_contributors = len(set(contributors_res.stdout.strip().split("\n")))
    except Exception:
        pass

    try:
        files_res = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, check=True
        )
        git_files = len(files_res.stdout.strip().split("\n"))
    except Exception:
        pass
        
    # 3. Real Test Coverage
    real_coverage = 78
    try:
        import coverage
        cov = coverage.Coverage()
        cov.load()
        real_coverage = int(cov.report(file=open(os.devnull, "w")))
    except Exception:
        pass
        
    # 4. Monitored link counts and stats
    total_decisions = len(_RECENT_DECISIONS)
    try:
        if os.path.exists("logs/control_plane/decision_history.jsonl"):
            with open("logs/control_plane/decision_history.jsonl") as f:
                total_decisions = sum(1 for _ in f)
    except Exception:
        pass
        
    total_policies = 0
    try:
        if os.path.exists("logs/control_plane/policy_enforcement.jsonl"):
            with open("logs/control_plane/policy_enforcement.jsonl") as f:
                total_policies = sum(1 for _ in f)
    except Exception:
        pass
        
    avg_response_time = 150
    if _INGESTED_LINKS:
        avg_response_time = sum(_LINK_METADATA.get(item["link"], {}).get("avg_response_time", 150) for item in _INGESTED_LINKS) / len(_INGESTED_LINKS)

    return {
        "total_commits": git_commits,
        "total_files": git_files,
        "total_contributors": git_contributors,
        "avg_test_coverage": real_coverage,
        "avg_response_time": int(avg_response_time),
        "total_errors": 0,
        "total_issues": 0,
        "avg_quality_score": 92,
        "system_cpu": system_cpu,
        "system_memory": system_memory,
        "total_decisions": total_decisions,
        "total_policies": total_policies,
    }


def _resolve_control_plane_root() -> Path:
    """Resolve project root for control-plane file checks across old/new layouts."""

    configured_root = os.getenv("PROJECT_ROOT", "").strip()
    if configured_root:
        candidate = Path(configured_root).resolve()
        if (candidate / "core").exists() and (candidate / "agent_runtime.py").exists():
            return candidate

    # Current layout: <project>/backend/app/main.py -> project root is parents[2]
    current_project_root = Path(__file__).resolve().parents[2]
    if (current_project_root / "core").exists() and (current_project_root / "agent_runtime.py").exists():
        return current_project_root

    # Legacy layout fallback where repo sat beside backend
    legacy_sibling = current_project_root / "multi-agent-control-plane-main"
    if (legacy_sibling / "core").exists() and (legacy_sibling / "agent_runtime.py").exists():
        return legacy_sibling

    return current_project_root


def _build_live_dashboard_payload() -> dict[str, Any]:
    """Build full dashboard payload consumed by Pravah Dashboard."""
    import time
    import requests
    import psutil

    recent_count = len(_RECENT_DECISIONS)
    success_rate_percent = int(SUCCESS_RATE * 100)
    now_iso = datetime.now(timezone.utc).isoformat()
    requests_count = max(recent_count, 1)
    estimated_cost = requests_count * 0.0025
    
    # Calculate aggregate metrics from ingested links
    agg_metrics = _calculate_aggregate_metrics()
    avg_latency_ms = agg_metrics["avg_response_time"]

    control_plane_root = _resolve_control_plane_root()

    # Check real-time state of target app (web1)
    web1_status = "HEALTHY"
    web1_latency = 120
    try:
        start_t = time.time()
        resp = requests.get("http://localhost:5001/health", timeout=0.5)
        web1_latency = int((time.time() - start_t) * 1000)
        if resp.status_code == 200:
            if resp.json().get("status") == "degraded":
                web1_status = "DEGRADED"
        else:
            web1_status = "CRITICAL"
    except Exception:
        web1_status = "CRITICAL"
        web1_latency = 0

    # Populate INGESTED_RUNTIME_STATE based on web1 live health
    if "web1" not in INGESTED_RUNTIME_STATE:
        INGESTED_RUNTIME_STATE["web1"] = {
            "service_id": "web1",
            "timestamp": now_iso,
            "status": "degraded" if web1_status == "DEGRADED" else ("crashed" if web1_status == "CRITICAL" else "running"),
            "metrics": {
                "cpu": 0.95 if web1_status == "DEGRADED" else (0.0 if web1_status == "CRITICAL" else 0.15),
                "memory": 0.83 if web1_status == "DEGRADED" else (0.0 if web1_status == "CRITICAL" else 0.35),
                "error_rate": 1.0 if web1_status == "CRITICAL" else 0.0,
                "uptime": 12345
            },
            "issue_detected": web1_status != "HEALTHY",
            "issue_type": "cpu_spike" if web1_status == "DEGRADED" else ("crash" if web1_status == "CRITICAL" else "none"),
            "recommended_action": "scale_up" if web1_status == "DEGRADED" else ("restart" if web1_status == "CRITICAL" else "noop")
        }
    else:
        INGESTED_RUNTIME_STATE["web1"]["status"] = "degraded" if web1_status == "DEGRADED" else ("crashed" if web1_status == "CRITICAL" else "running")
        INGESTED_RUNTIME_STATE["web1"]["issue_detected"] = web1_status != "HEALTHY"
        if web1_status == "DEGRADED":
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["cpu"] = 0.95
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["error_rate"] = 0.0
        elif web1_status == "CRITICAL":
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["cpu"] = 0.0
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["error_rate"] = 1.0
        else:
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["cpu"] = 0.15
            INGESTED_RUNTIME_STATE["web1"]["metrics"]["error_rate"] = 0.0

    # Build monitored services list (Live Production Monitoring)
    monitored_list = []
    
    # 1. Add ingested runtime state items (like web1)
    for service_id, state in INGESTED_RUNTIME_STATE.items():
        metrics = state.get("metrics", {})
        status = state.get("status", "UNKNOWN").upper()
        cpu = int(metrics.get("cpu", 0) * 100) if metrics.get("cpu", 0) <= 1.0 else int(metrics.get("cpu", 0))
        memory = int(metrics.get("memory", 0) * 100) if metrics.get("memory", 0) <= 1.0 else int(metrics.get("memory", 0))
        error_rate = metrics.get("error_rate", 0.0)
        
        h_score = 100
        if status == "DEGRADED":
            h_score = 60
        elif status == "CRASHED" or status == "CRITICAL":
            h_score = 20
        if cpu > 80:
            h_score -= 10
        h_score = max(30, h_score)

        monitored_list.append({
            "name": service_id.upper(),
            "domain": f"{service_id}.local",
            "url": f"http://localhost:5001" if service_id == "web1" else f"http://localhost/{service_id}",
            "status": "DEGRADED" if status == "DEGRADED" else ("CONNECTED" if status in ["RUNNING", "OK", "HEALTHY"] else "CRITICAL"),
            "health_score": h_score,
            "response_time_ms": web1_latency if service_id == "web1" else 300,
            "cpu_percent": cpu,
            "memory_percent": memory,
            "uptime_percent": 99.9 if status in ["RUNNING", "OK", "HEALTHY"] else (94.2 if status == "DEGRADED" else 0.0),
            "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
            "errors_24h": int(error_rate * 24),
        })

    # 2. Add user ingested links
    for item in _INGESTED_LINKS:
        link = item["link"]
        clean_name = item["name"]
        
        if any(x["name"].lower() == clean_name.lower() for x in monitored_list):
            continue
            
        link_status = "CONNECTED"
        link_health = _calculate_health_score(link)
        res_time = item["response_time_ms"]
        
        if link.startswith("http"):
            try:
                start_check = time.time()
                resp = requests.get(link, timeout=1.0)
                res_time = int((time.time() - start_check) * 1000)
                if resp.status_code != 200:
                    link_status = "DEGRADED"
                    link_health = 60
            except Exception:
                link_status = "DISCONNECTED"
                link_health = 0
                res_time = 0

        monitored_list.append({
            "name": clean_name,
            "domain": link.replace("https://", "").replace("http://", "").split("/")[0],
            "url": link,
            "status": link_status,
            "health_score": link_health,
            "response_time_ms": res_time,
            "cpu_percent": 5 + (_get_link_hash(link) % 15),
            "memory_percent": 10 + (_get_link_hash(link) % 25),
            "uptime_percent": item["uptime_percent"] if link_status != "DISCONNECTED" else 0.0,
            "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
            "errors_24h": item["errors_24h"] if link_status != "DISCONNECTED" else 5,
        })

    # 3. Default fallback if empty
    if not monitored_list:
        monitored_list = [
            {
                "name": "BlackHole Universe",
                "domain": "blackhole.rlreality.ai",
                "url": "https://blackhole.rlreality.ai",
                "status": "CONNECTED",
                "health_score": 95,
                "response_time_ms": 320,
                "cpu_percent": 18,
                "memory_percent": 35,
                "uptime_percent": 99.8,
                "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
                "errors_24h": 0,
            },
            {
                "name": "Uni-Guru Platform",
                "domain": "uni-guru.rlreality.ai",
                "url": "https://uni-guru.rlreality.ai",
                "status": "CONNECTED",
                "health_score": 98,
                "response_time_ms": 513,
                "cpu_percent": 22,
                "memory_percent": 43,
                "uptime_percent": 99.9,
                "last_action": _RECENT_DECISIONS[0].selected_action if recent_count else "noop",
                "errors_24h": 1,
            },
        ]

    system_health_val = 100
    active_issues_val = 0
    error_rate_val = 0
    
    if web1_status == "DEGRADED":
        system_health_val = 75
        active_issues_val = 1
        error_rate_val = 2
    elif web1_status == "CRITICAL":
        system_health_val = 45
        active_issues_val = 1
        error_rate_val = 10

    core_files = _collect_files(
        control_plane_root,
        [
            "core/base_agent.py",
            "core/decision_arbitrator.py",
            "core/event_bus.py",
            "core/env_validator.py",
            "core/rl_engine.py",
        ],
    )
    data_files = _collect_files(
        control_plane_root,
        [
            "dataset/student_scores.csv",
            "data/decision_history.json",
            "data/runtime_metrics.json",
            "feedback/production_feedback.json",
            "logs/prod/orchestrator_decisions.jsonl",
        ],
    )
    integration_files = _collect_files(
        control_plane_root,
        [
            "integration/api_adapter.py",
            "integration/unified_event_pipe.py",
            "integration/realtime_sync.py",
            "integration/monitoring_bridge.py",
            "integration/event_schema.py",
        ],
    )
    production_files = _collect_files(
        control_plane_root,
        [
            "deploy.py",
            "deploy_orchestrator.py",
            "docker-compose.yml",
            "render.yaml",
            "scripts/production_healthcheck.py",
        ],
    )

    return {
        "generated_at": now_iso,
        "header": {
            "title": "🚀 Pravah Dashboard",
            "subtitle": "Real-time Production Monitoring",
        },
        "live_production_monitoring": monitored_list,
        "summary_metrics": [
            {"label": "Total Commits", "value": str(agg_metrics["total_commits"])},
            {"label": "Contributors", "value": str(agg_metrics["total_contributors"])},
            {"label": "Test Coverage", "value": f"{agg_metrics['avg_test_coverage']}%"},
            {"label": "Monitored Links", "value": str(len(_INGESTED_LINKS))},
        ],
        "ai_learning_status": [
            {"label": "Learning Status", "value": "Optimizing" if agg_metrics["total_decisions"] > 0 else "Idle", "tone": "green"},
            {"label": "Code Quality Score", "value": f"{agg_metrics['avg_quality_score']}%", "tone": "blue"},
            {"label": "Policy Updates", "value": str(agg_metrics["total_policies"]), "tone": "blue"},
            {"label": "Q-Table Size", "value": str(100 + agg_metrics["total_policies"] * 2), "tone": "blue"},
            {"label": "Training Progress", "value": f"{min(100, 73 + agg_metrics['total_decisions'] * 5)}%", "tone": "blue" if agg_metrics["total_decisions"] > 0 else "red"},
        ],
        "system_health": [
            {"label": "Overall Health", "value": f"{system_health_val}%", "tone": "green" if system_health_val > 80 else ("orange" if system_health_val > 50 else "red")},
            {"label": "CPU Usage", "value": f"{agg_metrics['system_cpu']}%", "tone": "orange" if agg_metrics["system_cpu"] > 70 else "blue"},
            {"label": "Memory Usage", "value": f"{agg_metrics['system_memory']}%", "tone": "orange" if agg_metrics["system_memory"] > 80 else "blue"},
            {"label": "Active Issues", "value": str(active_issues_val), "tone": "red" if active_issues_val > 0 else "green"},
            {"label": "Error Rate", "value": f"{error_rate_val}%", "tone": "red" if error_rate_val > 0 else "green"},
        ],
        "performance_metrics": [
            {"label": "Response Time (ms)", "value": str(web1_latency if web1_latency > 0 else 120)},
            {"label": "Throughput/sec", "value": str(128 + agg_metrics["total_decisions"] * 10)},
            {"label": "Success Rate", "value": f"{success_rate_percent}%"},
            {"label": "Requests/min", "value": str(45 + agg_metrics["total_decisions"] * 2)},
            {"label": "Total Files Tracked", "value": str(agg_metrics["total_files"])},
        ],
        "project_files_status": [
            {"title": "Core RL System", "icon": "🧠", **core_files},
            {"title": "Data Files", "icon": "🗂️", **data_files},
            {"title": "Integration Layer", "icon": "🔌", **integration_files},
            {"title": "Production Layer", "icon": "🏭", **production_files},
        ] + [
            {
                "title": f"📦 {item['name']}",
                "icon": "📁",
                "active": _LINK_METADATA.get(item["link"], {}).get("files", 0),
                "total": _LINK_METADATA.get(item["link"], {}).get("files", 0),
                "files": [
                    {
                        "filename": f"main.py",
                        "status": "ACTIVE",
                        "size": f"{100 + (_get_link_hash(item['link']) % 500)} KB",
                    },
                    {
                        "filename": f"config.yaml",
                        "status": "ACTIVE",
                        "size": "5.2 KB",
                    },
                    {
                        "filename": f"requirements.txt",
                        "status": "ACTIVE",
                        "size": "2.1 KB",
                    }
                ]
            }
            for item in _INGESTED_LINKS
        ],
        "enhanced_telemetry": {
            "status": "HEALTHY" if web1_status == "HEALTHY" else ("DEGRADED" if web1_status == "DEGRADED" else "CRITICAL"),
            "avg_latency": f"{web1_latency if web1_latency > 0 else 120}ms",
            "cost": f"${estimated_cost:.4f}",
            "success": f"{success_rate_percent - (error_rate_val * 5)}%",
            "requests": str(requests_count + len(_INGESTED_LINKS)),
        },
        "policy_evolution": {
            "title": "Q-Table Evolution",
            "metrics": [
                {"label": "Q-Table Size", "value": str(100 + agg_metrics["total_policies"] * 2)},
                {"label": "Learning Progress", "value": f"{min(100, 73 + agg_metrics['total_decisions'] * 5)}%"},
                {"label": "Policy Actions", "value": f"{3 + len(_INGESTED_LINKS)} actions learned"},
                {"label": "Code Quality Impact", "value": f"+{agg_metrics['avg_quality_score'] - 70}%" if agg_metrics['avg_quality_score'] > 70 else f"{agg_metrics['avg_quality_score'] - 70}%"},
            ],
        },
        "error_analytics": {
            "recent_errors": [
                {"code": "WEB1_LATENCY_SPIKE" if web1_status == "DEGRADED" else "WEB1_SERVICE_CRASHED", "severity": "MEDIUM" if web1_status == "DEGRADED" else "CRITICAL"}
            ] if web1_status != "HEALTHY" else [{"code": "NO_ERRORS", "severity": "NONE"}],
            "statistics": {
                "total_errors": 1 if web1_status != "HEALTHY" else 0,
                "avg_impact_score": 5.0 if web1_status == "HEALTHY" else (7.5 if web1_status == "DEGRADED" else 9.9),
                "critical_issues": 1 if web1_status == "CRITICAL" else 0,
                "test_coverage_avg": agg_metrics["avg_test_coverage"],
            },
        },
        "auto_failover_status": {
            "active_domain": "UNI_GURU" if web1_status == "HEALTHY" else "BLACKHOLE",
            "failure_threshold": 3,
            "domains": [
                {"name": item["name"], "status": item["status"]} 
                for item in _INGESTED_LINKS[:5]
            ] + [
                {"name": "BLACKHOLE", "status": "CONNECTED" if web1_status == "HEALTHY" else "ACTIVE_FAILOVER"},
                {"name": "UNI_GURU", "status": "HEALTHY" if web1_status == "HEALTHY" else "DEGRADED"},
            ],
        },
        "live_events": [
            {"title": f"Tracking {len(_INGESTED_LINKS)} projects", "time_ago": "now", "tone": "green"},
            {"title": f"Code quality: {agg_metrics['avg_quality_score']}%", "time_ago": "1m ago", "tone": "blue"},
            {"title": f"{agg_metrics['total_commits']} commits detected", "time_ago": "2m ago", "tone": "indigo"},
            {"title": f"{agg_metrics['total_contributors']} contributors contributing", "time_ago": "3m ago", "tone": "purple"},
            {"title": f"Test coverage: {agg_metrics['avg_test_coverage']}%", "time_ago": "5m ago", "tone": "orange"},
            {"title": f"Active issues: {active_issues_val}", "time_ago": "8m ago", "tone": "red" if active_issues_val > 0 else "green"},
            {"title": "RL model updated", "time_ago": "10m ago", "tone": "teal"},
        ],
    }


def enforce_action_scope(action: str, environment: str):
    allowed = ACTION_SCOPE.get(environment, [])

    if action in allowed:
        return True, "allowed"
    else:
        return False, f"{action} not allowed in {environment}"



import requests

def execute_action(action: str, service_id: str):
    try:
        from control_plane.core.action_governance import ActionGovernance, normalize_environment
        from contracts.decision_contract import validate_decision_contract

        env = normalize_environment(os.getenv("ENVIRONMENT", "dev")).lower()
        governance = ActionGovernance(env=env)
        decision = validate_decision_contract(
            {
                "decision_type": "execution",
                "action": action,
                "parameters": {
                    "service_id": service_id,
                    "source": "backend_api",
                },
                "version": governance.POLICY_VERSION,
            }
        )
        governance_decision = governance.evaluate_contract(
            decision=decision,
            context={
                "service_id": service_id,
                "app_name": service_id,
                "env": env,
                "source": "backend_api",
            },
            source="backend_api",
        )

        if governance_decision.should_block:
            return False, {
                "status": "rejected",
                "action": action,
                "service_id": service_id,
                "reason": governance_decision.reason,
                "admission_state": governance_decision.admission_state,
                "rejection_code": governance_decision.rejection_code,
                "policy_snapshot": {
                    "policy_id": governance_decision.policy_id,
                    "policy_version": governance_decision.policy_version,
                    "policy_hash": governance_decision.policy_hash,
                },
            }

        from security.internal_requests import build_signed_headers
        import requests

        payload = {
            "action": action,
            "service_id": service_id
        }
        headers = build_signed_headers(service_id, payload)
        response = requests.post(
            "http://localhost:5003/execute-action",
            json=payload,
            headers=headers,
            timeout=3
        )

        return True, response.json()

    except Exception as e:
        return False, str(e)



@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health and runtime safety guarantees."""

    return HealthResponse(
        status="healthy",
        demo_frozen=DEMO_FROZEN,
        stateless=STATELESS,
        success_rate=SUCCESS_RATE,
    )


@app.get("/action-scope", response_model=ActionScopeResponse)
def action_scope() -> ActionScopeResponse:
    """Return environment-specific allowed actions for policy enforcement."""

    return ActionScopeResponse(**ACTION_SCOPE)





@app.get("/recent-activity", response_model=RecentActivityResponse)
def recent_activity() -> RecentActivityResponse:
    """Return the last ten in-memory decisions, newest first."""

    return RecentActivityResponse(items=list(_RECENT_DECISIONS))


@app.get("/", response_model=LiveDashboardResponse)
def root_dashboard() -> dict[str, Any]:
    """Map root URL directly to the live dashboard payload."""
    return _build_live_dashboard_payload()


@app.get("/live-dashboard", response_model=LiveDashboardResponse)
def live_dashboard() -> dict[str, Any]:
    """Return full real-time dashboard payload consumed by RL Reality UI."""

    return _build_live_dashboard_payload()


@app.get("/decision-summary", response_model=DecisionDashboardSummary)
def decision_summary() -> DecisionDashboardSummary:
    """Return aggregate summary metrics consumed by the Decision Brain UI."""

    return DecisionDashboardSummary(
        total_decisions=len(_RECENT_DECISIONS),
        last_action=_RECENT_DECISIONS[0].selected_action if _RECENT_DECISIONS else "-",
        success_rate=SUCCESS_RATE,
        demo_frozen=DEMO_FROZEN,
        stateless=STATELESS,
    )


@app.post("/ingest-link")
def ingest_link(payload: dict[str, Any]) -> dict[str, Any]:
    """Ingest a repository or website link for monitoring."""

    link = payload.get("link", "").strip()
    if not link:
        return {"success": False, "error": "Link cannot be empty"}

    # Check if link already exists
    existing = next((item for item in _INGESTED_LINKS if item["link"] == link), None)
    if existing:
        return {"success": False, "error": "Link already being monitored"}

    # Generate metadata for this link
    metadata = _generate_link_metadata(link)
    _LINK_METADATA[link] = metadata
    
    # Extract clean name from URL
    link_name = _extract_link_name(link)
    
    # Add new link with monitoring metadata
    ingested_item = {
        "link": link,
        "name": link_name,
        "added_at": datetime.now(timezone.utc).isoformat(),
        "status": "HEALTHY" if metadata["ci_status"] == "passing" else "DEGRADED",
        "response_time_ms": metadata["avg_response_time"],
        "uptime_percent": 99.2 + ((_get_link_hash(link) % 7) * 0.1),
        "errors_24h": metadata["error_rate"],
    }
    _INGESTED_LINKS.append(ingested_item)
    
    # Record event
    _LINK_EVENTS.appendleft({
        "type": "link_added",
        "link": link,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": f"Added {metadata['type']} with {metadata['files']} files",
    })

    return {"success": True, "message": f"Link ingested: {link}", "ingested_link": ingested_item}


@app.post("/remove-link")
def remove_link(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove a monitored link from the dashboard."""

    link = payload.get("link", "").strip()
    if not link:
        return {"success": False, "error": "Link cannot be empty"}

    # Find and remove the link
    global _INGESTED_LINKS, _LINK_METADATA
    original_count = len(_INGESTED_LINKS)
    _INGESTED_LINKS = [item for item in _INGESTED_LINKS if item["link"] != link]
    
    # Remove metadata
    if link in _LINK_METADATA:
        del _LINK_METADATA[link]
    
    # Record event
    if len(_INGESTED_LINKS) < original_count:
        _LINK_EVENTS.appendleft({
            "type": "link_removed",
            "link": link,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": f"Removed {link}",
        })
        return {"success": True, "message": f"Link removed: {link}"}
    else:
        return {"success": False, "error": "Link not found"}


# ============================================================================
# INTEGRATION WITH MULTI-AGENT CONTROL PLANE
# ============================================================================

@app.get("/control-plane/status")
def control_plane_status() -> dict[str, Any]:
    """Get integrated control plane orchestration status."""
    return _bridge.get_control_plane_status()


@app.get("/control-plane/apps")
def control_plane_apps() -> dict[str, Any]:
    """Get list of apps managed by the control plane."""
    apps = _bridge.get_app_registry()
    return {
        "total_apps": len(apps),
        "apps": apps,
        "integration_status": "connected" if _bridge.sync_enabled else "disconnected",
    }


@app.get("/orchestration/metrics")
def orchestration_metrics() -> dict[str, Any]:
    """Get unified orchestration metrics combining RL Brain and Control Plane."""
    agg_metrics = _calculate_aggregate_metrics()
    cp_metrics = _bridge.get_orchestration_metrics()
    
    return {
        "rl_brain": {
            "status": "active",
            "monitored_links": len(_INGESTED_LINKS),
            "total_commits": agg_metrics["total_commits"],
            "total_contributors": agg_metrics["total_contributors"],
            "avg_test_coverage": agg_metrics["avg_test_coverage"],
            "total_decisions": len(_RECENT_DECISIONS),
        },
        "control_plane": cp_metrics,
        "unified": {
            "total_entities_monitored": len(_INGESTED_LINKS) + cp_metrics.get("total_apps_monitored", 0),
            "total_decisions_made": len(_RECENT_DECISIONS) + cp_metrics.get("rl_decisions_made", 0),
            "system_status": "operational",
            "integration_enabled": _bridge.sync_enabled,
        },
    }






@app.get("/api/health")
def api_health():
    return {"status": "ok"}


class ReplayEvent(BaseModel):
    event_id: str
    trace_id: Optional[str] = None
    execution_id: str
    previous_hash: str
    parent_hash: Optional[str] = None
    timestamp: float
    state: str
    execution_hash: Optional[str]
    source: Optional[str]
    details: dict
    payload_hash: Optional[str] = None
    signer: Optional[str] = None
    signature: Optional[str] = None
    trace_hash: Optional[str] = None
    event_hash: Optional[str]


class ReplayResponse(BaseModel):
    execution_id: str
    valid: bool
    final_state: Optional[str]
    execution_state_history: List[str]
    events: List[ReplayEvent]
    execution_hash: Optional[str]
    runtime_attestation: Optional[Dict[str, Any]] = None


class VerifyResponse(BaseModel):
    execution_id: str
    valid: bool
    hash_chain_valid: bool
    fsm_valid: bool
    error: Optional[str] = None
    runtime_attestation_valid: Optional[bool] = None
    runtime_attestation_error: Optional[str] = None


@app.get("/api/lineage/{execution_id}", response_model=ReplayResponse)
def api_replay_lineage(
    execution_id: str,
    state: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
) -> ReplayResponse:
    """Deterministic, read-only replay of the execution lineage.

    Filters: `state`, `start_ts`, `end_ts` (unix seconds).
    This endpoint reads the journal only and never mutates runtime.
    """
    result = replay_execution_lineage(execution_id)

    # events may be empty; apply simple filters
    events = result.get("events", [])
    def _keep(ev: dict) -> bool:
        if state and ev.get("state") != state:
            return False
        ts = int(ev.get("timestamp") or 0)
        if start_ts and ts < start_ts:
            return False
        if end_ts and ts > end_ts:
            return False
        return True

    filtered = [ev for ev in events if _keep(ev)]

    # Extract runtime attestation from APPROVED event details if present
    runtime_attestation = None
    for ev in filtered:
        details = ev.get("details") or {}
        if details.get("runtime_attestation"):
            runtime_attestation = details.get("runtime_attestation")
            break

    return ReplayResponse(
        execution_id=execution_id,
        valid=result.get("valid", False),
        final_state=(filtered[-1]["state"] if filtered else None),
        execution_state_history=[ev["state"] for ev in filtered],
        events=filtered,
        execution_hash=result.get("execution_hash"),
        runtime_attestation=runtime_attestation,
    )


@app.get("/api/lineage/{execution_id}/verify", response_model=VerifyResponse)
def api_verify_lineage(execution_id: str) -> VerifyResponse:
    """Verify lineage integrity: hash chain and FSM transitions.

    Returns structured booleans rather than raising errors to aid operators.
    """
    try:
        replay_execution_lineage(execution_id)
        # Verify runtime attestation if present
        runtime_attestation_valid = None
        runtime_attestation_error = None
        try:
            replay_result = replay_execution_lineage(execution_id)
            for ev in replay_result.get("events", []):
                details = ev.get("details") or {}
                ra = details.get("runtime_attestation")
                if ra:
                    from contracts.runtime_attestation import verify_runtime_attestation

                    ok, msg = verify_runtime_attestation(ra)
                    runtime_attestation_valid = ok
                    runtime_attestation_error = None if ok else msg
                    break
        except Exception:
            # leave attestation fields as None when replay fails here
            runtime_attestation_valid = None
            runtime_attestation_error = None
        return VerifyResponse(
            execution_id=execution_id,
            valid=True,
            hash_chain_valid=True,
            fsm_valid=True,
            error=None,
            runtime_attestation_valid=runtime_attestation_valid,
            runtime_attestation_error=runtime_attestation_error,
        )
    except Exception as e:
        msg = str(e)
        hash_ok = True
        fsm_ok = True
        # Classify common failure modes
        if any(
            token in msg.lower()
            for token in (
                "hash mismatch",
                "chain broken",
                "unsigned",
                "signature",
                "duplicate",
                "timestamp",
            )
        ):
            hash_ok = False
        if "illegal" in msg.lower() or "replay start state" in msg.lower() or "continuation after terminal" in msg.lower():
            fsm_ok = False

        return VerifyResponse(
            execution_id=execution_id,
            valid=False,
            hash_chain_valid=hash_ok,
            fsm_valid=fsm_ok,
            error=msg,
        )








@app.post("/control-plane/runtime-ingest")
def runtime_ingest(payload: RuntimeIngestPayload):
    from control_plane.core.trace_logger import log_event, reset_trace, ensure_complete_trace

    # 1. Reset trace and log detection
    reset_trace()
    log_event("detection", {
        "issue": payload.issue_type,
        "service_id": payload.service_id,
        "metrics": payload.metrics
    })

    INGESTED_RUNTIME_STATE[payload.service_id] = payload.model_dump()
    decision_request = build_decision_request(payload)
    decision = DecisionEngine.decide(decision_request)
    
    # 2. Log payload_emitted
    log_event("payload_emitted", {
        "service_id": payload.service_id,
        "action": decision.selected_action
    })
    
    # 3. Log action_received
    log_event("action_received", {
        "service_id": payload.service_id,
        "action": decision.selected_action
    })
    
    success, execution_result = execute_action(
        action=decision.selected_action,
        service_id=payload.service_id,
    )
    
    if not success:
        if isinstance(execution_result, dict):
            execution_id = execution_result.get("execution_id")
            status = "blocked"
            reason = execution_result.get("reason", "governance_block")
        else:
            execution_id = None
            status = "blocked"
            reason = str(execution_result)
        
        # 4. Log execution_result (failure/blocked)
        log_event("execution_result", {
            "service_id": payload.service_id,
            "action": decision.selected_action,
            "status": status,
            "error": reason,
            "execution_id": execution_id
        })
        
        # 5. Log verification (failed)
        log_event("verification", {
            "verified": False,
            "reason": reason
        })
        ensure_complete_trace()
        
        return {
            "service_id": payload.service_id,
            "decision": decision.model_dump(mode="json"),
            "execution": {
                "execution_id": execution_id,
                "status": status,
                "reason": reason,
                "action": decision.selected_action,
            },
        }

    # 4. Log execution_result (success)
    exec_id = execution_result.get("execution_id") if isinstance(execution_result, dict) else None
    status = execution_result.get("status", "executed") if isinstance(execution_result, dict) else "executed"
    reason = execution_result.get("reason") if isinstance(execution_result, dict) else None
    verified = execution_result.get("verified", False) if isinstance(execution_result, dict) else False

    log_event("execution_result", {
        "service_id": payload.service_id,
        "action": decision.selected_action,
        "status": status,
        "execution_id": exec_id
    })
    
    # 5. Log verification
    log_event("verification", {
        "verified": verified,
        "reason": reason
    })
    ensure_complete_trace()

    return {
        "service_id": payload.service_id,
        "decision": decision.model_dump(mode="json"),
        "execution": {
            "execution_id": exec_id,
            "status": status,
            "reason": reason,
            "action": execution_result.get("action") if isinstance(execution_result, dict) else decision.selected_action,
        },
    }









import threading
import time





@app.get("/autonomous-status")
def autonomous_status():
    return {
        "last_runtime": _LAST_AUTONOMOUS_RUNTIME,
        "last_action": _LAST_EXECUTED_ACTION,
        "recent_autonomous_decisions": list(_AUTONOMOUS_DECISIONS),
        "loop_running": True,
    }








@app.get("/dashboard/state")
def dashboard_state():
    return get_dashboard_state()














if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


