# Vast.ai Template: llama-cpp-auto

## Overview

Simple LLM deployment template. Download any GGUF model and run with your custom llama-server command.

## Template Details

- **Name**: `llama-cpp-auto`
- **ID**: `355562`
- **Hash**: `62ffb8e0b250834131f023836f9d0f5e`
- **Image**: `vastai/linux-desktop:cuda-12.9-ubuntu24.04`
- **Access**: SSH with direct connections
- **Disk**: 50GB

## Quick Start

### 1. Set Up HuggingFace Token (Optional)

For faster downloads from HuggingFace, set your token as an environment variable when launching the instance:

```bash
# In Vast.ai web interface, add environment variable:
# Name: HF_TOKEN
# Value: hf_your_token_here
```

### 2. Launch Instance

```bash
vastai create instance --template 355562
```

### 2. Wait for Setup (~10-15 min)

Instance automatically:
- Fixes CUDA environment
- Builds llama.cpp with CUDA
- Creates `start-llm` command

### 3. Start Your Model

```bash
# SSH into instance
vastai ssh-url

# Run: start-llm <model-url> '<llama-server-command>'
start-llm https://huggingface.co/bartowski/Crow-9B-GGUF/resolve/main/Crow-9B-Q5_K_M.gguf \
  'llama-server --host 0.0.0.0 --port 8080 --ctx-size 262144 --n-gpu-layers 99 --flash-attn on --cache-type-k f16 --cache-type-v f16'
```

## Usage

**Format:**
```bash
start-llm <model-url> '<command-with-flags>'
```

**What it does:**
1. Downloads model to `/root/models/` (uses `HF_TOKEN` if set for authenticated downloads)
2. Runs: `/root/llama.cpp/build/bin/<your-command> --model /root/models/model.gguf`

## Environment Variables

| Variable | Description | Usage |
|----------|-------------|-------|
| `HF_TOKEN` | HuggingFace API token | Set in Vast.ai web interface for faster/authenticated downloads |

**How to set:**
1. Go to Vast.ai web interface
2. Find your template "llama-cpp-auto"
3. Add environment variable: `HF_TOKEN=hf_your_token_here`
4. Launch instance

## Examples

### Crow 9B (6GB)
```bash
start-llm https://huggingface.co/bartowski/Crow-9B-GGUF/resolve/main/Crow-9B-Q5_K_M.gguf \
  'llama-server --host 0.0.0.0 --port 8080 --ctx-size 262144 --n-gpu-layers 99 --batch-size 8192 --ubatch-size 2048 --flash-attn on --cache-type-k f16 --cache-type-v f16 --parallel 1 --cont-batching'
```

### Qwen 2.5 7B
```bash
start-llm https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q5_K_M.gguf \
  'llama-server --host 0.0.0.0 --port 8080 --ctx-size 262144 --n-gpu-layers 99 --flash-attn on --cache-type-k f16 --cache-type-v f16'
```

### Llama 3.2 3B
```bash
start-llm https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q5_K_M.gguf \
  'llama-server --host 0.0.0.0 --port 8080 --ctx-size 262144 --n-gpu-layers 99 --flash-attn on'
```

### Large Model with Reduced Context
```bash
start-llm https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf \
  'llama-server --host 0.0.0.0 --port 8080 --ctx-size 131072 --n-gpu-layers 99 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0'
```

## Finding Models

1. Browse: https://huggingface.co/models?search=gguf
2. Click on model → Files and versions
3. Copy the GGUF file link (must end in `.gguf`)

**Recommended quantizations:**
- `Q5_K_M` - Best quality/speed balance
- `Q4_K_M` - Smaller, slightly faster

## Port Mapping

```bash
# Check port mappings
env | grep VAST_TCP_PORT

# Example output:
# VAST_TCP_PORT_8080=12345
# Access at: http://YOUR_IP:12345
```

## Common Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--ctx-size` | Context length | `262144` (256K) |
| `--n-gpu-layers` | GPU layers | `99` (all) |
| `--flash-attn` | Flash Attention | `on` |
| `--cache-type-k` | K cache type | `f16` or `q8_0` |
| `--cache-type-v` | V cache type | `f16` or `q8_0` |
| `--batch-size` | Batch size | `8192` |
| `--ubatch-size` | Micro batch | `2048` |
| `--parallel` | Parallel sequences | `1` |
| `--cont-batching` | Continuous batching | (flag only) |

## Testing API

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Recommended GPUs

- **RTX 3090 (24GB)**: 7B-14B models with 256K context
- **RTX 4090 (24GB)**: Same, faster
- **A100 (40-80GB)**: 30B-70B models

## Troubleshooting

**Model won't start?**
- Reduce context: `--ctx-size 65536`
- Use quantized cache: `--cache-type-k q8_0 --cache-type-v q8_0`

**CUDA errors?**
- Check: `nvcc --version && ldconfig -p | grep cublas`
- Template auto-fixes these on startup

**Port in use?**
- Use different port: `--port 9000`

## Files

```
/root/
├── llama.cpp/build/bin/llama-server  # Binary
└── models/                           # Downloaded models
```
