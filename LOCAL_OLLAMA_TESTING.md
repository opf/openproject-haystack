# Local Ollama Testing Setup

This document explains how to test your application with your local Ollama instance instead of the Docker container for performance comparison.

## Quick Start

### Option 1: Using the Test Script (Recommended)

```bash
# Test with local Ollama
./test-local-ollama.sh local

# Test with Docker Ollama
./test-local-ollama.sh docker

# Restore original configuration
./test-local-ollama.sh restore
```

### Option 2: Manual Setup

#### Test with Local Ollama
```bash
# Make sure your local Ollama is running
ollama serve  # if not already running

# Start only the API service with local Ollama configuration
docker compose -f docker-compose.local-ollama.yml up --build api
```

#### Test with Docker Ollama
```bash
# Temporarily disable local configuration
mv .env .env.backup

# Start full Docker stack
docker compose up --build
```

## Files Created for Testing

- **`.env`** - Environment configuration pointing to local Ollama
- **`docker-compose.local-ollama.yml`** - Docker compose without Ollama services
- **`test-local-ollama.sh`** - Helper script for easy switching
- **`LOCAL_OLLAMA_TESTING.md`** - This documentation

## Configuration Details

### Local Ollama Configuration
- **Ollama URL**: `http://localhost:11434`
- **Network**: Uses `network_mode: host` for Linux compatibility
- **Dependencies**: Removes Docker Ollama service dependencies

### Performance Benefits
- **No Docker overhead** for Ollama
- **Direct host access** to your local Ollama instance
- **Faster startup** - no need to initialize Ollama container
- **Resource efficiency** - saves 6-8GB Docker memory allocation

## Prerequisites

1. **Local Ollama installed and running**:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Start Ollama if needed
   ollama serve
   ```

2. **Required models available locally**:
   ```bash
   # Pull required model if not available
   ollama pull mistral:latest
   ```

## Testing Your Application

1. **Start with local Ollama**:
   ```bash
   ./test-local-ollama.sh local
   ```

2. **Test your API endpoints** (in another terminal):
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Test generation endpoint (adjust as needed)
   curl -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Test prompt"}'
   ```

3. **Compare with Docker Ollama**:
   ```bash
   # Stop local test
   Ctrl+C
   
   # Test with Docker Ollama
   ./test-local-ollama.sh docker
   ```

4. **Restore original setup**:
   ```bash
   ./test-local-ollama.sh restore
   ```

## Troubleshooting

### Local Ollama Not Accessible
- Ensure Ollama is running: `ollama serve`
- Check port 11434 is available: `lsof -i :11434`
- Verify models are available: `ollama list`

### Docker Network Issues (Linux Specific)
- **Fixed**: Now uses `network_mode: host` which eliminates Docker network isolation
- **Previous issue**: `host.docker.internal` doesn't work on Linux systems
- **Solution**: Direct localhost access with host networking mode

### Environment Variable Issues
- Ensure the `.env` file exists and contains `OLLAMA_URL=http://localhost:11434`
- The docker compose file now includes both `env_file` and explicit `environment` settings
- Check container logs: `docker compose -f docker-compose.local-ollama.yml logs api`

### Permission Issues
- Make script executable: `chmod +x test-local-ollama.sh`

### Connection Issues
- Test local Ollama directly: `curl http://localhost:11434/api/tags`
- With host networking, the container can directly access localhost services
- If still having issues, ensure no firewall is blocking port 11434

### Linux-Specific Notes
- **Host networking**: Container shares the host's network stack
- **Port conflicts**: Ensure port 8000 is not already in use on your system
- **Firewall**: Some Linux distributions may require firewall configuration for localhost access

## Cleanup

To completely remove the testing setup:

```bash
# Remove testing files
rm .env docker-compose.local-ollama.yml test-local-ollama.sh LOCAL_OLLAMA_TESTING.md

# Remove any backup files
rm .env.backup 2>/dev/null || true
```

## Performance Comparison

When testing, pay attention to:
- **Startup time** - Local should be much faster
- **Response latency** - Local should have lower latency
- **Memory usage** - Local uses less Docker memory
- **CPU utilization** - May vary depending on your setup

The local Ollama setup should provide noticeably better performance, especially for development and testing workflows.
