#!/bin/bash
set -e

# Install dependencies
apt-get update && apt-get install -y caddy python3-pip >/dev/null 2>&1
pip3 install gpustat flask >/dev/null 2>&1

# GPU Dashboard
cat >/root/gpu-dashboard.py <<'EOF'
from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <html><head>
    <meta http-equiv="refresh" content="1">
    <style>body{font-family:monospace;background:#1a1a1a;color:#0f0;padding:20px} h1{color:#0f0} table{border-collapse:collapse;width:100%} th,td{border:1px solid #444;padding:8px;text-align:left} th{background:#333}</style>
    </head><body>
    <h1>GPU Stats</h1>
    <iframe src="/api" width="100%" height="400"></iframe>
    </body></html>
    '''

@app.route('/api')
def api():
    result = subprocess.run(['nvidia-smi','--query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,clocks.sm',
                           '--format=csv,noheader,nounits'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    html = '<table><tr><th>GPU</th><th>Name</th><th>Temp</th><th>GPU %</th><th>Mem %</th><th>VRAM</th><th>Total</th><th>Power</th><th>Clock</th></tr>'
    for line in lines:
        vals = line.split(',')
        html += f'<tr><td>{vals[0]}</td><td>{vals[1]}</td><td>{vals[2]}°C</td><td>{vals[3]}%</td><td>{vals[4]}%</td><td>{vals[5]}MB</td><td>{vals[6]}MB</td><td>{vals[7]}W</td><td>{vals[8]}MHz</td></tr>'
    html += '</table>'
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9001)
EOF

chmod +x /root/gpu-dashboard.py

# Setup Caddy for request/response logging
cat >/etc/caddy/Caddyfile <<'EOF'
:18000 {
    log {
        output file /root/access.log
        format json
    }
    reverse_proxy localhost:18000
}
EOF

caddy run --config /etc/caddy/Caddyfile --adapter caddyfile &
python3 /root/gpu-dashboard.py &

# Log Viewer
mkdir -p /root/log-viewer
cat >/root/log-viewer/index.html <<'EOF'
<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<title>Log Viewer</title>
<meta http-equiv="refresh" content="2">
<style>body{font-family:monospace;background:#1a1a1a;color:#e0e0e0;padding:10px} .log-entry{margin-bottom:8px;padding:4px} .timestamp{color:#facc15;font-size:12px} pre{margin:0;white-space:pre-wrap;word-wrap:break-word}</style>
</head><body>
<h2 style="color:#0f0">Server Logs</h2>
<pre id="logs"></pre>
<script>fetch("/logs").then(r=>r.text()).then(d=>document.getElementById("logs").innerHTML=d);</script>
</body></html>
EOF

python3 -m http.server 9000 -d /root/log-viewer &

# Log fetcher
while true; do
    {
        echo "=== ACCESS LOG ==="
        tail -n 50 /root/access.log 2>/dev/null
        echo ""
        echo "=== LLAMA SERVER LOG ==="
        tail -n 50 /root/llama-server.log 2>/dev/null
    } > /root/log-viewer/logs.txt
    sleep 1
done &

echo "Monitoring ready: Logs on port 9000, GPU Stats on port 9001"

# Run original entrypoint
exec entrypoint.sh