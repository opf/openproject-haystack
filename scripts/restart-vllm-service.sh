#!/bin/bash

echo "🔄 Restarting vLLM Service"
echo "=========================="
echo ""

# Stop the service
echo "🛑 Stopping vllm-mixtral service..."
sudo systemctl stop vllm-mixtral.service || echo "Service was not running"
echo "✅ Service stopped"

# Ensure cache directories exist with proper permissions
echo "📁 Creating missing cache directories..."
VLLM_ROOT="/scratch/vllm"
if [ -d "$VLLM_ROOT" ]; then
    sudo -u vllm mkdir -p "$VLLM_ROOT/.cache/triton"
    sudo -u vllm mkdir -p "$VLLM_ROOT/.cache"
    sudo -u vllm mkdir -p "$VLLM_ROOT/tmp"
    echo "✅ Cache directories verified"
else
    echo "⚠️  vLLM installation not found at $VLLM_ROOT"
fi

# Reload systemd (in case the service file was updated)
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd reloaded"

# Start the service
echo "🚀 Starting vllm-mixtral service..."
sudo systemctl start vllm-mixtral.service
echo "✅ Service started"

# Wait a moment for startup
echo "⏳ Waiting 5 seconds for service startup..."
sleep 5

# Check status
echo "📊 Service Status:"
sudo systemctl status vllm-mixtral.service --no-pager -l

echo ""
echo "🔍 Recent logs:"
journalctl -u vllm-mixtral.service --no-pager -n 10

echo ""
echo "🏥 Health Check:"
echo "Checking if port 8001 is listening..."
if ss -tlnp | grep -q ":8001"; then
    echo "✅ Port 8001 is listening"
    echo ""
    echo "🌐 Testing API endpoint..."
    sleep 2
    if curl -s -f http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ API health endpoint is responding"
        echo ""
        echo "🎉 vLLM service is running successfully!"
    else
        echo "⚠️  API health endpoint not yet ready (service may still be loading model)"
        echo "   This is normal - the Mixtral model takes 1-2 minutes to load"
        echo "   Monitor with: journalctl -u vllm-mixtral -f"
    fi
else
    echo "❌ Port 8001 is not listening"
    echo "❌ Service may have failed to start"
    echo ""
    echo "📋 To troubleshoot:"
    echo "   sudo systemctl status vllm-mixtral"
    echo "   journalctl -u vllm-mixtral -f"
fi

echo ""
echo "📊 GPU Status:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
