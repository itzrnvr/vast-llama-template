Write and execute scripts on the remote instance instead of running single commands. You may run single commands when you are trying to gather info. 

Plan before doing anything.

Think deeply always.

Observability matters. For long running tasks such as builds, downloads, and installations, provide an endpoint that can be externally accessed and show a webpage that shows all the progress that's happening so user can see what's going on.
Keep it verbose but structured so it is easier to debug.

Cleanup after yourself. Delete any temporary files or directories that you created. Leave no clutter or duplicates behind.

Think about the fastest and the most efficient approach to finishing the tasks. 

Start background terminal sessions using pty but keep track of them.
Execute/Run long running commands in background.
Do things in parallel whenever possible.

If a port is occupied, unless you are sure that the process using that port is not important, do not kill it. Instead, use a different port to run the process you want to run.


---

## LESSONS LEARNED FROM VAST.AI LLAMA.CPP DEPLOYMENT (March 2026)

### Critical Failures & Time Wasters

**1. Port Mapping Ignorance (15+ minutes wasted)**
- ALWAYS check cloud provider port mappings BEFORE choosing ports
- Vast.ai example: `env | grep VAST_TCP_PORT` shows mapped ports
- Available: 8080→36219, 6006→36023, 1111→36032, 8384→36118
- Attempting unmapped ports (8081, 8082) = complete waste of time

**2. Incomplete Downloads (20+ minutes wasted)**
- Large files (6GB models) get interrupted frequently
- ALWAYS verify file integrity: `ls -lh` and compare expected size
- Use wget with resume: `wget -c` or verify checksums
- Corrupted partial downloads cause cryptic errors later

**3. SSH Inefficiency (5+ minutes overhead)**
- Running 50+ separate SSH commands = massive overhead
- Each connection takes 2-3 seconds to authenticate
- SOLUTION: Execute everything in ONE script via single SSH call
- Alternative: Use PTY for interactive session when needed

**4. Process Management Chaos (10+ minutes)**
- Failed attempts leave zombie processes
- ALWAYS check before starting: `netstat -tlnp | grep PORT`
- Kill existing processes or choose different ports
- Jupyter/Caddy often pre-installed on cloud instances

**5. Poor Initial Planning**
- Didn't read environment first (port mappings, existing services)
- Didn't verify infrastructure constraints
- Should have: Check ports → Pick available → Deploy

**6. Build Timeout Issues**
- Long builds (10+ min) timeout in single commands
- SOLUTION: Run builds in background with `nohup` or use PTY
- Monitor progress via logs, not blocking calls

**7. Script Assumptions**
- Original script assumed port 8080 available
- Reality: Vast.ai has Jupyter on 8080
- ALWAYS audit scripts for environment-specific assumptions

### Optimal Deployment Pattern

```bash
# Option 1: Use robust scripts (recommended)
./deploy-to-vast-robust.sh --tunnel

# Option 2: Manual approach
# 1. Check infrastructure FIRST (30 seconds)
ssh instance "env | grep VAST_TCP_PORT"
ssh instance "netstat -tlnp | grep -E '(8080|6006|1111|8384)'"

# 2. Pick available port based on mappings
# 3. Execute complete deployment in ONE SSH call
# 4. Total time: ~15 minutes instead of 45+
```

### Server Process Persistence

**Issue: Server killed when SSH session ends**

Background processes started with `nohup` can still be killed if:
- SSH session terminates unexpectedly
- Container/instance management kills idle processes

**Solutions:**
1. Use `disown` after `nohup`: `nohup ./server & disown`
2. Create systemd service for persistence
3. Use `screen` or `tmux` session

### Golden Rules for Cloud Deployments

1. **Infrastructure Audit First**: Check ports, resources, existing services
2. **Verify CUDA Environment**: `nvcc --version && ldconfig -p | grep cublas` before building
3. **Single Script Execution**: One SSH call with complete setup script
4. **Verify Downloads**: Check file sizes, use resume-capable tools
5. **Observability Early**: Web dashboard for long-running tasks
6. **Port Strategy**: Check mappings → Verify availability → Deploy
7. **Process Hygiene**: Always check for conflicts before starting
8. **Timeout Awareness**: Background long builds, monitor via logs
9. **Use Robust Scripts**: `deploy-to-vast-robust.sh` handles all edge cases

### KV Cache Performance Optimization

**Critical Finding: KV Cache Data Type Matters**

After extensive testing on RTX 3090 with Crow-9B-Q5_K_M.gguf:

**Configuration Comparison:**
```
256K Context + Flash Attention + RTX 3090

K=f16, V=q8_0:  ~18-20 tok/s  (VRAM: ~13GB)
K=f16, V=f16:   ~56-80 tok/s  (VRAM: ~15GB)  ← RECOMMENDED
```

**Why f16 for both is faster:**
- No dequantization overhead during generation
- Better memory coalescing on GPU
- Flash Attention works optimally with uniform precision
- Only ~2GB more VRAM usage for 3x+ speed improvement

**Optimal Settings for 256K Context:**
```bash
./llama-server \
  --ctx-size 262144 \
  --batch-size 8192 \
  --flash-attn on \
  --cache-type-k f16 \
  --cache-type-v f16 \
  --n-gpu-layers 99
```

**Sampling Parameters (Thinking Mode):**
```bash
  --temp 1.0 \
  --top-p 0.95 \
  --top-k 20 \
  --min-p 0.0 \
  --presence-penalty 1.5 \
  --repeat-penalty 1.0
```

**Expected Performance:**
- Prompt processing: 60-90 tok/s
- Generation: 56-80 tok/s (varies with sequence length)
- VRAM usage: ~15GB / 24GB on RTX 3090

### GPU Performance Issues on Cloud Instances

**Critical Issue: GPU Power State Throttling**

After reboot, GPU may be stuck in P8 (idle) state at 210 MHz instead of P0 (max) at 1900+ MHz:

```
# Check GPU state
nvidia-smi --query-gpu=clocks.current.sm,power.draw,utilization.gpu --format=csv,noheader,nounits
# Output: 210, 15.28, 0  ← BAD (P8 idle state)
# Should be: 1905, 280, 95  ← GOOD (P0 max performance)
```

**Impact:** Generation speed drops from ~56-80 tok/s to ~30-40 tok/s (50% slower)

**Root Cause:** 
- Vast.ai containers use power management that throttles idle GPUs
- After reboot, GPU stays in low-power state until properly warmed up
- This is a container/infrastructure limitation, not configuration issue

**Workarounds:**
1. Run continuous inference to keep GPU warm (not practical)
2. Accept reduced speed after reboot (~30-40 tok/s instead of 56-80)
3. Use bare metal instances instead of containers (if available)

**Verification:**
```bash
# Check if GPU is throttled
nvidia-smi -q -d PERFORMANCE | grep "Performance State"
# P0 = Good (max performance)
# P8 = Bad (idle/throttled)
```

### CUDA Environment Issues on Vast.ai (CRITICAL)

**Problem: Vast.ai CUDA images have broken/misconfigured CUDA setup**

Discovered with `vastai/linux-desktop:cuda-12.9-ubuntu24.04`:
- Environment not configured (nvcc not in PATH, LD_LIBRARY_PATH empty)
- Broken symlinks: `libcublas.so.12` points to non-existent file
- Mixed CUDA versions: Toolkit 12.9 but cuBLAS library in 12.6

**Detection Commands:**
```bash
# Check if nvcc works
nvcc --version

# Check if cuBLAS is accessible
ldconfig -p | grep cublas

# Find actual cuBLAS library location
find /usr/local/cuda-* -name "libcublas.so.12.*" -type f
```

**Fix Pattern:**
```bash
# 1. Set environment
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 2. Fix broken symlinks
cd /usr/local/cuda/lib64
rm -f libcublas.so libcublas.so.12
ln -sf /usr/local/cuda-12.6/targets/x86_64-linux/lib/libcublas.so.12 libcublas.so.12
ln -sf libcublas.so.12 libcublas.so

# 3. Update ldconfig
echo "/usr/local/cuda/lib64" > /etc/ld.so.conf.d/cuda.conf
ldconfig
```

**Prevention:** ALWAYS verify CUDA works before building:
```bash
nvcc --version && ldconfig -p | grep cublas
```

### Robust Deployment Scripts

**Use these scripts for reliable deployment:**

1. **`deploy-to-vast-robust.sh`** (run locally) - Uploads and executes deployment
2. **`deploy-llama-robust.sh`** (runs on instance) - Handles all edge cases

**Features:**
- Auto-detects and fixes CUDA environment issues
- Parallel model download + build
- Verifies downloads and builds
- Idempotent (safe to run multiple times)
- Handles port conflicts

**Usage:**
```bash
# From laptop - one command
./deploy-to-vast-robust.sh --tunnel

# Or specify instance
./deploy-to-vast-robust.sh 32349398 --tunnel
```

**Time Savings:**
- First run: ~15 min (build + download)
- Subsequent runs: ~4 seconds (everything cached)

### Common Cloud Instance Gotchas

- **Jupyter**: Often on port 8080 or 8888
- **TensorBoard**: Often on port 6006
- **Caddy/Nginx**: May proxy ports
- **Port mappings**: External ≠ Internal (e.g., 8384 → 36118)
- **Base images**: Come with pre-installed services
- **GPU throttling**: Instances may throttle GPU after reboot (see above)
- **CUDA misconfig**: Vast.ai images have broken CUDA symlinks (see above)