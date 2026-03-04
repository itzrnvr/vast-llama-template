# LLaMA.cpp Auto-Setup with Web Monitoring

A complete automated setup script for LLaMA.cpp server with real-time web monitoring dashboard.

## What It Does

1. **Downloads & builds** latest LLaMA.cpp with CUDA support
2. **Downloads** the Crow-9B-Opus-4.6 model (Q5_K_M quantization)
3. **Starts** the server with 131k context and full GPU offloading
4. **Launches** a web monitoring portal on port 8081

## Quick Start

```bash
# On your new Vast.ai / RunPod / any GPU instance:
scp -P <SSH_PORT> -i ~/.ssh/id_ed25519 setup-llama.sh root@<IP>:/root/
ssh -p <SSH_PORT> -i ~/.ssh/id_ed25519 root@<IP> "bash /root/setup-llama.sh"
```

Or run directly:

```bash
curl -fsSL https://raw.githubusercontent.com/yourrepo/main/setup-llama.sh | bash
```

## Web Monitoring Portal

Once running, the script provides:

### URLs
- **Monitor Dashboard**: `http://<IP>:8081` (or Vast-mapped port)
- **LLaMA API**: `http://<IP>:8080` (or Vast-mapped port)
- **Anthropic API**: `http://<IP>:8080/v1/messages`

### Features
- ✅ Real-time server status (online/offline)
- ✅ GPU memory usage with visual progress bar
- ✅ GPU temperature and utilization
- ✅ Live log streaming
- ✅ Endpoint URLs displayed

## API Usage Examples

### OpenAI-compatible:
```bash
curl -X POST http://<IP>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Crow-9B-Q5_K_M.gguf",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Anthropic-compatible:
```bash
curl -X POST http://<IP>:8080/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Crow-9B-Q5_K_M.gguf",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## Configuration

Edit these variables at the top of `setup-llama.sh`:

```bash
MODEL_URL="https://huggingface.co/..."  # Change model
CONTEXT_SIZE=131072                        # Change context
WEB_PORT=8081                              # Monitor port
API_PORT=8080                              # LLaMA API port
```

## Requirements

- **GPU**: NVIDIA with CUDA 11.8+ (tested on RTX 3060 12GB)
- **RAM**: 8GB+ system RAM
- **Disk**: 10GB free space
- **OS**: Ubuntu 20.04+ / Debian-based

## Monitoring

### View logs:
```bash
tail -f /tmp/llama-server.log
tail -f /tmp/llama-setup.log
```

### Check GPU:
```bash
nvidia-smi
```

### Stop server:
```bash
pkill -f llama-server
```

## Troubleshooting

### Server won't start
Check logs: `tail -100 /tmp/llama-server.log`

### GPU out of memory
Reduce context size: Edit `CONTEXT_SIZE=65536` in the script

### Port already in use
Kill existing: `pkill -f llama-server` or change `API_PORT`

### SSH connection issues
Wait 2-3 minutes after instance creation for SSH to be ready

## Performance Expectations

**RTX 3060 12GB:**
- Generation: ~40-45 tokens/sec
- Prompt processing: ~250-350 tokens/sec
- Context: 131,072 tokens
- VRAM usage: ~10.5GB

**RTX 4090 24GB:**
- Generation: ~100-130 tokens/sec
- Prompt processing: ~800-1000 tokens/sec
- Context: 131,072 tokens (or higher)

## License

MIT - Feel free to modify and distribute.
