#!/bin/bash

# Native vLLM Installation Script for Mixtral 8x22B
# This installs vLLM directly on the host system for better GPU memory management

set -e

echo "🚀 Native vLLM Installation for Mixtral 8x22B"
echo "=============================================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  This script should not be run as root for security reasons"
   echo "   Please run as a regular user with sudo privileges"
   exit 1
fi

# Check for NVIDIA GPU
echo "1️⃣ Checking NVIDIA GPU availability..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi not found. Please install NVIDIA drivers first."
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Check CUDA installation
echo "2️⃣ Checking CUDA installation..."
if ! command -v nvcc &> /dev/null; then
    echo "⚠️  CUDA toolkit not found. Installing CUDA 12.1..."
    wget https://developer.download.nvidia.com/compute/cuda/12.1.1/local_installers/cuda_12.1.1_530.30.02_linux.run
    sudo sh cuda_12.1.1_530.30.02_linux.run --silent --toolkit
    echo 'export PATH=/usr/local/cuda-12.1/bin:$PATH' >> ~/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
    source ~/.bashrc
else
    nvcc --version
fi
echo ""

# Create dedicated user for vLLM service
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
echo ""

# Install Python dependencies
echo "5️⃣ Installing Python and dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential

# Create virtual environment
echo "6️⃣ Creating Python virtual environment..."
sudo -u vllm python3 -m venv /opt/vllm/venv
echo "✅ Created virtual environment at /opt/vllm/venv"

# Install vLLM and dependencies
echo "7️⃣ Installing vLLM..."
sudo -u vllm /opt/vllm/venv/bin/pip install --upgrade pip
sudo -u vllm /opt/vllm/venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu121
sudo -u vllm /opt/vllm/venv/bin/pip install vllm
sudo -u vllm /opt/vllm/venv/bin/pip install huggingface-hub
echo "✅ Installed vLLM and dependencies"
echo ""

# Download Mixtral model
echo "8️⃣ Downloading Mixtral 8x22B AWQ model (~26GB)..."
echo "This will take several minutes depending on your internet connection..."
sudo -u vllm /opt/vllm/venv/bin/python3 -c "
import huggingface_hub
print('Downloading Mixtral 8x22B AWQ model...')
huggingface_hub.snapshot_download(
    'mistral-community/Mixtral-8x22B-v0.1-AWQ',
    cache_dir='/opt/vllm/models'
)
print('✅ Model download complete!')
"

# Create vLLM configuration file
echo "9️⃣ Creating vLLM configuration..."
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
echo "✅ Created vLLM configuration"
echo ""

# Create startup script
echo "🔟 Creating vLLM startup script..."
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
echo "✅ Created startup script"
echo ""

# Create systemd service
echo "1️⃣1️⃣ Creating systemd service..."
sudo tee /etc/systemd/system/vllm-mixtral.service > /dev/null << 'EOF'
[Unit]
Description=vLLM Mixtral 8x22B Inference Server
After=network.target nvidia-persistenced.service
Wants=nvidia-persistenced.service
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

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable vllm-mixtral.service
echo "✅ Created and enabled systemd service"
echo ""

# Create log rotation
echo "1️⃣2️⃣ Setting up log rotation..."
sudo tee /etc/logrotate.d/vllm-mixtral > /dev/null << 'EOF'
/opt/vllm/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 vllm vllm
    postrotate
        systemctl reload vllm-mixtral.service > /dev/null 2>&1 || true
    endscript
}
EOF

echo "✅ Configured log rotation"
echo ""

# Final summary
echo "🎉 Native vLLM Installation Complete!"
echo "======================================"
echo ""
echo "📋 Installation Summary:"
echo "  • vLLM installed in: /opt/vllm/venv"
echo "  • Model cached in: /opt/vllm/models"
echo "  • Configuration: /opt/vllm/config/vllm.conf"
echo "  • Service: vllm-mixtral.service"
echo "  • Log location: journalctl -u vllm-mixtral -f"
echo ""
echo "🔧 Service Management:"
echo "  • Start:   sudo systemctl start vllm-mixtral"
echo "  • Stop:    sudo systemctl stop vllm-mixtral"
echo "  • Status:  sudo systemctl status vllm-mixtral"
echo "  • Logs:    journalctl -u vllm-mixtral -f"
echo ""
echo "🌐 Service will be available at:"
echo "  • http://localhost:8001"
echo "  • Health check: curl http://localhost:8001/health"
echo ""
echo "⚠️  Next Steps:"
echo "  1. Start the service: sudo systemctl start vllm-mixtral"
echo "  2. Check status: sudo systemctl status vllm-mixtral" 
echo "  3. Update your Docker Compose configuration"
echo "  4. Test the API endpoint"
echo ""
echo "✨ Installation complete! The native setup should resolve your memory issues."
