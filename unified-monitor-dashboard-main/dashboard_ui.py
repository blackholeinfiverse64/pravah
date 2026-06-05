"""Monitoring dashboard - displays live infrastructure state."""

from flask import Flask, render_template_string, jsonify, request
import os
from unified_system import UnifiedInfrastructureSystem

app = Flask(__name__)
system = UnifiedInfrastructureSystem()
system.start()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Unified Infrastructure Monitoring Dashboard</title>
    <style>
        :root {
            --bg: #0b1020;
            --panel: #131a2d;
            --panel-soft: #1b2440;
            --text: #e7ecff;
            --muted: #9cabd2;
            --ok: #2ecc71;
            --warn: #f39c12;
            --error: #ff5f7a;
            --accent: #4da3ff;
            --border: #2c3657;
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            padding: 24px;
            font-family: "Segoe UI", Arial, sans-serif;
            background: radial-gradient(circle at top right, #1b2750 0%, var(--bg) 50%);
            color: var(--text);
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            display: grid;
            gap: 16px;
        }
        .panel {
            background: linear-gradient(180deg, var(--panel-soft), var(--panel));
            border: 1px solid var(--border);
            border-radius: 14px;
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.25);
        }
        .header {
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
        }
        .title h1 { margin: 0 0 6px; font-size: 24px; }
        .title p { margin: 0; color: var(--muted); }
        .controls { display: flex; gap: 10px; align-items: center; }
        .btn {
            border: 1px solid var(--border);
            background: #213056;
            color: var(--text);
            border-radius: 8px;
            padding: 8px 14px;
            cursor: pointer;
            font-weight: 600;
        }
        .btn:hover { filter: brightness(1.15); }
        .chip {
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .chip.ok { color: #b8ffd6; background: rgba(46, 204, 113, 0.2); border-color: rgba(46, 204, 113, 0.35); }
        .chip.error { color: #ffd1da; background: rgba(255, 95, 122, 0.2); border-color: rgba(255, 95, 122, 0.35); }
        .chip.warn { color: #ffe0aa; background: rgba(243, 156, 18, 0.2); border-color: rgba(243, 156, 18, 0.35); }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            padding: 0 20px 20px;
        }
        .kpi {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
        }
        .kpi .label { color: var(--muted); font-size: 12px; }
        .kpi .value { font-size: 24px; font-weight: 800; margin-top: 6px; }

        .apps-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
            gap: 14px;
            padding: 0 20px 20px;
        }
        .app-card {
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            background: rgba(255, 255, 255, 0.02);
        }
        .app-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .app-name { font-weight: 700; }
        .metric {
            margin: 9px 0;
        }
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            color: var(--muted);
            font-size: 13px;
        }
        .bar {
            height: 9px;
            border-radius: 999px;
            background: #1f2a4b;
            overflow: hidden;
            border: 1px solid #2a3761;
        }
        .bar > div { height: 100%; }
        .bar .cpu { background: linear-gradient(90deg, #4da3ff, #1dd1a1); }
        .bar .mem { background: linear-gradient(90deg, #8e7dff, #5f9dff); }
        .bar .err { background: linear-gradient(90deg, #f1c40f, #e74c3c); }

        .meta {
            margin-top: 10px;
            font-size: 12px;
            color: var(--muted);
            line-height: 1.5;
            border-top: 1px dashed var(--border);
            padding-top: 10px;
        }

        .history {
            margin: 0 20px 20px;
            padding: 14px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        thead th {
            color: var(--muted);
            font-weight: 600;
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid var(--border);
        }
        tbody td {
            padding: 10px;
            border-bottom: 1px solid rgba(44, 54, 87, 0.6);
        }
        .mono { font-family: Consolas, "Courier New", monospace; }
        .footer {
            color: var(--muted);
            font-size: 12px;
            text-align: right;
            padding: 0 20px 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <section class="panel">
            <div class="header">
                <div class="title">
                    <h1>Unified Infrastructure Monitoring</h1>
                    <p>Runtime Telemetry -> Decision Brain -> Action Enforcement -> Orchestrator -> Visibility</p>
                </div>
                <div class="controls">
                    <span id="systemChip" class="chip warn">LOADING</span>
                    <button class="btn" id="toggleRefresh">Auto-Refresh: ON</button>
                    <button class="btn" id="refreshNow">Refresh Now</button>
                </div>
            </div>
            <div id="kpis" class="kpi-grid"></div>
            <div id="apps" class="apps-grid"></div>
        </section>

        <section class="panel history">
            <h3 style="margin: 0 0 12px;">Recent Decision Timeline</h3>
            <div id="historyTable"></div>
        </section>

        <div id="lastUpdated" class="footer">Last updated: --</div>
    </div>

    <script>
        let autoRefresh = true;
        let refreshTimer = null;
        const REFRESH_MS = 10000;

        function pct(v) { return (v * 100).toFixed(1) + "%"; }
        function healthChip(status) {
            if (status === "success") return '<span class="chip ok">SUCCESS</span>';
            if (status === "failed") return '<span class="chip error">FAILED</span>';
            return '<span class="chip warn">PENDING</span>';
        }

        function buildKpis(data) {
            const apps = Object.values(data.apps || {}).filter(a => !a.error);
            const avgCpu = apps.length ? apps.reduce((s, a) => s + a.metrics.cpu, 0) / apps.length : 0;
            const avgMem = apps.length ? apps.reduce((s, a) => s + a.metrics.memory, 0) / apps.length : 0;
            const failed = apps.filter(a => a.last_decision_status === "failed").length;

            return `
                <div class="kpi"><div class="label">System State</div><div class="value">${data.running ? "RUNNING" : "STOPPED"}</div></div>
                <div class="kpi"><div class="label">Active Applications</div><div class="value">${(data.active_applications || []).length}</div></div>
                <div class="kpi"><div class="label">Total Decisions</div><div class="value">${data.total_decisions}</div></div>
                <div class="kpi"><div class="label">Average CPU / Memory</div><div class="value">${pct(avgCpu)} / ${pct(avgMem)}</div></div>
                <div class="kpi"><div class="label">Failed Last Decisions</div><div class="value">${failed}</div></div>
                <div class="kpi"><div class="label">Uptime (s)</div><div class="value">${Math.floor(data.uptime_seconds || 0)}</div></div>
            `;
        }

        function buildApps(data) {
            const apps = Object.entries(data.apps || {});
            if (!apps.length) return "<div>No application data available.</div>";

            return apps.map(([appId, appData]) => {
                if (appData.error) {
                    return `<article class="app-card"><div class="app-head"><span class="app-name">${appId}</span><span class="chip error">ERROR</span></div><div>${appData.error}</div></article>`;
                }

                const m = appData.metrics;
                const latency = Number(m.latency_ms || 0).toFixed(0) + "ms";
                return `
                    <article class="app-card">
                        <div class="app-head">
                            <span class="app-name">${appId}</span>
                            ${healthChip(appData.last_decision_status)}
                        </div>

                        <div class="metric">
                            <div class="metric-row"><span>CPU</span><span>${pct(m.cpu)}</span></div>
                            <div class="bar"><div class="cpu" style="width:${Math.min(100, m.cpu * 100)}%"></div></div>
                        </div>
                        <div class="metric">
                            <div class="metric-row"><span>Memory</span><span>${pct(m.memory)}</span></div>
                            <div class="bar"><div class="mem" style="width:${Math.min(100, m.memory * 100)}%"></div></div>
                        </div>
                        <div class="metric">
                            <div class="metric-row"><span>Error Rate</span><span>${pct(m.error_rate)}</span></div>
                            <div class="bar"><div class="err" style="width:${Math.min(100, m.error_rate * 100)}%"></div></div>
                        </div>

                        <div class="meta">
                            Latency: <span class="mono">${latency}</span><br/>
                            Replicas: <span class="mono">${m.replicas}</span><br/>
                            Last Action: <span class="mono">${appData.last_action}</span> (${appData.last_action_success ? "Success" : "Failed"})<br/>
                            Current Decision: <span class="mono">${appData.current_decision}</span><br/>
                            Recent Decisions: <span class="mono">${appData.recent_decisions}</span>
                        </div>
                    </article>
                `;
            }).join("");
        }

        function buildHistory(data) {
            const rows = [];
            for (const [appId, appData] of Object.entries(data.apps || {})) {
                for (const d of (appData.decision_history || [])) {
                    rows.push({
                        ts: d.timestamp || 0,
                        appId: appId,
                        decisionId: d.decision_id,
                        req: d.action_requested,
                        emit: d.action_emitted,
                        ack: d.orchestrator_acknowledged
                    });
                }
            }

            rows.sort((a, b) => b.ts - a.ts);
            const sliced = rows.slice(0, 20);
            if (!sliced.length) return "<div>No decision history available.</div>";

            const body = sliced.map(r => `
                <tr>
                    <td>${new Date(r.ts * 1000).toLocaleTimeString()}</td>
                    <td>${r.appId}</td>
                    <td class="mono">${r.decisionId}</td>
                    <td class="mono">${r.req}</td>
                    <td class="mono">${r.emit}</td>
                    <td>${r.ack === true ? '<span class="chip ok">ACK</span>' : r.ack === false ? '<span class="chip error">NACK</span>' : '<span class="chip warn">N/A</span>'}</td>
                </tr>
            `).join("");

            return `
                <table>
                    <thead>
                        <tr>
                            <th>Time</th><th>App</th><th>Decision ID</th><th>Requested</th><th>Emitted</th><th>Orchestrator Ack</th>
                        </tr>
                    </thead>
                    <tbody>${body}</tbody>
                </table>
            `;
        }

        async function loadDashboard() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();

                document.getElementById("kpis").innerHTML = buildKpis(data);
                document.getElementById("apps").innerHTML = buildApps(data);
                document.getElementById("historyTable").innerHTML = buildHistory(data);
                document.getElementById("lastUpdated").innerText = "Last updated: " + new Date().toLocaleString();

                const chip = document.getElementById("systemChip");
                chip.className = "chip " + (data.running ? "ok" : "error");
                chip.innerText = data.running ? "SYSTEM RUNNING" : "SYSTEM STOPPED";
            } catch (e) {
                document.getElementById("apps").innerHTML = "<div class='app-card'>Failed to load dashboard data.</div>";
                document.getElementById("systemChip").className = "chip error";
                document.getElementById("systemChip").innerText = "LOAD FAILED";
                console.error(e);
            }
        }

        function startTimer() {
            if (refreshTimer) clearInterval(refreshTimer);
            if (autoRefresh) refreshTimer = setInterval(loadDashboard, REFRESH_MS);
        }

        document.getElementById("toggleRefresh").addEventListener("click", () => {
            autoRefresh = !autoRefresh;
            document.getElementById("toggleRefresh").innerText = "Auto-Refresh: " + (autoRefresh ? "ON" : "OFF");
            startTimer();
        });
        document.getElementById("refreshNow").addEventListener("click", loadDashboard);

        loadDashboard();
        startTimer();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/status')
def get_status():
    return jsonify(system.get_system_status())

@app.route('/api/decisions')
def get_decisions():
    return jsonify({
        'decisions': system.decision_history[-50:],
        'total': len(system.decision_history)
    })


@app.route('/api/apps/register', methods=['POST'])
def register_app():
    body = request.get_json(silent=True) or {}
    app_id = body.get('app_id')
    if not app_id:
        return jsonify({'error': 'app_id is required'}), 400

    replicas = int(body.get('replicas', 1))
    initial_signals = body.get('signals') or {}
    result = system.register_application(
        app_id=app_id,
        replicas=replicas,
        initial_signals=initial_signals,
    )
    return jsonify(result)


@app.route('/api/telemetry/ingest', methods=['POST'])
def ingest_telemetry():
    body = request.get_json(silent=True) or {}
    app_id = body.get('app_id')
    signals = body.get('signals')
    if not app_id or not isinstance(signals, dict):
        return jsonify({'error': 'app_id and signals object are required'}), 400

    result = system.ingest_telemetry(app_id=app_id, signals=signals)
    return jsonify(result)

if __name__ == '__main__':
    host = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    port = int(os.getenv("DASHBOARD_PORT", "5000"))
    app.run(debug=False, host=host, port=port)
