#!/bin/bash

# VLLM Memory Fix Script
# This script addresses CUDA out of memory issues with Mixtral 8x22B

echo "🔧 VLLM Memory Fix Script Starting..."
echo "This will clean up GPU memory and restart services with optimized settings."
echo ""

# Check if running as root (may be needed for Docker operations)
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  Running as root - this is fine for Docker operations"
fi

# Step 1: Check current GPU memory usage
echo "1️⃣ Checking current GPU memory usage..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
    echo ""
else
    echo "❌ nvidia-smi not found. Please ensure NVIDIA drivers are installed."
    exit 1
fi

# Step 2: Stop all containers
echo "2️⃣ Stopping all Docker containers..."
docker compose down
sleep 5

# Step 3: Clean up Docker resources
echo "3️⃣ Cleaning up Docker resources..."
docker system prune -f
docker builder prune -f

# Step 4: Check for any remaining GPU processes
echo "4️⃣ Checking for remaining GPU processes..."
if command -v fuser &> /dev/null; then
    # Kill any processes using CUDA devices
    for i in {0..7}; do
        if [ -e "/dev/nvidia$i" ]; then
            echo "Checking /dev/nvidia$i..."
            fuser -k /dev/nvidia$i 2>/dev/null || true
        fi
    done
fi

# Step 5: Restart Docker daemon (if possible)
echo "5️⃣ Attempting to restart Docker daemon..."
if systemctl is-active --quiet docker; then
    echo "Restarting Docker daemon..."
    sudo systemctl restart docker
    sleep 10
else
    echo "Docker daemon restart requires manual action or different permissions"
fi

# Step 6: Verify GPU memory is clear
echo "6️⃣ Verifying GPU memory is cleared..."
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
echo ""

# Step 7: Rebuild vLLM container with new configuration
echo "7️⃣ Rebuilding vLLM container with memory optimizations..."
echo "New settings:"
echo "  - GPU Memory Utilization: 85% (was 95%)"
echo "  - Max Model Length: 2048 tokens (was 4096)"
echo "  - PyTorch Memory Management: Enabled"
echo ""

docker compose build --no-cache mixtral-vllm

# Step 8: Start services
echo "8️⃣ Starting services with new configuration..."
docker compose up -d mixtral-vllm

# Step 9: Monitor startup
echo "9️⃣ Monitoring vLLM startup (this may take 60-90 seconds)..."
echo "Waiting for model to load..."

# Wait for health check to pass
timeout=300  # 5 minutes
elapsed=0
interval=10

while [ $elapsed -lt $timeout ]; do
    if curl -s -f http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ vLLM service is healthy!"
        break
    else
        echo "⏳ Still loading... ($elapsed/$timeout seconds)"
        sleep $interval
        elapsed=$((elapsed + interval))
        
        # Show container logs if there are issues
        if [ $elapsed -gt 60 ]; then
            echo "📋 Recent vLLM logs:"
            docker compose logs --tail=10 mixtral-vllm
            echo ""
        fi
    fi
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ vLLM service failed to start within $timeout seconds"
    echo "📋 Full logs:"
    docker compose logs mixtral-vllm
    exit 1
fi

# Step 10: Start API service
echo "🔟 Starting API service..."
docker compose up -d api

# Final verification
echo "✅ Memory optimization complete!"
echo ""
echo "📊 Final GPU memory usage:"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
echo ""
echo "🔗 Service endpoints:"
echo "  - vLLM API: http://localhost:8001"
echo "  - Main API: http://localhost:8000"
echo ""
echo "🧪 Test the service:"
echo 'curl -X POST http://localhost:8000/v1/chat/completions \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"model": "test", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 50}'"'"''
echo ""
echo "✨ Done! The VLLM memory issue should now be resolved."
