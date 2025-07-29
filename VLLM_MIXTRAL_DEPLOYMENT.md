# vLLM Mixtral 8x22B Integration Guide

This document describes the integration of Mixtral 8x22B AWQ quantized model with vLLM for high-performance inference on NVIDIA L40S hardware.

## Overview

The system now supports both Ollama and vLLM backends:
- **vLLM (Default)**: High-performance inference with Mixtral 8x22B AWQ
- **Ollama (Fallback)**: Existing models for compatibility

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Service   │ -> │ Generation       │ -> │ vLLM Mixtral    │
│   (Port 8000)   │    │ Pipeline         │    │ (Port 8001)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Ollama Fallback │
                       │ (Port 11434)    │
                       └─────────────────┘
```

## Deployment

### 1. Build and Start Services

```bash
# Build the vLLM container (downloads ~26GB model)
docker compose build mixtral-vllm

# Start all services
docker compose up -d
```

### 2. Configuration

The system is configured via environment variables:

```bash
# vLLM Configuration (enabled by default)
VLLM_URL=http://mixtral-vllm:8000
VLLM_MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
USE_VLLM_DEFAULT=true

# Ollama Configuration (fallback)
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=mistral:latest
```

### 3. Service Dependencies

- **mixtral-vllm**: Requires NVIDIA GPU with 48GB VRAM
- **api**: Depends on mixtral-vllm service
- **ollama**: Optional fallback service

## Features

### Model Override
All requests are automatically routed to Mixtral 8x22B regardless of client model specification:

```python
# Client requests mistral:latest
request.model = "mistral:latest" 

# System overrides to:
request.model = "mistral-community/Mixtral-8x22B-v0.1-AWQ"
```

### Performance Optimizations

#### GPU Memory Utilization
- **95% GPU memory usage** (safe for 48GB VRAM)
- **4096 max model length** optimized for most use cases
- **Concurrent request handling** via vLLM

#### Request Routing
- **Chat completions**: Direct vLLM API calls
- **BlockNote integration**: Enhanced JSON generation
- **Project reports**: High-quality analysis with RAG
- **Hint generation**: Smart fallback to optimizer

### Error Handling
- **Fail-fast approach**: Requests fail immediately if vLLM is unavailable
- **Clear error messages**: Detailed logging for troubleshooting
- **Health checks**: Service monitoring and automatic restart

## Service Configuration

### vLLM Service (mixtral-vllm)
```yaml
ports: ["8001:8000"]
resources:
  limits: { memory: 32G, cpus: '8.0' }
  reservations: { memory: 16G, cpus: '4.0' }
gpu: NVIDIA driver required
```

### API Service
```yaml
ports: ["8000:8000"]
depends_on: [ollama, ollama-init, mixtral-vllm]
resources:
  limits: { memory: 2G, cpus: '2.0' }
```

## Testing

### Health Check
```bash
# Check vLLM service
curl http://localhost:8001/health

# Check API service 
curl http://localhost:8000/health
```

### Chat Completion Test
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "any-model-name",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### BlockNote Integration Test
```bash
# Test with BlockNote.js function calling
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "any-model",
    "messages": [{"role": "user", "content": "Create a heading about AI"}],
    "tools": [{"type": "function", "function": {"name": "json"}}],
    "tool_choice": {"type": "function", "function": {"name": "json"}}
  }'
```

## Monitoring

### Log Files
- **vLLM logs**: `docker compose logs mixtral-vllm`
- **API logs**: `docker compose logs api`
- **System logs**: Check for model override messages

### Resource Usage
```bash
# GPU utilization
nvidia-smi

# Container resources
docker stats
```

### Health Endpoints
- **vLLM**: `http://localhost:8001/health`
- **API**: `http://localhost:8000/health`
- **Ollama**: `http://localhost:11434/api/tags`

## Troubleshooting

### Common Issues

#### 1. vLLM Service Fails to Start
**Symptoms**: API service shows vLLM connection errors
**Solutions**:
- Verify NVIDIA drivers: `nvidia-smi`
- Check GPU memory: Should have ~30GB+ free
- Verify model download: `docker logs mixtral-vllm`

### 1.1. Build Issues with Model Download
**Symptoms**: Docker build fails with "TypeError: EngineArgs.__init__() got an unexpected keyword argument 'download_only'"
**Solution**: Fixed in latest Dockerfile.vllm - now uses huggingface-hub for reliable model download
- The build now uses `huggingface_hub.snapshot_download()` instead of vLLM's download_only parameter
- This is version-independent and more reliable

#### 2. Out of Memory Errors
**Symptoms**: CUDA OOM errors in vLLM logs
**Solutions**:
- Reduce `gpu-memory-utilization` in Dockerfile.vllm
- Close other GPU processes
- Use smaller `max-model-len`

#### 3. Slow Response Times
**Symptoms**: Requests timeout or take >30 seconds
**Solutions**:
- Check GPU utilization with `nvidia-smi`
- Verify no CPU bottlenecks
- Consider reducing `max_tokens` in requests

#### 4. Model Override Not Working
**Symptoms**: Clients receive errors about model not found
**Solutions**:
- Check `USE_VLLM_DEFAULT=true` in environment
- Verify GenerationPipeline logs show model override
- Ensure vLLM service is healthy

### Recovery Steps

#### Hard Reset
```bash
# Stop all services
docker compose down

# Clean up resources
docker system prune -f

# Rebuild and restart
docker compose build --no-cache
docker compose up -d
```

#### Fallback to Ollama
```bash
# Temporarily disable vLLM
export USE_VLLM_DEFAULT=false
docker compose restart api
```

## Performance Expectations

With NVIDIA L40S (48GB VRAM):
- **Model Loading**: ~60-90 seconds initial startup
- **First Token Latency**: ~500-800ms
- **Token Generation**: ~50-80 tokens/second
- **Concurrent Users**: 2-4 simultaneous requests
- **Memory Usage**: ~28-32GB GPU memory

## Integration Points

### Existing Features (Compatible)
- ✅ BlockNote.js integration
- ✅ Project status reports  
- ✅ German hint generation
- ✅ RAG pipeline enhancement
- ✅ OpenProject API integration

### New Capabilities (Enhanced)
- 🚀 **Superior text quality** with Mixtral 8x22B
- 🚀 **Better JSON generation** for BlockNote
- 🚀 **Improved multilingual support**
- 🚀 **Enhanced reasoning** for complex tasks
- 🚀 **Consistent model responses** (no client override)

## Migration Notes

### From Ollama Only
1. Existing `.env` files continue to work
2. No API changes required
3. All endpoints remain compatible
4. Performance improves automatically

### Configuration Changes
- Add vLLM settings to `.env`
- Update Docker Compose for GPU access
- Ensure sufficient disk space (30GB+)

## Support

For issues specific to this integration:
1. Check service logs: `docker compose logs`
2. Verify GPU resources: `nvidia-smi`  
3. Test health endpoints
4. Review error messages in API logs

The system maintains full backward compatibility while providing significant performance improvements through vLLM and Mixtral 8x22B.
