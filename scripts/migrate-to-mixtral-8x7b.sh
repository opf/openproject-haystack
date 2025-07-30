#!/bin/bash

# Migrate from Mixtral 8x22B to 8x7B for Memory Optimization
# This script updates the model configuration and downloads the smaller model

set -e

echo "🔄 Migrating to Mixtral 8x7B"
echo "============================"
echo ""
echo "This will switch from Mixtral 8x22B (44GB memory) to 8x7B (15GB memory)"
echo ""

VLLM_ROOT="/scratch/vllm"

# Check if vLLM installation exists
if [ ! -d "$VLLM_ROOT" ]; then
    echo "❌ vLLM installation not found at $VLLM_ROOT"
    echo "Please run ./scripts/vllm-external-drive.sh first"
    exit 1
fi

echo "📁 Found vLLM installation at: $VLLM_ROOT"
echo ""

# Stop the current service
echo "1️⃣ Stopping vLLM service..."
sudo systemctl stop vllm-mixtral.service || echo "Service was not running"
echo "✅ Service stopped"
echo ""

# Backup current configuration
echo "2️⃣ Backing up current configuration..."
sudo cp "$VLLM_ROOT/config/vllm.conf" "$VLLM_ROOT/config/vllm.conf.8x22b.backup"
echo "✅ Configuration backed up to vllm.conf.8x22b.backup"
echo ""

# Update configuration for Mixtral 8x7B
echo "3️⃣ Updating configuration for Mixtral 8x7B..."
sudo tee "$VLLM_ROOT/config/vllm.conf" > /dev/null << EOF
# vLLM Configuration for Mixtral 8x7B (External Drive Installation)
MODEL=mistral-community/Mixtral-8x7B-v0.1-AWQ
HOST=0.0.0.0
PORT=8001
GPU_MEMORY_UTILIZATION=0.80
MAX_MODEL_LEN=8192
DTYPE=auto
TRUST_REMOTE_CODE=false
CACHE_DIR=$VLLM_ROOT/models
LOG_LEVEL=INFO
VLLM_ROOT=$VLLM_ROOT

# PyTorch optimizations
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_VISIBLE_DEVICES=0

# HuggingFace cache
HF_HOME=$VLLM_ROOT/models

# Triton cache (critical for GPU compute)
TRITON_CACHE_DIR=$VLLM_ROOT/.cache/triton
XDG_CACHE_HOME=$VLLM_ROOT/.cache

# Additional temp directories
TMPDIR=$VLLM_ROOT/tmp
TMP=$VLLM_ROOT/tmp
TEMP=$VLLM_ROOT/tmp
EOF

sudo chown vllm:vllm "$VLLM_ROOT/config/vllm.conf"
echo "✅ Configuration updated for Mixtral 8x7B"
echo ""

# Download new model
echo "4️⃣ Downloading Mixtral 8x7B AWQ model (~13GB)..."
echo "This will take several minutes depending on your internet speed..."
echo ""

MODEL_CACHE="$VLLM_ROOT/models"
sudo -u vllm env HF_HOME="$MODEL_CACHE" \
    "$VLLM_ROOT/venv/bin/python3" -c "
import huggingface_hub
print('🔽 Downloading Mixtral 8x7B AWQ model...')
print('📦 Size: ~13GB (much smaller than 8x22B)')
huggingface_hub.snapshot_download(
    'mistral-community/Mixtral-8x7B-v0.1-AWQ',
    cache_dir='$MODEL_CACHE'
)
print('✅ Model download complete!')
"

echo ""
echo "✅ Mixtral 8x7B model downloaded successfully"
echo ""

# Update systemd service description
echo "5️⃣ Updating systemd service..."
sudo sed -i 's/Mixtral 8x22B/Mixtral 8x7B/g' /etc/systemd/system/vllm-mixtral.service
sudo systemctl daemon-reload
echo "✅ Systemd service updated"
echo ""

# Restart service with new configuration
echo "6️⃣ Starting vLLM service with Mixtral 8x7B..."
sudo systemctl start vllm-mixtral.service
echo "✅ Service started"
echo ""

# Wait for startup
echo "⏳ Waiting 10 seconds for service startup..."
sleep 10

# Check service status
echo "7️⃣ Checking service status..."
if systemctl is-active --quiet vllm-mixtral.service; then
    echo "✅ Service is running"
    echo ""
    
    # Check if port is listening
    if ss -tlnp | grep -q ":8001"; then
        echo "✅ Port 8001 is listening"
        echo ""
        
        # Test API health
        echo "🌡️ Testing API health..."
        sleep 5
        if curl -s -f http://localhost:8001/health >/dev/null 2>&1; then
            echo "✅ API health endpoint is responding"
            echo ""
            echo "🎉 Migration to Mixtral 8x7B completed successfully!"
        else
            echo "⚠️  API not yet ready (model may still be loading)"
            echo "   Monitor with: journalctl -u vllm-mixtral -f"
        fi
    else
        echo "❌ Port 8001 is not listening"
        echo "❌ Service may have failed to start"
    fi
else
    echo "❌ Service failed to start"
    echo ""
    echo "📋 Troubleshooting:"
    echo "   sudo systemctl status vllm-mixtral"
    echo "   journalctl -u vllm-mixtral -f"
fi

echo ""
echo "📊 GPU Memory Status:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,memory.free --format=csv,noheader

echo ""
echo "📊 Model Comparison:"
echo "🔸 OLD: Mixtral 8x22B - ~44GB memory usage (99% GPU utilization)"
echo "🔸 NEW: Mixtral 8x7B  - ~15GB memory usage (~34% GPU utilization)"
echo ""
echo "💡 Benefits of 8x7B:"
echo "   • 66% less memory usage"
echo "   • Faster loading and inference"
echo "   • Much more stable operation"
echo "   • Double the context length (8192 vs 4096 tokens)"
echo "   • Plenty of headroom for larger batches"
echo ""

# Show disk usage
echo "💾 Disk Usage After Migration:"
if [ -d "$VLLM_ROOT/models" ]; then
    du -sh $VLLM_ROOT/models/* 2>/dev/null || echo "Model directory structure updating..."
fi

echo ""
echo "🔧 Management Commands:"
echo "   • Health check: $VLLM_ROOT/bin/health-check.sh"
echo "   • Disk usage: $VLLM_ROOT/bin/disk-usage.sh" 
echo "   • View logs: journalctl -u vllm-mixtral -f"
echo "   • Restart: sudo systemctl restart vllm-mixtral"
echo ""
echo "✨ Your vLLM service is now running Mixtral 8x7B with optimal memory usage!"
