#!/usr/bin/env python3
"""
Llama.cpp Request/Response Monitor with Proxy
Captures full request and response bodies for debugging
"""
import http.server
import http.client
import json
import threading
import time
from datetime import datetime
from collections import deque

LLAMA_HOST = '127.0.0.1'
LLAMA_PORT = 18000
PROXY_PORT = 18001
VIEWER_PORT = 8766
MAX_REQUESTS = 50

requests_db = deque(maxlen=MAX_REQUESTS)
requests_lock = threading.Lock()

def truncate_json(json_str, max_len=50000):
    if len(json_str) <= max_len:
        return json_str
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            summary = {"_truncated": f"... ({len(json_str)} bytes, showing summary)"}
            if 'id' in data: summary['id'] = data['id']
            if 'model' in data: summary['model'] = data['model']
            if 'choices' in data:
                summary['choices_count'] = len(data['choices'])
                if data['choices']:
                    choice = data['choices'][0]
                    if 'message' in choice:
                        msg = choice['message']
                        content = msg.get('content', '')
                        reasoning = msg.get('reasoning_content', '')
                        summary['message'] = {
                            'role': msg.get('role'),
                            'content_preview': content[:1000] + '...' if len(content) > 1000 else content,
                            'reasoning_preview': reasoning[:1000] + '...' if len(reasoning) > 1000 else reasoning
                        }
                    if 'finish_reason' in choice:
                        summary['finish_reason'] = choice['finish_reason']
            if 'usage' in data: summary['usage'] = data['usage']
            if 'error' in data: summary['error'] = data['error']
            return json.dumps(summary, indent=2, ensure_ascii=False)
    except:
        pass
    return json_str[:max_len] + f"\n... (truncated, {len(json_str)} total bytes)"

def store_request(req_id, method, path, headers, body, response_status, response_headers, response_body, duration):
    with requests_lock:
        requests_db.appendleft({
            'id': req_id,
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'headers': dict(headers) if headers else {},
            'body': truncate_json(body) if body else '',
            'response_status': response_status,
            'response_headers': dict(response_headers) if response_headers else {},
            'response_body': truncate_json(response_body) if response_body else '',
            'duration_ms': duration
        })

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_PROXY(self):
        start_time = time.time()
        req_id = f"{int(time.time() * 1000)}"
        
        content_length = int(self.headers.get('Content-Length', 0))
        req_body = self.rfile.read(content_length) if content_length > 0 else b''
        
        try:
            req_json = json.loads(req_body.decode('utf-8'))
            req_body_display = json.dumps(req_json, indent=2, ensure_ascii=False)
        except:
            req_body_display = req_body.decode('utf-8', errors='replace') if req_body else ''
        
        try:
            conn = http.client.HTTPConnection(LLAMA_HOST, LLAMA_PORT, timeout=300)
            headers = {k: v for k, v in self.headers.items() if k.lower() != 'content-length'}
            
            conn.request(self.command, self.path, body=req_body, headers=headers)
            response = conn.getresponse()
            
            resp_body = response.read()
            resp_status = response.status
            resp_headers = response.getheaders()
            
            try:
                resp_json = json.loads(resp_body.decode('utf-8'))
                resp_body_display = json.dumps(resp_json, indent=2, ensure_ascii=False)
            except:
                resp_body_display = resp_body.decode('utf-8', errors='replace') if resp_body else ''
            
            self.send_response(resp_status)
            for header, value in resp_headers:
                if header.lower() not in ['content-length', 'transfer-encoding']:
                    self.send_header(header, value)
            self.send_header('Content-Length', str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
            
            duration = (time.time() - start_time) * 1000
            store_request(req_id, self.command, self.path, dict(self.headers), 
                         req_body_display, resp_status, dict(resp_headers), 
                         resp_body_display, duration)
            
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            error_msg = f"Proxy error: {str(e)}"
            self.wfile.write(error_msg.encode())
            store_request(req_id, self.command, self.path, dict(self.headers), 
                         req_body_display, 502, {}, error_msg, 0)
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self): self.do_PROXY()
    def do_POST(self): self.do_PROXY()
    def do_PUT(self): self.do_PROXY()
    def do_DELETE(self): self.do_PROXY()
    def do_PATCH(self): self.do_PROXY()

class ViewerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/api/requests':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with requests_lock:
                self.wfile.write(json.dumps(list(requests_db), ensure_ascii=False).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Llama.cpp Request Inspector</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117; 
            color: #c9d1d9;
            font-size: 13px;
        }
        #header {
            background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
            padding: 16px 20px;
            border-bottom: 1px solid #30363d;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        h1 { color: #f0883e; font-size: 18px; margin-bottom: 8px; }
        .subtitle { color: #8b949e; font-size: 12px; }
        #stats { display: flex; gap: 20px; margin-top: 10px; font-size: 12px; }
        .stat { display: flex; align-items: center; gap: 6px; }
        .stat-value { font-weight: 600; color: #58a6ff; }
        .good { color: #3fb950; }
        .bad { color: #f85149; }
        
        #filters {
            background: #161b22;
            padding: 10px 20px;
            border-bottom: 1px solid #30363d;
            display: flex;
            gap: 10px;
        }
        .filter-btn {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .filter-btn:hover { background: #30363d; }
        .filter-btn.active { background: #238636; border-color: #238636; color: white; }
        .clear-btn { background: #da3633; border-color: #da3633; color: white; margin-left: auto; }
        .clear-btn:hover { background: #f85149; }
        
        #requests { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
        
        .request-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
        }
        .request-card:hover { border-color: #58a6ff; }
        .request-card.error { border-left: 3px solid #f85149; }
        .request-card.success { border-left: 3px solid #238636; }
        
        .card-header {
            padding: 12px 16px;
            display: grid;
            grid-template-columns: auto 1fr auto auto auto;
            align-items: center;
            gap: 12px;
            cursor: pointer;
        }
        .card-header:hover { background: #1c2128; }
        .expand-icon { color: #8b949e; font-size: 10px; transition: transform 0.2s; }
        .request-card.collapsed .expand-icon { transform: rotate(-90deg); }
        
        .method { font-weight: 700; padding: 4px 10px; border-radius: 4px; font-size: 11px; }
        .method.POST { background: #238636; color: white; }
        .method.GET { background: #1f6feb; color: white; }
        
        .endpoint { color: #79c0ff; font-family: 'SF Mono', Monaco, monospace; font-size: 13px; }
        
        .status-badge { padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .status-200 { background: #23863633; color: #3fb950; }
        .status-error { background: #da363333; color: #f85149; }
        
        .duration { color: #8b949e; font-size: 12px; font-family: 'SF Mono', Monaco, monospace; }
        
        .card-body { border-top: 1px solid #30363d; background: #0d1117; }
        .request-card.collapsed .card-body { display: none; }
        
        .tabs { display: flex; background: #161b22; border-bottom: 1px solid #30363d; }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            color: #8b949e;
            font-size: 12px;
            border-bottom: 2px solid transparent;
        }
        .tab:hover { color: #c9d1d9; background: #1c2128; }
        .tab.active { color: #58a6ff; border-bottom-color: #58a6ff; background: #0d1117; }
        
        .tab-content { display: none; padding: 16px; }
        .tab-content.active { display: block; }
        
        .json-viewer {
            background: #161b22;
            border-radius: 6px;
            padding: 12px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 12px;
            line-height: 1.6;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .json-key { color: #79c0ff; }
        .json-string { color: #a5d6ff; }
        .json-number { color: #f2cc60; }
        .json-boolean { color: #ff7b72; }
        
        .empty-state { text-align: center; padding: 60px 20px; color: #8b949e; }
        .empty-state h2 { color: #c9d1d9; margin-bottom: 8px; }
        
        .reasoning-block {
            background: #1c1c2e;
            border-left: 3px solid #a371f7;
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
        }
        .reasoning-header { color: #a371f7; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
        
        .content-block {
            background: #161b22;
            border-left: 3px solid #3fb950;
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
        }
        .content-header { color: #3fb950; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
        
        .finish-reason { 
            background: #21262d; 
            padding: 8px 12px; 
            border-radius: 4px; 
            margin-bottom: 12px;
            font-size: 12px;
        }
        .finish-reason.stop { color: #3fb950; }
        .finish-reason.length { color: #f85149; }
        .finish-reason.tool_use { color: #58a6ff; }
    </style>
</head>
<body>
    <div id="header">
        <h1>🔍 Llama.cpp Request Inspector</h1>
        <div class="subtitle">Proxy on port 18001 | Real-time request/response capture</div>
        <div id="stats">
            <div class="stat"><span>●</span><span id="connection" class="good">Connected</span></div>
            <div class="stat"><span>Requests:</span><span id="reqCount" class="stat-value">0</span></div>
            <div class="stat"><span>Last:</span><span id="lastUpdate">-</span></div>
        </div>
    </div>
    
    <div id="filters">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="success">✓ Success</button>
        <button class="filter-btn" data-filter="error">✗ Errors</button>
        <button class="filter-btn" data-filter="chat">Chat</button>
        <button class="filter-btn clear-btn" onclick="clearRequests()">Clear</button>
    </div>
    
    <div id="requests"></div>
    
    <script>
        let allRequests = [];
        let currentFilter = 'all';
        
        document.querySelectorAll('.filter-btn:not(.clear-btn)').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderRequests();
            });
        });
        
        function clearRequests() {
            allRequests = [];
            renderRequests();
        }
        
        function escapeHtml(text) {
            return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        
        function formatJson(obj, indent = 0) {
            if (obj === null || obj === undefined) return '<span class="json-boolean">null</span>';
            if (typeof obj === 'string') {
                try { obj = JSON.parse(obj); } catch { return escapeHtml(obj); }
            }
            if (typeof obj === 'number') return '<span class="json-number">' + obj + '</span>';
            if (typeof obj === 'boolean') return '<span class="json-boolean">' + obj + '</span>';
            if (typeof obj !== 'object') return escapeHtml(String(obj));
            
            const spaces = '  '.repeat(indent);
            const isArray = Array.isArray(obj);
            const entries = isArray 
                ? obj.map(v => formatJson(v, indent + 1))
                : Object.entries(obj).map(([k, v]) => 
                    '<span class="json-key">"' + escapeHtml(k) + '"</span>: ' + formatJson(v, indent + 1)
                  );
            
            const brackets = isArray ? '[]' : '{}';
            if (entries.length === 0) return brackets;
            if (JSON.stringify(obj).length < 80) return brackets[0] + entries.join(', ') + brackets[1];
            
            return brackets[0] + '\\n' + entries.map(e => spaces + '  ' + e).join(',\\n') + '\\n' + spaces + brackets[1];
        }
        
        function parseResponse(body) {
            try {
                const data = typeof body === 'string' ? JSON.parse(body) : body;
                const result = { finish_reason: null, content: null, reasoning: null, usage: null };
                
                if (data.choices && data.choices[0]) {
                    const choice = data.choices[0];
                    result.finish_reason = choice.finish_reason;
                    if (choice.message) {
                        result.content = choice.message.content;
                        result.reasoning = choice.message.reasoning_content;
                    }
                }
                if (data.usage) result.usage = data.usage;
                return result;
            } catch { return null; }
        }
        
        function renderRequests() {
            const container = document.getElementById('requests');
            let filtered = allRequests;
            
            if (currentFilter === 'success') filtered = allRequests.filter(r => r.response_status === 200);
            else if (currentFilter === 'error') filtered = allRequests.filter(r => r.response_status !== 200);
            else if (currentFilter === 'chat') filtered = allRequests.filter(r => r.path.includes('/chat') || r.path.includes('/messages'));
            
            if (filtered.length === 0) {
                container.innerHTML = '<div class="empty-state"><h2>No requests</h2><p>Make a request to localhost:8001</p></div>';
                return;
            }
            
            container.innerHTML = filtered.map((req, idx) => {
                const statusClass = req.response_status === 200 ? 'success' : 'error';
                const collapsed = idx > 2 ? 'collapsed' : '';
                const duration = req.duration_ms > 0 ? (req.duration_ms / 1000).toFixed(2) + 's' : '-';
                const parsed = parseResponse(req.response_body);
                
                let finishHtml = '';
                if (parsed && parsed.finish_reason) {
                    const fr = parsed.finish_reason;
                    const frClass = fr === 'stop' ? 'stop' : (fr === 'length' ? 'length' : 'tool_use');
                    finishHtml = '<div class="finish-reason ' + frClass + '">Finish Reason: <strong>' + fr + '</strong></div>';
                }
                
                let parsedHtml = '';
                if (parsed) {
                    if (parsed.reasoning) {
                        parsedHtml += '<div class="reasoning-block"><div class="reasoning-header">💭 Reasoning</div><div style="white-space: pre-wrap;">' + escapeHtml(parsed.reasoning) + '</div></div>';
                    }
                    if (parsed.content) {
                        parsedHtml += '<div class="content-block"><div class="content-header">📝 Response</div><div style="white-space: pre-wrap;">' + escapeHtml(parsed.content) + '</div></div>';
                    }
                    if (parsed.usage) {
                        parsedHtml += '<div style="background: #21262d; padding: 8px; border-radius: 4px; font-size: 11px; color: #8b949e;">Usage: prompt=' + (parsed.usage.prompt_tokens || 0) + ', completion=' + (parsed.usage.completion_tokens || 0) + ', total=' + (parsed.usage.total_tokens || 0) + '</div>';
                    }
                }
                
                return '<div class="request-card ' + statusClass + ' ' + collapsed + '">' +
                    '<div class="card-header" onclick="toggleCard(this)">' +
                    '<span class="expand-icon">▼</span>' +
                    '<span class="method ' + req.method + '">' + req.method + '</span>' +
                    '<span class="endpoint">' + req.path + '</span>' +
                    '<span class="status-badge status-' + (req.response_status === 200 ? '200' : 'error') + '">' + (req.response_status || '...') + '</span>' +
                    '<span class="duration">' + duration + '</span>' +
                    '</div>' +
                    '<div class="card-body">' +
                    finishHtml +
                    '<div class="tabs">' +
                    '<div class="tab active" onclick="switchTab(this, 'request')">Request</div>' +
                    '<div class="tab" onclick="switchTab(this, 'response')">Response</div>' +
                    (parsedHtml ? '<div class="tab" onclick="switchTab(this, 'parsed')">Parsed</div>' : '') +
                    '<div class="tab" onclick="switchTab(this, 'headers')">Headers</div>' +
                    '</div>' +
                    '<div class="tab-content active" data-tab="request"><div class="json-viewer">' + formatJson(req.body || '(empty)') + '</div></div>' +
                    '<div class="tab-content" data-tab="response"><div class="json-viewer">' + formatJson(req.response_body || '(empty)') + '</div></div>' +
                    (parsedHtml ? '<div class="tab-content" data-tab="parsed">' + parsedHtml + '</div>' : '') +
                    '<div class="tab-content" data-tab="headers" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">' +
                    '<div><h4 style="color: #8b949e; margin-bottom: 8px; font-size: 12px;">Request</h4><div class="json-viewer" style="max-height: 200px;">' + formatJson(req.headers) + '</div></div>' +
                    '<div><h4 style="color: #8b949e; margin-bottom: 8px; font-size: 12px;">Response</h4><div class="json-viewer" style="max-height: 200px;">' + formatJson(req.response_headers) + '</div></div>' +
                    '</div>' +
                    '</div>' +
                    '</div>';
            }).join('');
            
            document.getElementById('reqCount').textContent = allRequests.length;
        }
        
        function toggleCard(header) { header.parentElement.classList.toggle('collapsed'); }
        
        function switchTab(tabEl, tabName) {
            const card = tabEl.closest('.card-body');
            card.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            card.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tabEl.classList.add('active');
            card.querySelector('[data-tab="' + tabName + '"]').classList.add('active');
        }
        
        function fetchRequests() {
            fetch('/api/requests')
                .then(r => r.json())
                .then(data => {
                    allRequests = data;
                    renderRequests();
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                    document.getElementById('connection').className = 'good';
                    document.getElementById('connection').textContent = 'Connected';
                })
                .catch(e => {
                    document.getElementById('connection').className = 'bad';
                    document.getElementById('connection').textContent = 'Disconnected';
                });
        }
        
        setInterval(fetchRequests, 500);
        fetchRequests();
    </script>
</body>
</html>'''

def run_proxy():
    server = http.server.HTTPServer(('0.0.0.0', PROXY_PORT), ProxyHandler)
    print(f'Proxy server running on port {PROXY_PORT}')
    server.serve_forever()

def run_viewer():
    server = http.server.HTTPServer(('0.0.0.0', VIEWER_PORT), ViewerHandler)
    print(f'Viewer server running on port {VIEWER_PORT}')
    server.serve_forever()

if __name__ == '__main__':
    print(f'Starting Llama.cpp Request Inspector...')
    print(f'  Proxy:  http://localhost:{PROXY_PORT} -> {LLAMA_HOST}:{LLAMA_PORT}')
    print(f'  Viewer: http://localhost:{VIEWER_PORT}')
    
    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()
    
    run_viewer()
