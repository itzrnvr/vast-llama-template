# Vast.ai Llama.cpp Template with Real-time Monitoring

Complete monitoring solution for interruptible Vast.ai instances with real-time log sync to your local machine.

## 🚀 Quick Start

### 1. Launch Instance
Use template `Qwen3.5-35B-heretic-v2-Q5KM` on Vast.ai or create from template ID `355728`.

### 2. Start Log Sync (on your Mac)
```bash
./start-log-sync.sh [INSTANCE_ID]
```

This will:
- Create SSH tunnels for all services
- Start real-time log sync to `~/llama-logs/requests.jsonl`
- Open local viewer at http://localhost:8768

### 3. Access Services
- **API**: http://localhost:8000 (OpenAI-compatible)
- **Request Logs**: http://localhost:9000 (full request/response inspector)
- **GPU Stats**: http://localhost:9001 (real-time GPU monitoring)
- **Local Viewer**: http://localhost:8768 (synced logs on your Mac)

## 📊 Features

### Request/Response Logging
- Every request and response captured in full
- JSONL format for easy parsing and analytics
- Web UI with filtering, search, and JSON formatting
- Shows reasoning_content for thinking models

### Real-time Sync to Local Machine
- Logs stream from remote instance to your Mac via WebSocket
- Survives instance interruptions (data saved locally)
- Use for analytics, training datasets, or debugging

### GPU Monitoring
- Real-time temperature, utilization, VRAM
- Power draw and clock speeds
- Auto-refresh every second

### Performance Optimized
- Virtual scrolling in browser (handles 10k+ requests)
- Batched log transmission
- Local file append (not rewrite)

## 📁 Files

| File | Purpose | Location |
|------|---------|----------|
| `template-onstart.sh` | Instance setup script | Remote: downloaded on start |
| `llama-proxy-viewer.py` | Proxy + Web UI + JSONL logger | Remote: `/root/` |
| `remote-log-forwarder.py` | Sends logs to your Mac | Remote: `/root/` |
| `local-log-forwarder.py` | Receives and saves logs | Local: your Mac |
| `start-log-sync.sh` | One-command setup | Local: your Mac |

## 💾 Log Format (JSONL)

Each line is a complete JSON object:
```json
{
  "timestamp": "2026-03-05T12:34:56.789",
  "id": "1234567890",
  "method": "POST",
  "path": "/v1/chat/completions",
  "headers": {...},
  "body": "{\"model\": \"...\", \"messages\": [...]}",
  "response_status": 200,
  "response_headers": {...},
  "response_body": "{\"choices\": [...]}",
  "duration_ms": 1234.5
}
```

## 🔍 Use Cases

1. **Debugging**: Full request/response trace
2. **Analytics**: Token usage, latency, error rates
3. **Training Data**: Capture conversations for fine-tuning
4. **Monitoring**: Real-time performance tracking
5. **Compliance**: Complete audit trail

## 🛠️ Manual Setup

If you prefer manual control:

```bash
# On remote instance
wget https://raw.githubusercontent.com/itzrnvr/vast-llama-template/main/llama-proxy-viewer.py
python3 llama-proxy-viewer.py

# On your Mac (in another terminal)
ssh -L 8767:localhost:8767 -L 9000:localhost:9000 -L 9001:localhost:9001 root@<instance-ip> -p <port>
python3 local-log-forwarder.py
```

## ⚠️ Interruptible Instance Notes

- **Data Loss Prevention**: Logs sync in real-time to your Mac
- **Auto-reconnect**: Forwarder automatically reconnects if SSH tunnel drops
- **Resume**: If instance stops, restart `start-log-sync.sh` to resume
- **JSONL**: Local file grows continuously, survives any interruption

## 📈 Analytics Example

```python
import json

# Analyze your logs
with open('~/llama-logs/requests.jsonl') as f:
    for line in f:
        req = json.loads(line)
        print(f"{req['duration_ms']}ms - {req['path']}")
```

## 🔧 Troubleshooting

**Port already in use:**
```bash
pkill -f start-log-sync
./start-log-sync.sh
```

**No logs appearing:**
- Check SSH tunnel: `ssh -p <port> root@<host> "tail /root/requests.jsonl"`
- Check forwarder: `ssh -p <port> root@<host> "tail /root/forwarder.log"`

**Slow browser:**
- Local viewer only shows last 100 requests
- Use filters to reduce what's displayed
- Download JSONL for offline analysis

## 📚 Architecture

```
┌─────────────────┐     SSH Tunnel      ┌──────────────────┐
│   Your Mac      │ ◄─────────────────► │  Vast.ai Instance│
│                 │                     │                  │
│ ┌─────────────┐ │                     │ ┌──────────────┐ │
│ │Local Viewer │ │◄──WebSocket (8767)──│ │Log Forwarder │ │
│ │  (8768)     │ │                     │ │              │ │
│ └─────────────┘ │                     │ └──────────────┘ │
│        ▲        │                     │        ▲         │
│        │        │                     │        │         │
│ ┌─────────────┐ │                     │ ┌──────────────┐ │
│ │  JSONL File │ │                     │ │  JSONL File  │ │
│ │  (persist)  │ │                     │ │  (temporary) │ │
│ └─────────────┘ │                     │ └──────────────┘ │
└─────────────────┘                     │        ▲         │
                                        │        │         │
                                        │ ┌──────────────┐ │
                                        │ │Proxy+Viewer  │ │
                                        │ │  (9000/9001) │ │
                                        │ └──────────────┘ │
                                        │        ▲         │
                                        │        │         │
                                        │ ┌──────────────┐ │
                                        │ │Llama Server  │ │
                                        │ │  (18001)     │ │
                                        │ └──────────────┘ │
                                        └──────────────────┘
```

## 🤝 Contributing

All scripts are in this repo. Modify and push - new instances will use the updated version automatically.
