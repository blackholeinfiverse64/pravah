"""Monitoring dashboard - displays live infrastructure state."""

from flask import Flask, render_template_string, jsonify
import json
from unified_system import UnifiedInfrastructureSystem

app = Flask(__name__)
system = UnifiedInfrastructureSystem()
system.start()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Infrastructure Monitoring Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .header h1 { margin: 0; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; }
        .card h2 { margin-top: 0; color: #2c3e50; }
        .metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .metric-label { font-weight: bold; color: #666; }
        .metric-value { color: #2c3e50; font-family: monospace; }
        .status-ok { color: #27ae60; }
        .status-warn { color: #f39c12; }
        .status-error { color: #e74c3c; }
        .info { background: #ecf0f1; padding: 15px; border-radius: 4px; }
        .refresh { text-align: center; padding: 20px; }
        button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Unified Infrastructure Monitoring</h1>
            <p>Real-time operational visibility and decision tracking</p>
        </div>
        <div class="refresh">
            <button onclick="location.reload()">Refresh Data</button>
        </div>
        <div id="content"></div>
    </div>
    
    <script>
        async function loadDashboard() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                displayDashboard(data);
            } catch (e) {
                console.error('Error:', e);
                document.getElementById('content').innerHTML = '<p>Error loading dashboard</p>';
            }
        }
        
        function displayDashboard(data) {
            let html = '<div class="grid">';
            
            html += '<div class="card"><h2>System Overview</h2>';
            html += '<div class="metric-row"><span class="metric-label">Status:</span>';
            html += '<span class="metric-value ' + (data.running ? 'status-ok' : 'status-error') + '">';
            html += data.running ? 'Running' : 'Stopped';
            html += '</span></div>';
            html += '<div class="metric-row"><span class="metric-label">Total Decisions:</span>';
            html += '<span class="metric-value">' + data.total_decisions + '</span></div>';
            html += '</div>';
            
            for (const [appId, appData] of Object.entries(data.apps)) {
                if (appData.error) {
                    html += '<div class="card"><h2>' + appId + '</h2>';
                    html += '<p class="status-error">Error: ' + appData.error + '</p>';
                    html += '</div>';
                    continue;
                }
                
                const m = appData.metrics;
                html += '<div class="card"><h2>' + appId + '</h2>';
                html += '<div class="metric-row"><span class="metric-label">CPU:</span><span class="metric-value">' + (m.cpu * 100).toFixed(1) + '%</span></div>';
                html += '<div class="metric-row"><span class="metric-label">Memory:</span><span class="metric-value">' + (m.memory * 100).toFixed(1) + '%</span></div>';
                html += '<div class="metric-row"><span class="metric-label">Error Rate:</span><span class="metric-value">' + (m.error_rate * 100).toFixed(1) + '%</span></div>';
                html += '<div class="metric-row"><span class="metric-label">Latency:</span><span class="metric-value">' + m.latency_ms.toFixed(0) + 'ms</span></div>';
                html += '<div class="metric-row"><span class="metric-label">Replicas:</span><span class="metric-value">' + m.replicas + '</span></div>';
                
                html += '<div class="info">';
                html += '<strong>Last Action:</strong> ' + appData.last_action + ' (' + (appData.last_action_success ? 'Success' : 'Failed') + ')<br/>';
                html += '<strong>Current Decision:</strong> ' + appData.current_decision + '<br/>';
                html += '<strong>Recent Decisions:</strong> ' + appData.recent_decisions;
                html += '</div>';
                html += '</div>';
            }
            
            html += '</div>';
            document.getElementById('content').innerHTML = html;
        }
        
        loadDashboard();
        setInterval(loadDashboard, 10000);
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

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
