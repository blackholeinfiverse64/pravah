# Pravah Dashboard Frontend (Next.js)

Next.js frontend for real-time monitoring and decision-brain interaction.

## Stack

- Next.js 15
- React 18
- TypeScript
- Tailwind CSS

## Local Run

```powershell
cd dashboard\frontend
npm install
npm run dev
```

Default dev URL:

- http://localhost:4500

## API Configuration

Set values in dashboard/frontend/.env.local:

```env
NEXT_PUBLIC_BACKEND_PORT=8000
NEXT_PUBLIC_DECISION_BRAIN_API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CONTROL_PLANE_URL=http://localhost:7000
```

Resolution behavior:
- NEXT_PUBLIC_DECISION_BRAIN_API_URL has highest priority.
- Otherwise NEXT_PUBLIC_API_URL is used.
- Otherwise localhost with NEXT_PUBLIC_BACKEND_PORT is used.

## API Client

Primary client used by pages:

- dashboard/frontend/services/api.ts

Endpoints consumed include:
- /health
- /action-scope
- /recent-activity
- /decision-summary
- /decision
- /decision-with-control-plane
- /live-dashboard
- /ingest-link
- /remove-link
- /control-plane/status
- /control-plane/apps
- /orchestration/metrics
- /autonomous-status

## Main Pages

- Home dashboard: app/page.tsx
- Decision brain tester: app/decision-brain/page.tsx

## Troubleshooting

Undefined API URL issues:

1. Verify .env.local values.
2. Restart Next.js after env changes.
3. Clear .next cache if needed:

```powershell
Remove-Item -Recurse -Force .next
npm run dev
```

Backend unreachable behavior:
- UI surfaces graceful error states while preserving current render.
