# Native vLLM Setup Guide

This guide walks you through migrating from Docker-based Mixtral vLLM to a native installation running directly on your server. This approach should resolve CUDA out of memory issues and provide better performance.

## Overview

**Benefits of Native vLLM:**
- ✅ No Docker memory overhead - Full GPU memory available
- ✅ Better CUDA memory management - Direct allocation
- ✅ Easier debugging - Native process monitoring  
- ✅ Faster startup times - No container initialization
- ✅ More stable - Fewer abstraction layers

**Architecture Change:**
```
BEFORE: API Container → vLLM Container → GPU
AFTER:  API Container → Native vLLM → GPU
```

## Prerequisites

- **Operating System**: Ubuntu 20.04+ or similar Linux distribution
- **GPU**: NVIDIA GPU with 40GB+ VRAM (tested on L40S with 48GB)
- **CUDA**: Version 12.1+ (will be installed automatically if missing)
- **System Memory**: 16GB+ RAM recommended
- **Storage**: 30GB+ free space for model and dependencies
- **User Access**: sudo privileges for system installation

## Migration Steps

### Step 1: Stop Current Docker Services

```bash
# Stop all running containers
docker compose down

# Clean up Docker resources (optional but recommended)
docker system prune -f
```

### Step 2: Install Native vLLM

```bash
# Make the installation script executable (already done)
chmod +x scripts/install-native-vllm.sh

# Run the installation script
./scripts/install-native-vllm.sh
```

**What this script does:**
1. Checks NVIDIA GPU and installs CUDA 12.1 if needed
2. Creates dedicated `vllm` system user for security
3. Sets up directory structure in `/opt/vllm/`
4. Creates Python virtual environment
5. Installs vLLM and PyTorch with CUDA support
6. Downloads Mixtral 8x22B AWQ model (~26GB)
7. Creates systemd service for automatic startup
8. Configures logging and monitoring

### Step 3: Update Docker Compose Configuration

```bash
# Make the configuration update script executable (already done)
chmod +x scripts/update-compose-for-native-vllm.sh

# Run the configuration update
./scripts/update-compose-for-native-vllm.sh
```

**What this script does:**
1. Backs up current `docker-compose.yml`
2. Creates new configuration without vLLM container
3. Updates environment variables for native vLLM
4. Creates development override file
5. Sets up systemd integration
6. Creates monitoring and testing scripts

### Step 4: Start Native vLLM Service

```bash
# Start the native vLLM service
sudo systemctl start vllm-mixtral

# Check service status
sudo systemctl status vllm-mixtral

# Monitor startup logs (model loading takes 60-90 seconds)
journalctl -u vllm-mixtral -f
```

**Expected startup sequence:**
1. Service starts and loads configuration
2. PyTorch initializes CUDA context
3. Model downloads/loads from cache (~60-90 seconds)
4. vLLM server starts listening on port 8001
5. Health endpoint becomes available

### Step 5: Start API Service

```bash
# Start the API service (now configured for native vLLM)
docker compose up -d api

# Check if services are communicating
docker compose logs api
```

### Step 6: Test the Setup

```bash
# Use the comprehensive test script
./scripts/test-native-vllm.sh

# Or test manually:
# Test vLLM directly
curl -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-community/Mixtral-8x22B-v0.1-AWQ",
    "prompt": "Hello! How are you?",
    "max_tokens": 50
  }'

# Test through API service
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test-model",
    "messages": [{"role": "user", "content": "Say hello!"}],
    "max_tokens": 30
  }'
```

## Configuration Files

### Native vLLM Configuration: `/opt/vllm/config/vllm.conf`
```bash
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
```

### Updated Docker Compose: `docker-compose.yml`
```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    volumes:
      - ./src:/app/src
      - ./config:/app/config
    ports:
      - "8000:8000"
    environment:
      - VLLM_URL=http://host.docker.internal:8001  # Points to native vLLM
      - USE_VLLM_DEFAULT=true
    depends_on:
      - wait-for-vllm

  wait-for-vllm:
    image: curlimages/curl:latest
    command: >
      sh -c "
        until curl -f http://host.docker.internal:8001/health; do
          echo 'Waiting for native vLLM...'
          sleep 5
        done
      "
```

### Environment Variables: `.env`
```bash
# Native vLLM Configuration
VLLM_URL=http://localhost:8001
VLLM_MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
USE_VLLM_DEFAULT=true
```

## Service Management

### Native vLLM Service (systemd)
```bash
# Start service
sudo systemctl start vllm-mixtral

# Stop service  
sudo systemctl stop vllm-mixtral

# Restart service
sudo systemctl restart vllm-mixtral

# Enable auto-start on boot
sudo systemctl enable vllm-mixtral

# Check status
sudo systemctl status vllm-mixtral

# View logs
journalctl -u vllm-mixtral -f
```

### API Service (Docker)
```bash
# Start API
docker compose up -d api

# Stop API
docker compose stop api

# Restart API
docker compose restart api

# View logs
docker compose logs -f api
```

## Monitoring

### Use the Monitoring Script
```bash
# Comprehensive system monitoring
./scripts/monitor-native-vllm.sh
```

### Manual Monitoring
```bash
# Check GPU usage
nvidia-smi

# Check vLLM process
ps aux | grep vllm

# Check memory usage
free -h

# Check disk usage
df -h /opt/vllm

# Test health endpoints
curl http://localhost:8001/health  # Native vLLM
curl http://localhost:8000/health  # API service
```

## Troubleshooting

### Common Issues

#### 1. vLLM Service Won't Start
**Symptoms**: `systemctl status vllm-mixtral` shows failed state

**Solutions**:
```bash
# Check detailed logs
journalctl -u vllm-mixtral -n 50

# Common issues:
# - CUDA not found: Install NVIDIA drivers and CUDA toolkit
# - Model not found: Check /opt/vllm/models directory
# - Permission issues: Check vllm user permissions
sudo chown -R vllm:vllm /opt/vllm
```

#### 2. Out of Memory Errors  
**Symptoms**: CUDA OOM errors in logs

**Solutions**:
```bash
# Reduce GPU memory utilization
sudo nano /opt/vllm/config/vllm.conf
# Change GPU_MEMORY_UTILIZATION from 0.90 to 0.85 or 0.80

# Restart service
sudo systemctl restart vllm-mixtral
```

#### 3. API Can't Connect to vLLM
**Symptoms**: API logs show connection refused errors

**Solutions**:
```bash
# Check vLLM is listening
sudo netstat -tlnp | grep 8001

# Check firewall (if applicable)
sudo ufw status

# Verify health endpoint
curl http://localhost:8001/health
```

#### 4. Model Loading Too Slow
**Symptoms**: Service takes >5 minutes to start

**Solutions**:
```bash
# Check disk I/O
iostat -x 1

# Move model to faster storage if needed
# Check available space
df -h /opt/vllm
```

### Performance Tuning

#### Optimize for Your Hardware
```bash
# Edit configuration
sudo nano /opt/vllm/config/vllm.conf

# For 48GB GPU (L40S):
GPU_MEMORY_UTILIZATION=0.90
MAX_MODEL_LEN=4096

# For 40GB GPU (A100):
GPU_MEMORY_UTILIZATION=0.85
MAX_MODEL_LEN=3072

# For 24GB GPU (RTX 4090):
GPU_MEMORY_UTILIZATION=0.80
MAX_MODEL_LEN=2048
```

## Rollback Plan

If you need to revert to Docker-based vLLM:

```bash
# Stop native vLLM
sudo systemctl stop vllm-mixtral
sudo systemctl disable vllm-mixtral

# Restore original Docker Compose
cp docker-compose.yml.backup.YYYYMMDD_HHMMSS docker-compose.yml

# Start Docker services
docker compose up -d
```

## Performance Expectations

With native vLLM on NVIDIA L40S (48GB VRAM):

- **Model Loading**: 60-90 seconds (first start)
- **First Token Latency**: 300-500ms
- **Token Generation Speed**: 60-100 tokens/second
- **Concurrent Users**: 3-5 simultaneous requests
- **Memory Usage**: ~38-42GB GPU memory
- **CPU Usage**: 2-4 cores during inference

## Security Considerations

- vLLM runs as dedicated `vllm` user (not root)
- Service restricted to localhost by default
- Log rotation configured to prevent disk filling
- Model files protected with appropriate permissions
- No network access required after initial setup

## Maintenance

### Regular Tasks
```bash
# Check service health weekly
./scripts/monitor-native-vllm.sh

# Monitor disk usage
df -h /opt/vllm

# Check for system updates monthly
sudo apt update && sudo apt upgrade

# Review logs for errors
journalctl -u vllm-mixtral --since "7 days ago" | grep ERROR
```

### Model Updates
```bash
# To update to a newer model:
sudo systemctl stop vllm-mixtral

# Update model in configuration
sudo nano /opt/vllm/config/vllm.conf

# Download new model
sudo -u vllm /opt/vllm/venv/bin/python3 -c "
import huggingface_hub
huggingface_hub.snapshot_download('NEW_MODEL_NAME', cache_dir='/opt/vllm/models')
"

# Restart service
sudo systemctl restart vllm-mixtral
```

## Support

For issues specific to this native setup:

1. **Check service logs**: `journalctl -u vllm-mixtral -f`
2. **Run monitoring script**: `./scripts/monitor-native-vllm.sh`
3. **Test connectivity**: `./scripts/test-native-vllm.sh`
4. **Verify GPU resources**: `nvidia-smi`
5. **Check system resources**: `htop`

The native setup provides better debugging capabilities and should resolve the CUDA memory issues you were experiencing with Docker.
