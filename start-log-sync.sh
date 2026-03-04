#!/bin/bash
#
# start-log-sync.sh - Start real-time log sync from Vast.ai instance to local Mac
#
# Usage: ./start-log-sync.sh [INSTANCE_ID]
#

set -e

INSTANCE_ID="${1:-}"
LOCAL_WS_PORT=8767
LOCAL_VIEWER_PORT=8768
REMOTE_WS_PORT=8767

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Real-time Log Sync${NC}"
echo ""

# Check if vastai CLI is available
if ! command -v vastai &> /dev/null; then
    echo "❌ vastai CLI not found. Install with: pip install vastai"
    exit 1
fi

# Get instance ID if not provided
if [ -z "$INSTANCE_ID" ]; then
    echo "📋 Your running instances:"
    vastai show instances --raw | python3 -c "
import sys, json
data = json.load(sys.stdin)
for inst in data:
    if inst.get('actual_status') == 'running':
        print(f\"  {inst['id']}: {inst.get('gpu_name', 'Unknown GPU')} - {inst.get('image', 'No image')[:50]}...\")
"
    echo ""
    read -p "Enter Instance ID: " INSTANCE_ID
fi

if [ -z "$INSTANCE_ID" ]; then
    echo "❌ No instance ID provided"
    exit 1
fi

echo -e "${YELLOW}📡 Instance: $INSTANCE_ID${NC}"

# Get SSH connection info
echo "🔑 Getting SSH connection..."
SSH_URL=$(vastai ssh-url "$INSTANCE_ID" 2>/dev/null)

if [ -z "$SSH_URL" ]; then
    echo "❌ Failed to get SSH URL. Is instance running?"
    exit 1
fi

SSH_HOST=$(echo "$SSH_URL" | sed 's|ssh://root@||' | cut -d: -f1)
SSH_PORT=$(echo "$SSH_URL" | sed 's|ssh://root@||' | cut -d: -f2)

echo "   Host: $SSH_HOST"
echo "   Port: $SSH_PORT"

# Find SSH key
echo "🔐 Finding SSH key..."
SSH_KEY=""
for key in ~/.ssh/id_ed25519 ~/.ssh/id_rsa ~/.ssh/vast_ai; do
    if [ -f "$key" ]; then
        SSH_KEY="$key"
        break
    fi
done

if [ -z "$SSH_KEY" ]; then
    echo "❌ No SSH key found in ~/.ssh/"
    exit 1
fi

echo "   Key: $SSH_KEY"

# Kill existing tunnels
echo "🧹 Cleaning up existing tunnels..."
pkill -f "ssh.*$LOCAL_WS_PORT.*$SSH_HOST" 2>/dev/null || true
pkill -f "ssh.*9000.*$SSH_HOST" 2>/dev/null || true
pkill -f "ssh.*9001.*$SSH_HOST" 2>/dev/null || true
sleep 2

# Setup SSH tunnels
echo "🔌 Setting up SSH tunnels..."
echo "   Port $LOCAL_WS_PORT -> remote:$REMOTE_WS_PORT (log sync)"
echo "   Port 9000 -> remote:9000 (request viewer)"
echo "   Port 9001 -> remote:9001 (GPU stats)"

ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -fN -L $LOCAL_WS_PORT:localhost:$REMOTE_WS_PORT \
    -L 9000:localhost:9000 \
    -L 9001:localhost:9001 \
    -p "$SSH_PORT" -i "$SSH_KEY" "root@$SSH_HOST"

sleep 2

# Check if tunnel is working
if ! nc -z localhost $LOCAL_WS_PORT 2>/dev/null; then
    echo "⚠️  Warning: Tunnel may not be ready yet"
fi

# Upload remote forwarder
echo "📤 Uploading remote forwarder..."
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -P "$SSH_PORT" -i "$SSH_KEY" \
    "$(dirname "$0")/remote-log-forwarder.py" \
    "root@$SSH_HOST:/root/remote-log-forwarder.py" 2>/dev/null

# Start remote forwarder in background
echo "🚀 Starting remote forwarder..."
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -p "$SSH_PORT" -i "$SSH_KEY" "root@$SSH_HOST" \
    "nohup python3 /root/remote-log-forwarder.py > /root/forwarder.log 2>&1 &"

# Start local forwarder
echo "🖥️  Starting local log viewer..."
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "📊 Access points:"
echo "   Local viewer:    http://localhost:$LOCAL_VIEWER_PORT"
echo "   Remote viewer:   http://localhost:9000"
echo "   GPU stats:       http://localhost:9001"
echo ""
echo "💾 Logs saved to: ~/llama-logs/requests.jsonl"
echo ""
echo "Press Ctrl+C to stop..."
echo ""

# Start local forwarder
python3 "$(dirname "$0")/local-log-forwarder.py"
