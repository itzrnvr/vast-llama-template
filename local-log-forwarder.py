#!/usr/bin/env python3
"""
Local log forwarder - runs on your Mac
Receives logs from remote instance via SSH tunnel and saves locally
Also provides real-time viewer with virtual scrolling
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import deque
import websockets
import http.server
import threading

# Configuration
LOCAL_LOG_DIR = Path.home() / "llama-logs"
LOCAL_LOG_FILE = LOCAL_LOG_DIR / "requests.jsonl"
WEBSOCKET_PORT = 8767
VIEWER_PORT = 8768
MAX_MEMORY_REQUESTS = 1000  # Keep last 1000 in memory for viewer

# In-memory store for viewer
requests_db = deque(maxlen=MAX_MEMORY_REQUESTS)
requests_lock = threading.Lock()

class LogForwarder:
    def __init__(self):
        self.local_file = open(LOCAL_LOG_FILE, 'a')
        self.request_count = 0
        
    def write_log(self, record):
        """Write to local file and memory"""
        # Write to file
        self.local_file.write(json.dumps(record) + '\n')
        self.local_file.flush()
        
        # Add to memory for viewer
        with requests_lock:
            requests_db.append(record)
        
        self.request_count += 1
        if self.request_count % 100 == 0:
            print(f"  📊 Total requests logged: {self.request_count}")

async def websocket_server(forwarder):
    """WebSocket server to receive logs from remote"""
    async def handler(websocket, path):
        print(f"  🔌 Remote instance connected")
        try:
            async for message in websocket:
                try:
                    record = json.loads(message)
                    forwarder.write_log(record)
                except json.JSONDecodeError:
                    print(f"  ⚠️  Invalid JSON: {message[:100]}")
        except websockets.exceptions.ConnectionClosed:
            print(f"  🔌 Remote instance disconnected")
    
    print(f"  📡 WebSocket server on port {WEBSOCKET_PORT}")
    async with websockets.serve(handler, 'localhost', WEBSOCKET_PORT):
        await asyncio.Future()  # Run forever

class LocalViewerHandler(http.server.BaseHTTPRequestHandler):
    """Local viewer for real-time logs"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(VIEWER_HTML.encode())
        elif self.path == '/api/requests':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with requests_lock:
                # Return last 100 requests for performance
                recent = list(requests_db)[:100]
                self.wfile.write(json.dumps(recent).encode())
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            stats = {
                'total_requests': len(requests_db),
                'log_file_size': os.path.getsize(LOCAL_LOG_FILE) if LOCAL_LOG_FILE.exists() else 0,
                'log_file_path': str(LOCAL_LOG_FILE)
            }
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_local_viewer():
    server = http.server.HTTPServer(('localhost', VIEWER_PORT), LocalViewerHandler)
    print(f"  🌐 Local viewer: http://localhost:{VIEWER_PORT}")
    server.serve_forever()

VIEWER_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Local Log Viewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0d1117; 
            color: #c9d1d9;
            font-size: 13px;
        }
        #header {
            background: #161b22;
            padding: 16px 20px;
            border-bottom: 1px solid #30363d;
        }
        h1 { color: #f0883e; font-size: 18px; margin-bottom: 8px; }
        #stats { display: flex; gap: 20px; font-size: 12px; color: #8b949e; }
        #log-container {
            height: calc(100vh - 100px);
            overflow-y: auto;
            padding: 10px;
        }
        .log-entry {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 8px;
            font-family: monospace;
            font-size: 12px;
        }
        .log-entry:hover { border-color: #58a6ff; }
        .timestamp { color: #6e7681; }
        .method { color: #58a6ff; font-weight: bold; }
        .path { color: #79c0ff; }
        .status-200 { color: #3fb950; }
        .status-error { color: #f85149; }
        .duration { color: #d29922; }
        pre { 
            background: #0d1117; 
            padding: 8px; 
            margin-top: 8px;
            border-radius: 4px;
            overflow-x: auto;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div id="header">
        <h1>📡 Real-time Log Viewer</h1>
        <div id="stats">
            <span>Requests: <span id="reqCount">0</span></span>
            <span>File: <span id="filePath">-</span></span>
            <span>Size: <span id="fileSize">-</span></span>
        </div>
    </div>
    <div id="log-container"></div>
    
    <script>
        let requests = [];
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function renderRequests() {
            const container = document.getElementById('log-container');
            container.innerHTML = requests.map(req => {
                const statusClass = req.response_status === 200 ? 'status-200' : 'status-error';
                return `<div class="log-entry">
                    <span class="timestamp">${req.timestamp}</span>
                    <span class="method">${req.method}</span>
                    <span class="path">${req.path}</span>
                    <span class="${statusClass}">${req.response_status}</span>
                    <span class="duration">${req.duration_ms.toFixed(0)}ms</span>
                    <pre>${JSON.stringify(req.body, null, 2).substring(0, 500)}...</pre>
                </div>`;
            }).join('');
            
            // Auto-scroll to bottom
            container.scrollTop = container.scrollHeight;
        }
        
        async function fetchData() {
            try {
                const [reqsRes, statsRes] = await Promise.all([
                    fetch('/api/requests'),
                    fetch('/api/stats')
                ]);
                
                requests = await reqsRes.json();
                const stats = await statsRes.json();
                
                document.getElementById('reqCount').textContent = stats.total_requests;
                document.getElementById('filePath').textContent = stats.log_file_path;
                document.getElementById('fileSize').textContent = formatBytes(stats.log_file_size);
                
                renderRequests();
            } catch (e) {
                console.error('Fetch error:', e);
            }
        }
        
        setInterval(fetchData, 1000);
        fetchData();
    </script>
</body>
</html>'''

def main():
    print("=" * 60)
    print("🚀 Local Log Forwarder & Viewer")
    print("=" * 60)
    print()
    
    # Setup local log directory
    LOCAL_LOG_DIR.mkdir(exist_ok=True)
    print(f"📁 Local log directory: {LOCAL_LOG_DIR}")
    print(f"📝 Log file: {LOCAL_LOG_FILE}")
    print()
    
    forwarder = LogForwarder()
    
    # Start local viewer in background thread
    viewer_thread = threading.Thread(target=run_local_viewer, daemon=True)
    viewer_thread.start()
    
    print("📋 Setup complete!")
    print()
    print("To connect from remote instance:")
    print(f"  python3 -c \"import websockets, asyncio, json; async def send(): w = await websockets.connect('ws://localhost:{WEBSOCKET_PORT}'); await w.send(json.dumps({{'test': 'data'}})); asyncio.run(send())\"")
    print()
    print("Or use the remote forwarder script on the instance")
    print()
    
    # Run WebSocket server
    asyncio.run(websocket_server(forwarder))

if __name__ == '__main__':
    main()
