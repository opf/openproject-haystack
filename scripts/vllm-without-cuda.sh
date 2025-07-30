#!/bin/bash

# Install vLLM without CUDA toolkit (use existing NVIDIA drivers)
# This bypasses CUDA installation issues by using pre-compiled wheels

set -e

echo "🚀 Installing vLLM without CUDA toolkit"
echo "======================================"
echo ""

# Clean up the failed CUDA download
echo "1️⃣ Cleaning up failed CUDA download..."
if [ -f "cuda_12.1.1_530.30.02_linux.run" ]; then
    echo "Removing corrupted CUDA installer..."
    rm -f cuda_12.1.1_530.30.02_linux.run
fi

# Check GPU and drivers
echo "2️⃣ Checking NVIDIA GPU and drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi not found. Please install NVIDIA drivers first."
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Create vllm user
echo "3️⃣ Creating vLLM service user..."
if ! id "vllm" &>/dev/null; then
    sudo useradd -r -s /bin/false -d /opt/vllm vllm
    echo "✅ Created vllm service user"
else
    echo "✅ vllm user already exists"
fi

# Create directories
echo "4️⃣ Creating directory structure..."
sudo mkdir -p /opt/vllm/{bin,models,logs,config}
sudo chown -R vllm:vllm /opt/vllm
echo "✅ Created /opt/vllm directory structure"

# Install system dependencies
echo "5️⃣ Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential

# Create virtual environment  
echo "6️⃣ Creating Python virtual environment..."
sudo -u vllm python3 -m venv /opt/vllm/venv
echo "✅ Created virtual environment"

# Install vLLM with pre-compiled CUDA wheels
echo "7️⃣ Installing vLLM with pre-compiled CUDA support..."
sudo -u vllm /opt/vllm/venv/bin/pip install --upgrade pip

# Install PyTorch with CUDA 12.1 support (pre-compiled)
echo "Installing PyTorch with CUDA 12.1..."
sudo -u vllm /opt/vllm/venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install vLLM (uses pre-compiled CUDA kernels)
echo "Installing vLLM..."
sudo -u vllm /opt/vllm/venv/bin/pip install vllm

# Install additional dependencies
echo "Installing additional dependencies..."
sudo -u vllm /opt/vllm/venv/bin/pip install huggingface-hub

echo "✅ Installed vLLM with CUDA support"

# Test CUDA availability in Python
echo "8️⃣ Testing CUDA availability..."
sudo -u vllm /opt/vllm/venv/bin/python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
else:
    print('❌ CUDA not available - check NVIDIA drivers')
    exit(1)
"

# Download Mixtral model
echo "9️⃣ Downloading Mixtral 8x22B AWQ model (~26GB)..."
echo "This will take several minutes..."
sudo -u vllm /opt/vllm/venv/bin/python3 -c "
import huggingface_hub
print('Downloading Mixtral 8x22B AWQ model...')
huggingface_hub.snapshot_download(
    'mistral-community/Mixtral-8x22B-v0.1-AWQ',
    cache_dir='/opt/vllm/models'
)
print('✅ Model download complete!')
"

# Create configuration
echo "🔟 Creating vLLM configuration..."
sudo tee /opt/vllm/config/vllm.conf > /dev/null << 'EOF'
# vLLM Configuration for Mixtral 8x22B
MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
HOST=0.0.0.0
PORT=8001
GPU_MEMORY_UTILIZATION=0.90
MAX_MODEL_LEN=4096
DTYPE=auto
TRUST_REMOTE_CODE=false
CACHE_DIR=/opt/vllm/models
LOG_LEVEL=INFO

# PyTorch optimizations
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_VISIBLE_DEVICES=0
EOF

sudo chown vllm:vllm /opt/vllm/config/vllm.conf

# Create startup script
echo "1️⃣1️⃣ Creating startup script..."
sudo tee /opt/vllm/bin/start-vllm.sh > /dev/null << 'EOF'
#!/bin/bash

# vLLM Startup Script
set -e

# Load configuration
source /opt/vllm/config/vllm.conf

# Set environment variables
export PYTORCH_CUDA_ALLOC_CONF
export CUDA_VISIBLE_DEVICES

# Start vLLM server
cd /opt/vllm
exec /opt/vllm/venv/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host "$HOST" \
    --port "$PORT" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-model-len "$MAX_MODEL_LEN" \
    --dtype "$DTYPE" \
    --trust-remote-code "$TRUST_REMOTE_CODE" \
    --download-dir "$CACHE_DIR" \
    --log-level "$LOG_LEVEL"
EOF

sudo chmod +x /opt/vllm/bin/start-vllm.sh
sudo chown vllm:vllm /opt/vllm/bin/start-vllm.sh

# Create systemd service
echo "1️⃣2️⃣ Creating systemd service..."
sudo tee /etc/systemd/system/vllm-mixtral.service > /dev/null << 'EOF'
[Unit]
Description=vLLM Mixtral 8x22B Inference Server
After=network.target
StartLimitBurst=3
StartLimitIntervalSec=60

[Service]
Type=exec
User=vllm
Group=vllm
WorkingDirectory=/opt/vllm
ExecStart=/opt/vllm/bin/start-vllm.sh
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=on-failure
RestartSec=10

# Resource limits
LimitNOFILE=65536
LimitMEMLOCK=infinity

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vllm-mixtral

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vllm
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vllm-mixtral.service

echo "✅ Created systemd service"

echo ""
echo "🎉 vLLM Installation Complete!"
echo "============================="
echo ""
echo "✅ Installation Summary:"
echo "  • vLLM installed with pre-compiled CUDA support"
echo "  • Model cached in: /opt/vllm/models"
echo "  • Service: vllm-mixtral.service"
echo ""
echo "🚀 Next Steps:"
echo "  1. Start the service: sudo systemctl start vllm-mixtral"
echo "  2. Check status: sudo systemctl status vllm-mixtral"
echo "  3. Monitor logs: journalctl -u vllm-mixtral -f"
echo "  4. Test health: curl http://localhost:8001/health"
echo ""
echo "🔧 If it works, run the Docker Compose update:"
echo "     ./scripts/update-compose-for-native-vllm.sh"
echo ""
echo "✨ This bypasses CUDA toolkit installation by using pre-compiled wheels!"
