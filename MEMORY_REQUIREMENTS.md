# Memory Requirements and Resource Management

## System Requirements

### Minimum System Requirements
- **Total RAM**: 10GB (recommended 12GB+)
- **Available RAM for Docker**: 8GB minimum
- **CPU**: 4 cores recommended
- **Storage**: 20GB free space for models and data

### Memory Allocation
- **Ollama Service**: 6-8GB (handles LLM model loading and inference)
- **API Service**: 512MB-2GB (FastAPI application and request processing)
- **System Overhead**: 2GB (OS and Docker overhead)

## Docker Resource Configuration

The docker-compose.yml file includes resource limits and reservations:

### Ollama Service
```yaml
deploy:
  resources:
    limits:
      memory: 8G        # Maximum memory usage
      cpus: '4.0'       # Maximum CPU cores
    reservations:
      memory: 6G        # Guaranteed memory allocation
      cpus: '2.0'       # Guaranteed CPU cores
```

### API Service
```yaml
deploy:
  resources:
    limits:
      memory: 2G        # Maximum memory usage
      cpus: '2.0'       # Maximum CPU cores
    reservations:
      memory: 512M      # Guaranteed memory allocation
      cpus: '0.5'       # Guaranteed CPU cores
```

## Environment Variables for Memory Optimization

### Ollama Configuration
- `OLLAMA_MAX_LOADED_MODELS=1`: Limits concurrent model loading
- `OLLAMA_NUM_PARALLEL=1`: Controls parallel processing
- `OLLAMA_KEEP_ALIVE=5m`: Model unload timeout

### Python/API Configuration
- `PYTHONUNBUFFERED=1`: Prevents Python output buffering
- `PYTHONDONTWRITEBYTECODE=1`: Prevents .pyc file creation

## Troubleshooting Memory Issues

### Error: "model requires more system memory than is available"

**Symptoms:**
```
Status: 500
Error: model requires more system memory (5.7 GiB) than is available (2.8 GiB)
```

**Solutions:**

1. **Increase Docker Memory Allocation**
   ```bash
   # Check current Docker memory limit
   docker system info | grep -i memory
   
   # Increase Docker Desktop memory allocation in settings
   # Or for Docker Engine, modify daemon.json
   ```

2. **Verify System Memory**
   ```bash
   # Check total system memory
   free -h
   
   # Check Docker container memory usage
   docker stats
   ```

3. **Restart Services with New Configuration**
   ```bash
   docker compose down
   docker compose up -d
   ```

### Error: "Container killed due to memory limit"

**Solutions:**
1. Increase memory limits in docker-compose.yml
2. Use a smaller model (see Model Alternatives section)
3. Add swap space to the system

### Performance Issues

**Symptoms:**
- Slow response times
- High memory usage
- Container restarts

**Solutions:**
1. Monitor resource usage: `docker stats`
2. Check logs: `docker compose logs ollama`
3. Adjust `OLLAMA_KEEP_ALIVE` to free memory faster
4. Consider using quantized models

## Model Alternatives for Lower Memory

If you continue to experience memory issues, consider these smaller models:

### Recommended Models by Memory Usage
- `phi:latest` (~1.6GB) - Good balance of performance and memory
- `gemma:2b` (~1.4GB) - Efficient small model
- `tinyllama:latest` (~637MB) - Minimal memory footprint
- `mistral:7b-instruct-q4_0` (~4GB) - Quantized version of Mistral

### Switching Models
Update the `OLLAMA_MODEL` environment variable in your configuration:
```yaml
environment:
  - OLLAMA_MODEL=phi:latest
```

## Monitoring and Maintenance

### Regular Monitoring Commands
```bash
# Check container resource usage
docker stats

# Check Docker system resource usage
docker system df

# Monitor Ollama service logs
docker compose logs -f ollama

# Check API service logs
docker compose logs -f api
```

### Cleanup Commands
```bash
# Remove unused Docker resources
docker system prune -f

# Remove unused Ollama models
docker exec ollama_container ollama rm <model_name>

# Clear Docker build cache
docker builder prune -f
```

## Production Recommendations

1. **Use Docker Swarm or Kubernetes** for better resource management
2. **Implement horizontal scaling** for the API service
3. **Use external model hosting** (OpenAI, Anthropic) for high-traffic scenarios
4. **Set up monitoring** with Prometheus/Grafana
5. **Configure log rotation** to prevent disk space issues
6. **Use SSD storage** for better model loading performance

## Support

If you continue to experience memory-related issues:
1. Check system requirements above
2. Verify Docker memory allocation
3. Monitor resource usage with provided commands
4. Consider using smaller models or external LLM services
