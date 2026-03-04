| Service            | Port | URL                   |
| ------------------ | ---- | --------------------- |
| Llama.cpp (direct) | 8000 | http://localhost:8000 |
| Llama.cpp (proxy)  | 8001 | http://localhost:8001 |
| GPU Monitor        | 8765 | http://localhost:8765 |
| Request Inspector  | 8766 | http://localhost:8766 |
| Instance Portal    | 1111 | http://localhost:1111 |



# SSH into instance
ssh root@<instance-ip>
# Find and kill existing llama-server
ps aux | grep llama-server
kill <pid>
# Restart directly with new flags
/root/llama.cpp/build/bin/llama-server --model /root/Qwen3.5-35B-A3B-heretic-v2-Q5_K_M.gguf \
  --host 0.0.0.0 --port 18000 --ctx-size 32768 --n-gpu-layers 99