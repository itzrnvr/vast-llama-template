# Usage: Qwen3.5-35B-heretic-v2-Q5KM Template

## 🚀 Zero-Setup Launch

1. **Create instance** from template `Qwen3.5-35B-heretic-v2-Q5KM` (ID: 355728)
2. **Wait 2-3 minutes** for startup to complete
3. **Click buttons in Vast.ai UI:**

### ✅ Available After Launch

| Button | URL | What You See |
|--------|-----|--------------|
| **Llama.cpp UI** | http://localhost:8000 | Chat interface with your model |
| **Request Logs** | http://localhost:9000 | Full request/response inspector |
| **GPU Stats** | http://localhost:9001 | Real-time GPU monitoring |
| **Jupyter** | http://localhost:8080 | Terminal access |

### 💾 Logs Saved on Instance

All requests automatically saved to: `/root/requests.jsonl`

## 🔄 Optional: Sync to Your Mac

For backup and analytics, run this **on your Mac** (not on the instance):

```bash
./start-log-sync.sh [INSTANCE_ID]
```

This gives you:
- **Local logs**: `~/llama-logs/requests.jsonl` (persists even if instance dies)
- **Local viewer**: http://localhost:8768
- **Real-time sync**: Logs stream as they happen

## 📊 Viewing Logs

### On the Instance (Browser)
1. Click "Request Logs" button in Vast.ai UI
2. See all requests in real-time
3. Expand cards to view full request/response
4. Use filters (All/Success/Errors/Chat)

### In Terminal (SSH)
```bash
# Tail the live JSONL file
ssh root@<instance-ip> -p <port> "tail -f /root/requests.jsonl"

# Or download entire file
scp -P <port> root@<instance-ip>:/root/requests.jsonl ./
```

## 🎯 API Usage

The API is ready immediately at: **http://localhost:8000**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llmfan46/Qwen3.5-35B-A3B-heretic-v2-GGUF:Q5_K_M",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

All requests automatically appear in the Request Logs UI.

## ⚡ Performance

- **Request logging**: Zero overhead (async)
- **Web UI**: Lazy loading, handles 10k+ requests
- **GPU monitoring**: <1% CPU usage
- **JSONL**: Append-only, no I/O blocking

## 🛠️ Troubleshooting

**Buttons show "No URL available":**
- Wait 2-3 minutes for full startup
- Refresh Vast.ai instance page

**Request Logs empty:**
- Check server is running: `ps aux | grep llama-server`
- Check logs: `tail /root/proxy-viewer.log`
- Check if proxy is listening: `netstat -tlnp | grep 18000`

**Instance crashes:**
- JSONL file at `/root/requests.jsonl` persists until instance destroyed
- Download before destroying: `scp -P <port> root@<host>:/root/requests.jsonl ./`

## 📈 Analytics Example

```python
import json

# SSH into instance and read JSONL
with open('/root/requests.jsonl') as f:
    for line in f:
        req = json.loads(line)
        print(f"{req['duration_ms']}ms - Tokens: {req.get('usage', {}).get('total_tokens', 0)}")
```

## 🔒 Security

- JSONL file: `/root/requests.jsonl` (private to instance)
- Web UI: No auth on ports 9000/9001 (instance-level security)
- Vast.ai portal: Token-protected
- To restrict: Edit `llama-proxy-viewer.py` and add auth
