#!/bin/bash

# Install vLLM on External Drive (for disk space issues)
# This script handles installation when the main drive is full

set -e

echo "🚀 Installing vLLM on External Drive"
echo "===================================="
echo ""

# Function to check available space
check_space() {
    local path="$1"
    local required_gb="$2"
    local available_gb=$(df -BG "$path" | awk 'NR==2 {print $4}' | sed 's/G//')
    
    echo "📊 Space check for $path:"
    echo "   Available: ${available_gb}GB"
    echo "   Required:  ${required_gb}GB"
    
    if [ "$available_gb" -ge "$required_gb" ]; then
        echo "   ✅ Sufficient space"
        return 0
    else
        echo "   ❌ Insufficient space"
        return 1
    fi
}

# Function to find best installation path
find_install_path() {
    local required_space=60  # 60GB required (PyTorch + vLLM + Model)
    
    echo "🔍 Searching for installation location with ${required_space}GB+ free space..." >&2
    echo "" >&2
    
    # List of potential paths to check (in order of preference)
    local paths=(
        "/scratch"
        "/data"
        "/opt"
        "/mnt"
        "/tmp"
        "/var/tmp"
        "/home"
        "/"
    )
    
    # Check mounted filesystems with enough space
    echo "📋 Available mount points:" >&2
    df -h | grep -E "^/dev|^tmpfs" | while read filesystem size used avail percent mount; do
        avail_num=$(echo $avail | sed 's/[^0-9.]//g')
        unit=$(echo $avail | sed 's/[0-9.]//g')
        
        # Convert to GB for comparison
        if [[ "$unit" == "T" ]]; then
            avail_gb=$((${avail_num%.*} * 1024))
        elif [[ "$unit" == "G" ]]; then
            avail_gb=${avail_num%.*}
        else
            avail_gb=0
        fi
        
        if [ "$avail_gb" -ge "$required_space" ]; then
            echo "   ✅ $mount: ${avail} available" >&2
        else
            echo "   ❌ $mount: ${avail} available (too small)" >&2
        fi
    done
    echo "" >&2
    
    # Try each path
    for path in "${paths[@]}"; do
        if [ -d "$path" ]; then
            # Redirect check_space output to stderr
            if check_space "$path" "$required_space" >&2 2>&1; then
                echo "🎯 Selected installation path: $path" >&2
                echo "$path"
                return 0
            fi
        fi
    done
    
    echo "" >&2
    echo "❌ No suitable location found with ${required_space}GB+ free space!" >&2
    echo "" >&2
    echo "💡 Options:" >&2
    echo "   1. Free up space on existing drives" >&2
    echo "   2. Mount an external drive to one of these locations:" >&2
    echo "      - /scratch" >&2
    echo "      - /data" >&2
    echo "      - /mnt/vllm" >&2
    echo "   3. Use Docker with scratch space (see scripts/move-docker-to-scratch.sh)" >&2
    echo "" >&2
    exit 1
}

# Get installation path
INSTALL_BASE=$(find_install_path)
VLLM_ROOT="$INSTALL_BASE/vllm"

echo ""
echo "📁 Installation will use: $VLLM_ROOT"
echo ""

# Ask for confirmation
read -p "Continue with installation at $VLLM_ROOT? (y/N): " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

echo ""
echo "🏗️  Starting installation..."
echo ""

# Check GPU and drivers
echo "1️⃣ Checking NVIDIA GPU and drivers..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi not found. Please install NVIDIA drivers first."
    exit 1
fi

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Create vllm user
echo "2️⃣ Creating vLLM service user..."
if ! id "vllm" &>/dev/null; then
    sudo useradd -r -s /bin/false -d "$VLLM_ROOT" vllm
    echo "✅ Created vllm service user"
else
    echo "✅ vllm user already exists"
fi

# Create directories on external drive
echo "3️⃣ Creating directory structure on external drive..."
sudo mkdir -p "$VLLM_ROOT"/{bin,models,logs,config,venv}
sudo chown -R vllm:vllm "$VLLM_ROOT"

# Create symlinks in standard locations
echo "4️⃣ Creating system integration symlinks..."
if [ "$VLLM_ROOT" != "/opt/vllm" ]; then
    sudo ln -sf "$VLLM_ROOT" /opt/vllm
fi

echo "✅ Created directory structure at $VLLM_ROOT"

# Install system dependencies
echo "5️⃣ Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential

# Create virtual environment on external drive
echo "6️⃣ Creating Python virtual environment..."
sudo -u vllm python3 -m venv "$VLLM_ROOT/venv"
echo "✅ Created virtual environment at $VLLM_ROOT/venv"

# Configure all temp and cache directories on external drive
echo "7️⃣ Configuring external storage for all temporary files..."
PIP_CACHE_DIR="$VLLM_ROOT/.cache/pip"
TEMP_DIR="$VLLM_ROOT/tmp"
BUILD_DIR="$VLLM_ROOT/build"
TRITON_CACHE_DIR="$VLLM_ROOT/.cache/triton"
XDG_CACHE_DIR="$VLLM_ROOT/.cache"

# Create all necessary directories
sudo -u vllm mkdir -p "$PIP_CACHE_DIR" "$TEMP_DIR" "$BUILD_DIR" "$TRITON_CACHE_DIR" "$XDG_CACHE_DIR"
echo "✅ Created cache, temp, and Triton directories on external drive"

# Install PyTorch with all temp files redirected to external drive
echo "8️⃣ Installing PyTorch with CUDA support (using external storage)..."
echo "   This may take 10-15 minutes..."
echo "   All temporary files will use external drive to avoid space issues"

# First upgrade pip
sudo -u vllm env \
    PIP_CACHE_DIR="$PIP_CACHE_DIR" \
    TMPDIR="$TEMP_DIR" \
    TMP="$TEMP_DIR" \
    TEMP="$TEMP_DIR" \
    BUILDDIR="$BUILD_DIR" \
    "$VLLM_ROOT/venv/bin/pip" install --upgrade pip

echo "   Downloading PyTorch (~2.5GB) to external storage..."
# Install PyTorch with all environment variables set to use external drive
sudo -u vllm env \
    PIP_CACHE_DIR="$PIP_CACHE_DIR" \
    TMPDIR="$TEMP_DIR" \
    TMP="$TEMP_DIR" \
    TEMP="$TEMP_DIR" \
    BUILDDIR="$BUILD_DIR" \
    PYTORCH_BUILD_DIR="$BUILD_DIR" \
    "$VLLM_ROOT/venv/bin/pip" install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121 \
    --cache-dir "$PIP_CACHE_DIR"

# Install vLLM
echo "9️⃣ Installing vLLM..."
sudo -u vllm env \
    PIP_CACHE_DIR="$PIP_CACHE_DIR" \
    TMPDIR="$TEMP_DIR" \
    TMP="$TEMP_DIR" \
    TEMP="$TEMP_DIR" \
    BUILDDIR="$BUILD_DIR" \
    "$VLLM_ROOT/venv/bin/pip" install vllm \
    --cache-dir "$PIP_CACHE_DIR"

# Install additional dependencies
echo "🔟 Installing additional dependencies..."
sudo -u vllm env \
    PIP_CACHE_DIR="$PIP_CACHE_DIR" \
    TMPDIR="$TEMP_DIR" \
    TMP="$TEMP_DIR" \
    TEMP="$TEMP_DIR" \
    BUILDDIR="$BUILD_DIR" \
    "$VLLM_ROOT/venv/bin/pip" install huggingface-hub \
    --cache-dir "$PIP_CACHE_DIR"

echo "✅ Installed vLLM with CUDA support"

# Test CUDA availability
echo "1️⃣1️⃣ Testing CUDA availability..."
sudo -u vllm "$VLLM_ROOT/venv/bin/python3" -c "
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

# Download Mixtral model to external drive
echo "1️⃣2️⃣ Downloading Mixtral 8x22B AWQ model (~26GB)..."
echo "This will take several minutes depending on your internet speed..."

MODEL_CACHE="$VLLM_ROOT/models"
sudo -u vllm env HF_HOME="$MODEL_CACHE" \
    "$VLLM_ROOT/venv/bin/python3" -c "
import huggingface_hub
print('Downloading Mixtral 8x22B AWQ model...')
huggingface_hub.snapshot_download(
    'mistral-community/Mixtral-8x22B-v0.1-AWQ',
    cache_dir='$MODEL_CACHE'
)
print('✅ Model download complete!')
"

# Create configuration
echo "1️⃣3️⃣ Creating vLLM configuration..."
sudo tee "$VLLM_ROOT/config/vllm.conf" > /dev/null << EOF
# vLLM Configuration for Mixtral 8x22B (External Drive Installation)
MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
HOST=0.0.0.0
PORT=8001
GPU_MEMORY_UTILIZATION=0.90
MAX_MODEL_LEN=4096
DTYPE=auto
TRUST_REMOTE_CODE=false
CACHE_DIR=$MODEL_CACHE
LOG_LEVEL=INFO
VLLM_ROOT=$VLLM_ROOT

# PyTorch optimizations
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_VISIBLE_DEVICES=0

# HuggingFace cache
HF_HOME=$MODEL_CACHE

# Triton cache (critical for GPU compute)
TRITON_CACHE_DIR=$VLLM_ROOT/.cache/triton
XDG_CACHE_HOME=$VLLM_ROOT/.cache

# Additional temp directories
TMPDIR=$VLLM_ROOT/tmp
TMP=$VLLM_ROOT/tmp
TEMP=$VLLM_ROOT/tmp
EOF

sudo chown vllm:vllm "$VLLM_ROOT/config/vllm.conf"

# Create startup script
echo "1️⃣4️⃣ Creating startup script..."
sudo tee "$VLLM_ROOT/bin/start-vllm.sh" > /dev/null << EOF
#!/bin/bash

# vLLM Startup Script (External Drive)
set -e

# Load configuration
source $VLLM_ROOT/config/vllm.conf

# Create cache directories if they don't exist
mkdir -p "\$TRITON_CACHE_DIR"
mkdir -p "\$XDG_CACHE_HOME"
mkdir -p "\$TMPDIR"

# Set all environment variables
export PYTORCH_CUDA_ALLOC_CONF
export CUDA_VISIBLE_DEVICES
export HF_HOME
export TRITON_CACHE_DIR
export XDG_CACHE_HOME
export TMPDIR
export TMP
export TEMP

# Change to vLLM directory
cd \$VLLM_ROOT

# Start vLLM server
exec \$VLLM_ROOT/venv/bin/python3 -m vllm.entrypoints.openai.api_server \\
    --model "\$MODEL" \\
    --host "\$HOST" \\
    --port "\$PORT" \\
    --gpu-memory-utilization "\$GPU_MEMORY_UTILIZATION" \\
    --max-model-len "\$MAX_MODEL_LEN" \\
    --dtype "\$DTYPE" \\
    --trust-remote-code "\$TRUST_REMOTE_CODE" \\
    --download-dir "\$CACHE_DIR"
EOF

sudo chmod +x "$VLLM_ROOT/bin/start-vllm.sh"
sudo chown vllm:vllm "$VLLM_ROOT/bin/start-vllm.sh"

# Create systemd service
echo "1️⃣5️⃣ Creating systemd service..."
sudo tee /etc/systemd/system/vllm-mixtral.service > /dev/null << EOF
[Unit]
Description=vLLM Mixtral 8x22B Inference Server (External Drive)
After=network.target
StartLimitBurst=3
StartLimitIntervalSec=60

[Service]
Type=exec
User=vllm
Group=vllm
WorkingDirectory=$VLLM_ROOT
ExecStart=$VLLM_ROOT/bin/start-vllm.sh
ExecReload=/bin/kill -HUP \$MAINPID
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
ReadWritePaths=$VLLM_ROOT
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vllm-mixtral.service

echo "✅ Created systemd service"

# Create health check script
echo "1️⃣6️⃣ Creating monitoring utilities..."
sudo tee "$VLLM_ROOT/bin/health-check.sh" > /dev/null << 'EOF'
#!/bin/bash

echo "🏥 vLLM Health Check"
echo "===================="
echo ""

# Check service status
echo "📊 Service Status:"
systemctl is-active vllm-mixtral || echo "Service not running"
echo ""

# Check if port is listening
echo "🔌 Port Status:"
if ss -tlnp | grep -q ":8001"; then
    echo "✅ Port 8001 is listening"
else
    echo "❌ Port 8001 is not listening"
fi
echo ""

# Check API health endpoint
echo "🌡️ API Health:"
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ API is responding"
else
    echo "❌ API is not responding"
fi
echo ""

# Check GPU usage
echo "🎮 GPU Status:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
EOF

sudo chmod +x "$VLLM_ROOT/bin/health-check.sh"
sudo chown vllm:vllm "$VLLM_ROOT/bin/health-check.sh"

# Create disk usage monitor
sudo tee "$VLLM_ROOT/bin/disk-usage.sh" > /dev/null << EOF
#!/bin/bash

echo "💾 vLLM Disk Usage"
echo "=================="
echo ""

# Check vLLM directory usage
echo "📁 vLLM Installation:"
du -sh $VLLM_ROOT/*
echo ""

# Check mount point usage
echo "🗄️ Mount Point Usage:"
df -h "$VLLM_ROOT"
echo ""

# Check model cache size
echo "🤖 Model Cache:"
if [ -d "$VLLM_ROOT/models" ]; then
    du -sh $VLLM_ROOT/models/*
else
    echo "No models cached"
fi
EOF

sudo chmod +x "$VLLM_ROOT/bin/disk-usage.sh"
sudo chown vllm:vllm "$VLLM_ROOT/bin/disk-usage.sh"

echo ""
echo "🎉 vLLM Installation Complete!"
echo "=============================="
echo ""
echo "✅ Installation Summary:"
echo "  • Location: $VLLM_ROOT"
echo "  • Service: vllm-mixtral.service"
echo "  • Port: 8001"
echo "  • Models: $MODEL_CACHE"
echo ""
echo "🚀 Next Steps:"
echo "  1. Start the service:"
echo "     sudo systemctl start vllm-mixtral"
echo ""
echo "  2. Check status:"
echo "     sudo systemctl status vllm-mixtral"
echo "     $VLLM_ROOT/bin/health-check.sh"
echo ""
echo "  3. Monitor logs:"
echo "     journalctl -u vllm-mixtral -f"
echo ""
echo "  4. Test health:"
echo "     curl http://localhost:8001/health"
echo ""
echo "  5. Update Docker Compose:"
echo "     ./scripts/update-compose-for-native-vllm.sh"
echo ""
echo "🔧 Monitoring:"
echo "  • Health check: $VLLM_ROOT/bin/health-check.sh"
echo "  • Disk usage: $VLLM_ROOT/bin/disk-usage.sh"
echo ""
echo "✨ This installation uses $VLLM_ROOT with full disk space management!"
