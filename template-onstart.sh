#!/bin/bash

# Install dependencies
apt-get update && apt-get install -y python3-pip >/dev/null 2>&1 || true
pip3 install websockets >/dev/null 2>&1 || true

# Download the proxy viewer from GitHub
wget -q https://raw.githubusercontent.com/itzrnvr/vast-llama-template/main/llama-proxy-viewer.py -O /root/llama-proxy-viewer.py
chmod +x /root/llama-proxy-viewer.py

# Download remote log forwarder
wget -q https://raw.githubusercontent.com/itzrnvr/vast-llama-template/main/remote-log-forwarder.py -O /root/remote-log-forwarder.py
chmod +x /root/remote-log-forwarder.py

# Modify LLAMA_ARGS to use internal port 18001 (proxy will expose on 18000)
export LLAMA_ARGS="${LLAMA_ARGS/--port 18000/--port 18001}"

# Start the proxy viewer (ports: 18000=proxy, 9000=viewer, 9001=GPU)
nohup python3 /root/llama-proxy-viewer.py > /root/proxy-viewer.log 2>&1 &

# Start remote log forwarder for syncing to local Mac
nohup python3 /root/remote-log-forwarder.py > /root/forwarder.log 2>&1 &

sleep 3
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           🚀 LLaMA Server with Full Monitoring            ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  API Endpoint:  http://localhost:8000                     ║"
echo "║  Request Logs:  http://localhost:9000                     ║"
echo "║  GPU Stats:     http://localhost:9001                     ║"
echo "║  JSONL Log:     /root/requests.jsonl                      ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  For real-time sync to your Mac:                          ║"
echo "║  ./start-log-sync.sh [INSTANCE_ID]                        ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Run original entrypoint (starts llama-server)
exec entrypoint.sh
