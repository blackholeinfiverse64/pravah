# Backend Setup & Configuration

## ✅ SINGLE BACKEND: FastAPI (backend/app/main.py)

The project uses **ONE backend**: FastAPI-based Pravah Decision Brain API.

### Running the Backend

**Development (with auto-reload):**
```bash
.venv\Scripts\python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

**Or use the entry point script:**
```bash
.venv\Scripts\python backend/run.py
```
Port: Defaults to **8000** (configurable via `BACKEND_PORT` env var)

**Production (Render):**
- Use `render.yaml` which runs: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

---

## ⚠️ DEPRECATED: Flask API (api/agent_api.py & wsgi.py)

The old Flask-based API (`api/agent_api.py` and `wsgi.py`) is **NOT USED** and should be ignored.
- **Do not run** `python wsgi.py` or import `agent_api.py` directly
- Only the FastAPI backend (`backend/app/main.py`) is the canonical backend

---

## Backend API Endpoints (FastAPI)

All endpoints served by `backend/app/main.py`:

### Health & Status
- `GET /health` - Service health and guarantees
- `GET /action-scope` - Environment-specific allowed actions
- `GET /decision-summary` - Aggregate decision metrics

### Real-time Dashboard
- `GET /` - Root (maps to live dashboard)
- `GET /live-dashboard` - Full real-time dashboard payload

### Decision Engine
- `POST /decision` - Compute a deterministic decision
- `GET /recent-activity` - Last 10 decisions

### Control Plane
- `GET /control-plane/status` - Control plane status
- `GET /control-plane/apps` - List managed apps
- `GET /orchestration/metrics` - Orchestration metrics
- `POST /decision-with-control-plane` - Integrated decision

### Link Ingestion (Project Monitoring)
- `POST /ingest-link` - Ingest a repository or website for monitoring
- `POST /remove-link` - Stop monitoring a link

### Autonomous Loop
- `GET /autonomous-status` - Autonomous decision loop status
- `POST /start-autonomous-loop` - Start autonomous decision making

---

## Frontend Integration (localhost)

### Frontend Configuration (.env.local)

```env
NEXT_PUBLIC_BACKEND_PORT=8000
NEXT_PUBLIC_DECISION_BRAIN_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CONTROL_PLANE_URL=http://localhost:8000
```

### Starting Frontend

```bash
cd frontend
npm run dev
```
Frontend runs on: **http://localhost:4500**
Backend: **http://localhost:8000** (configured in .env.local)

---

## CORS Configuration

The FastAPI backend includes:
- `allow_origins=["*"]` - Wildcard CORS for public API
- `allow_credentials=False` - Required for wildcard CORS
- Applies to all endpoints

---

## Production Deployment (Render)

**Backend:**
- Deployment specified in `render.yaml`
- Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Only endpoint: `https://multi-agents-control-plane-bck.onrender.com`

**Frontend:**
- Deployed on Vercel
- Update `.env.local` to use production URLs when needed:
  ```env
  NEXT_PUBLIC_DECISION_BRAIN_API_URL=https://multi-agents-control-plane-bck.onrender.com
  NEXT_PUBLIC_API_URL=https://multi-agents-control-plane-bck.onrender.com
  NEXT_PUBLIC_CONTROL_PLANE_URL=https://multi-agents-control-plane-bck.onrender.com
  ```

---

## Troubleshooting

### "Cannot connect to backend"
1. Verify backend is running: `http://localhost:8000/health` should return 200
2. Check frontend .env.local has correct backend URL
3. Verify port 8000 is not blocked by firewall

### "Port 8000 already in use"
```bash
# Find and kill process on port 8000
netstat -ano | findstr "8000"
taskkill /PID <PID> /F
```

### "No Access-Control-Allow-Origin header"
- Backend should be running with FastAPI's CORSMiddleware (already configured)
- Verify backend is restarted after code changes

