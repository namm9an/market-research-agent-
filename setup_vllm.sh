#!/bin/bash
# ============================================================
# vLLM Setup Script for E2E A100 80GB Instance
# v3 — Fully isolated virtual environment.
# ============================================================

set -e

echo "============================================"
echo "🚀 Market Research Agent — vLLM Setup (v3)"
echo "============================================"
echo ""

# Step 1: Check GPU
echo "📊 Step 1: Checking GPU..."
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo ""

# Step 2: System deps
echo "📦 Step 2: Installing tmux & curl..."
apt-get update -qq && apt-get install -y -qq tmux curl > /dev/null 2>&1
echo "✅ Done"
echo ""

# Step 3: Kill any old vLLM process
echo "🧹 Step 3: Cleaning up..."
tmux kill-session -t vllm-server 2>/dev/null || true
rm -rf /root/vllm-env
rm -f /root/vllm_server.log
echo "✅ Old environment removed"
echo ""

# Step 4: Create FULLY ISOLATED virtual environment
echo "📦 Step 4: Creating isolated virtual environment..."
echo "   (No --system-site-packages — clean slate)"
python3 -m venv /root/vllm-env
source /root/vllm-env/bin/activate
pip install --upgrade pip --quiet
echo "✅ Clean venv ready"
echo ""

# Step 5: Install vLLM (brings its own PyTorch + numpy)
echo "📦 Step 5: Installing vLLM + all dependencies..."
echo "   This downloads PyTorch + vLLM (~3GB). May take 5-10 min."
echo ""
pip install vllm 2>&1 | tail -5
echo ""
echo "✅ vLLM installed"
echo ""

# Step 6: Verify import
echo "🧪 Step 6: Testing import..."
python3 -c "
import numpy; print(f'   numpy  = {numpy.__version__}')
import torch;  print(f'   torch  = {torch.__version__}')
import vllm;   print(f'   vllm   = {vllm.__version__}')
print(f'   CUDA   = {torch.cuda.is_available()}')
print(f'   GPU    = {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NONE\"}')
"
echo "✅ All imports working"
echo ""

# Step 7: Start vLLM server
echo "🧠 Step 7: Starting vLLM server..."
echo "   Model: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
echo "   First run downloads the model (~32GB)"
echo ""

tmux new-session -d -s vllm-server \
    "source /root/vllm-env/bin/activate && \
     python -m vllm.entrypoints.openai.api_server \
        --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16 \
        --trust-remote-code \
        --max-model-len 8192 \
        --host 0.0.0.0 \
        --port 8000 \
        2>&1 | tee /root/vllm_server.log"

echo "✅ Server starting in tmux"
echo ""

# Step 8: Wait for ready
echo "⏳ Waiting for server (up to 30 min)..."
echo "   You can also watch live: tmux attach -t vllm-server"
echo ""

MAX_WAIT=1800
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "============================================"
        echo "✅ vLLM SERVER IS READY!"
        echo "============================================"
        echo ""
        curl -s http://localhost:8000/v1/chat/completions \
            -H "Content-Type: application/json" \
            -d '{
                "model": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16",
                "messages": [{"role": "user", "content": "Say hello in one sentence."}],
                "max_tokens": 50
            }' | python3 -m json.tool
        echo ""
        echo "🎉 VLLM_BASE_URL = http://205.147.102.105:8000/v1/"
        echo "============================================"
        exit 0
    fi
    LOG=$(tail -1 /root/vllm_server.log 2>/dev/null | cut -c1-120 || echo "waiting...")
    echo "   [${WAITED}s] $LOG"
    sleep 15
    WAITED=$((WAITED + 15))
done

echo ""
echo "⚠️  Didn't respond in 30 min. Check: tmux attach -t vllm-server"
