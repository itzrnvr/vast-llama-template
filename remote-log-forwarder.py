#!/usr/bin/env python3
"""
Remote log forwarder - runs on the Vast.ai instance
Reads JSONL file and forwards to local Mac via WebSocket
"""
import asyncio
import json
import os
import time
import websockets
from pathlib import Path

JSONL_FILE = '/root/requests.jsonl'
LOCAL_WS_URL = 'ws://localhost:8767'  # Will be forwarded via SSH tunnel
BATCH_SIZE = 10
FLUSH_INTERVAL = 1  # seconds

async def forward_logs():
    """Forward logs from JSONL file to WebSocket"""
    print(f"📡 Log Forwarder starting...")
    print(f"   Source: {JSONL_FILE}")
    print(f"   Target: {LOCAL_WS_URL}")
    print()
    
    last_position = 0
    sent_count = 0
    
    while True:
        try:
            async with websockets.connect(LOCAL_WS_URL) as websocket:
                print(f"   ✅ Connected to local forwarder")
                
                while True:
                    if not os.path.exists(JSONL_FILE):
                        await asyncio.sleep(1)
                        continue
                    
                    with open(JSONL_FILE, 'r') as f:
                        f.seek(last_position)
                        lines = f.readlines()
                        last_position = f.tell()
                    
                    if lines:
                        batch = []
                        for line in lines:
                            line = line.strip()
                            if line:
                                try:
                                    record = json.loads(line)
                                    batch.append(record)
                                except json.JSONDecodeError:
                                    continue
                        
                        if batch:
                            # Send in batches for efficiency
                            for i in range(0, len(batch), BATCH_SIZE):
                                chunk = batch[i:i+BATCH_SIZE]
                                for record in chunk:
                                    await websocket.send(json.dumps(record))
                                    sent_count += 1
                                
                                if sent_count % 100 == 0:
                                    print(f"   📤 Sent {sent_count} requests")
                                
                                await asyncio.sleep(0.01)  # Small delay between batches
                    
                    await asyncio.sleep(FLUSH_INTERVAL)
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"   ⚠️  Connection lost, retrying in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            await asyncio.sleep(5)

if __name__ == '__main__':
    # Install websockets if needed
    try:
        import websockets
    except ImportError:
        print("Installing websockets...")
        os.system("pip3 install websockets -q")
        import websockets
    
    asyncio.run(forward_logs())
