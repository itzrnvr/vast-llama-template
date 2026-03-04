#!/usr/bin/env python3
import http.server
import subprocess
import json
import re
from datetime import datetime

LOG_FILE = '/var/log/portal/llama.log'
PORT = 8766
MAX_LINES = 500

HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Llama.cpp Logs - Real-time</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; 
            background: #0d1117; 
            color: #c9d1d9;
            margin: 0;
            padding: 0;
            font-size: 13px;
        }
        #header {
            background: #161b22;
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        h1 { 
            color: #f0883e; 
            font-size: 14px;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        #stats {
            font-size: 11px;
            color: #8b949e;
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }
        #stats span { display: flex; align-items: center; gap: 4px; }
        .good { color: #3fb950; }
        .warn { color: #d29922; }
        .bad { color: #f85149; }
        
        #filters {
            background: #161b22;
            padding: 8px 16px;
            border-bottom: 1px solid #30363d;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .filter-btn {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        .filter-btn:hover { background: #30363d; }
        .filter-btn.active { background: #238636; border-color: #238636; }
        
        #logs {
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .request-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            overflow: hidden;
        }
        .request-card.error { border-color: #f85149; }
        .request-card.success { border-color: #238636; }
        
        .card-header {
            padding: 10px 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            user-select: none;
        }
        .card-header:hover { background: #21262d; }
        
        .method {
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            min-width: 50px;
            text-align: center;
        }
        .method.POST { background: #238636; color: white; }
        .method.GET { background: #1f6feb; color: white; }
        
        .endpoint {
            color: #79c0ff;
            font-family: 'Monaco', monospace;
            font-size: 12px;
            flex: 1;
        }
        
        .status {
            font-weight: 600;
            font-size: 12px;
        }
        .status.s200 { color: #3fb950; }
        .status.s400, .status.s500 { color: #f85149; }
        .status.sactive { color: #d29922; }
        
        .timing {
            color: #8b949e;
            font-size: 11px;
        }
        
        .expand-icon {
            color: #8b949e;
            transition: transform 0.2s;
        }
        .request-card.collapsed .expand-icon { transform: rotate(-90deg); }
        
        .card-body {
            border-top: 1px solid #30363d;
            padding: 12px;
            background: #0d1117;
        }
        .request-card.collapsed .card-body { display: none; }
        
        .section {
            margin-bottom: 12px;
        }
        .section:last-child { margin-bottom: 0; }
        
        .section-title {
            color: #8b949e;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 8px;
        }
        
        .metric {
            background: #161b22;
            padding: 8px 10px;
            border-radius: 4px;
        }
        .metric-label {
            color: #8b949e;
            font-size: 10px;
            text-transform: uppercase;
        }
        .metric-value {
            color: #58a6ff;
            font-size: 14px;
            font-weight: 600;
            font-family: 'Monaco', monospace;
        }
        .metric-value.good { color: #3fb950; }
        .metric-value.warn { color: #d29922; }
        
        .log-lines {
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 11px;
            line-height: 1.5;
            background: #161b22;
            border-radius: 4px;
            padding: 8px;
            max-height: 300px;
            overflow-y: auto;
        }
        .log-line {
            padding: 2px 0;
            border-bottom: 1px solid #21262d;
        }
        .log-line:last-child { border-bottom: none; }
        
        .raw-log {
            color: #8b949e;
        }
        .time { color: #6e7681; }
        .level-error { color: #f85149; }
        .level-warn { color: #d29922; }
        .level-info { color: #58a6ff; }
        .level-success { color: #3fb950; }
        
        .token-count { color: #a371f7; }
        .speed { color: #3fb950; }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8b949e;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>🔥 Llama.cpp Request Monitor</h1>
        <div id="stats">
            <span>Status: <span id="status" class="good">● Connected</span></span>
            <span>Requests: <span id="reqCount">0</span></span>
            <span>Last Update: <span id="lastUpdate">-</span></span>
        </div>
    </div>
    <div id="filters">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="success">Success (200)</button>
        <button class="filter-btn" data-filter="error">Errors</button>
        <button class="filter-btn" data-filter="active">Active</button>
    </div>
    <div id="logs"></div>
    
    <script>
        let currentFilter = 'all';
        let allRequests = [];
        
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderRequests();
            });
        });
        
        function parseLogs(lines) {
            const requests = [];
            let currentReq = null;
            
            for (const line of lines) {
                const reqMatch = line.match(/log_server_r: processing request: (\\w+) (\\S+)/);
                if (reqMatch) {
                    if (currentReq) requests.push(currentReq);
                    currentReq = {
                        method: reqMatch[1],
                        endpoint: reqMatch[2],
                        status: null,
                        lines: [line],
                        startTime: Date.now(),
                        endTime: null,
                        tokens: { prompt: 0, generated: 0 },
                        speed: { prompt: 0, generation: 0 },
                        timing: { prompt: 0, eval: 0, total: 0 }
                    };
                    continue;
                }
                
                const doneMatch = line.match(/log_server_r: done request: (\\w+) (\\S+) \\S+ (\\d+)/);
                if (doneMatch && currentReq) {
                    currentReq.status = parseInt(doneMatch[3]);
                    currentReq.endTime = Date.now();
                    currentReq.lines.push(line);
                    requests.push(currentReq);
                    currentReq = null;
                    continue;
                }
                
                if (currentReq) {
                    currentReq.lines.push(line);
                    
                    const promptTokMatch = line.match(/prompt processing done.*n_tokens = (\\d+)/);
                    if (promptTokMatch) currentReq.tokens.prompt = parseInt(promptTokMatch[1]);
                    
                    const timingMatch = line.match(/prompt eval time =\\s+(\\d+\\.?\\d*) ms \\/\\s+(\\d+) tokens.*?(\\d+\\.?\\d*) tokens per second/);
                    if (timingMatch) {
                        currentReq.timing.prompt = parseFloat(timingMatch[1]);
                        currentReq.tokens.prompt = parseInt(timingMatch[2]);
                        currentReq.speed.prompt = parseFloat(timingMatch[3]);
                    }
                    
                    const evalMatch = line.match(/eval time =\\s+(\\d+\\.?\\d*) ms \\/\\s+(\\d+) tokens.*?(\\d+\\.?\\d*) tokens per second/);
                    if (evalMatch) {
                        currentReq.timing.eval = parseFloat(evalMatch[1]);
                        currentReq.tokens.generated = parseInt(evalMatch[2]);
                        currentReq.speed.generation = parseFloat(evalMatch[3]);
                    }
                    
                    const totalMatch = line.match(/total time =\\s+(\\d+\\.?\\d*) ms/);
                    if (totalMatch) {
                        currentReq.timing.total = parseFloat(totalMatch[1]);
                    }
                }
            }
            
            if (currentReq) requests.push(currentReq);
            return requests.reverse();
        }
        
        function renderRequests() {
            const logsDiv = document.getElementById('logs');
            let filtered = allRequests;
            
            if (currentFilter === 'success') {
                filtered = allRequests.filter(r => r.status === 200);
            } else if (currentFilter === 'error') {
                filtered = allRequests.filter(r => r.status && r.status !== 200);
            } else if (currentFilter === 'active') {
                filtered = allRequests.filter(r => !r.status);
            }
            
            if (filtered.length === 0) {
                logsDiv.innerHTML = '<div class="empty-state">No requests match the current filter</div>';
                return;
            }
            
            logsDiv.innerHTML = filtered.map((req, idx) => {
                const statusClass = req.status === 200 ? 'success' : (req.status ? 'error' : '');
                const collapsed = idx > 3 ? 'collapsed' : '';
                const duration = req.endTime ? ((req.endTime - req.startTime) / 1000).toFixed(1) + 's' : 'Active...';
                
                return `
                    <div class="request-card ${statusClass} ${collapsed}" data-idx="${idx}">
                        <div class="card-header" onclick="toggleCard(this)">
                            <span class="expand-icon">▼</span>
                            <span class="method ${req.method}">${req.method}</span>
                            <span class="endpoint">${req.endpoint}</span>
                            <span class="status s${req.status || 'active'}">${req.status || '●'}</span>
                            <span class="timing">${duration}</span>
                        </div>
                        <div class="card-body">
                            <div class="section">
                                <div class="section-title">Metrics</div>
                                <div class="metrics-grid">
                                    <div class="metric">
                                        <div class="metric-label">Prompt Tokens</div>
                                        <div class="metric-value">${req.tokens.prompt.toLocaleString()}</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Generated Tokens</div>
                                        <div class="metric-value">${req.tokens.generated.toLocaleString()}</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Prompt Speed</div>
                                        <div class="metric-value ${req.speed.prompt > 1000 ? 'good' : ''}">${req.speed.prompt.toFixed(0)} tok/s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Gen Speed</div>
                                        <div class="metric-value ${req.speed.generation > 50 ? 'good' : 'warn'}">${req.speed.generation.toFixed(1)} tok/s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Prompt Time</div>
                                        <div class="metric-value">${(req.timing.prompt / 1000).toFixed(2)}s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Gen Time</div>
                                        <div class="metric-value">${(req.timing.eval / 1000).toFixed(2)}s</div>
                                    </div>
                                    <div class="metric">
                                        <div class="metric-label">Total Time</div>
                                        <div class="metric-value">${(req.timing.total / 1000).toFixed(2)}s</div>
                                    </div>
                                </div>
                            </div>
                            <div class="section">
                                <div class="section-title">Log Lines (${req.lines.length})</div>
                                <div class="log-lines">
                                    ${req.lines.map(l => formatLine(l)).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('reqCount').textContent = allRequests.length;
        }
        
        function formatLine(line) {
            let html = line
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            let cls = 'log-line';
            if (html.includes('error') || html.includes('ERROR') || html.includes('fail')) {
                cls += ' level-error';
            } else if (html.includes('warn')) {
                cls += ' level-warn';
            } else if (html.includes('done') || html.includes('200')) {
                cls += ' level-success';
            }
            
            html = html.replace(/(\\d+\\.?\\d* tokens per second)/g, '<span class="speed">$1</span>');
            html = html.replace(/(\\d+\\.?\\d* ms)/g, '<span class="time">$1</span>');
            html = html.replace(/(\\d+ tokens)/g, '<span class="token-count">$1</span>');
            
            return '<div class="' + cls + '">' + html + '</div>';
        }
        
        function toggleCard(header) {
            header.parentElement.classList.toggle('collapsed');
        }
        
        function fetchLogs() {
            fetch('/api/logs')
                .then(r => r.json())
                .then(data => {
                    allRequests = parseLogs(data.lines);
                    renderRequests();
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    document.getElementById('status').className = 'good';
                    document.getElementById('status').textContent = '● Connected';
                })
                .catch(e => {
                    document.getElementById('status').className = 'bad';
                    document.getElementById('status').textContent = '● Disconnected';
                });
        }
        
        setInterval(fetchLogs, 500);
        fetchLogs();
    </script>
</body>
</html>'''

class LogHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                result = subprocess.run(['tail', '-n', str(MAX_LINES), LOG_FILE], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                self.wfile.write(json.dumps({'lines': lines}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'lines': [f'Error: {e}']}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    print(f'Starting log viewer on port {PORT}')
    server = http.server.HTTPServer(('0.0.0.0', PORT), LogHandler)
    server.serve_forever()
