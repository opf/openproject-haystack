#!/bin/bash

# Update Docker Compose for Native vLLM Setup
# This script modifies the docker-compose.yml to work with native vLLM

set -e

echo "🔧 Updating Docker Compose for Native vLLM"
echo "==========================================="
echo ""

# Backup current docker-compose.yml
echo "1️⃣ Creating backup of current docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup created"
echo ""

# Create new docker-compose.yml without vLLM container
echo "2️⃣ Creating updated docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
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
      - LOG_LEVEL=INFO
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      # Native vLLM configuration
      - VLLM_URL=http://host.docker.internal:8001
      - VLLM_MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
      - USE_VLLM_DEFAULT=true
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - haystack-internal
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    # Wait for native vLLM service to be available
    depends_on:
      - wait-for-vllm

  wait-for-vllm:
    image: curlimages/curl:latest
    command: >
      sh -c "
        echo 'Waiting for native vLLM service at localhost:8001...'
        until curl -f http://host.docker.internal:8001/health; do
          echo 'vLLM not ready yet, waiting 5 seconds...'
          sleep 5
        done
        echo 'Native vLLM service is ready!'
      "
    networks:
      - haystack-internal

networks:
  haystack-internal:
    driver: bridge
EOF

echo "✅ Updated docker-compose.yml for native vLLM"
echo ""

# Update .env file if it exists
if [ -f ".env" ]; then
    echo "3️⃣ Updating .env file..."
    
    # Backup .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    
    # Update or add vLLM settings
    if grep -q "VLLM_URL" .env; then
        sed -i 's|VLLM_URL=.*|VLLM_URL=http://localhost:8001|' .env
    else
        echo "VLLM_URL=http://localhost:8001" >> .env
    fi
    
    if grep -q "USE_VLLM_DEFAULT" .env; then
        sed -i 's|USE_VLLM_DEFAULT=.*|USE_VLLM_DEFAULT=true|' .env
    else
        echo "USE_VLLM_DEFAULT=true" >> .env
    fi
    
    echo "✅ Updated .env file"
else
    echo "3️⃣ Creating .env file with native vLLM settings..."
    cat > .env << 'EOF'
# Native vLLM Configuration
VLLM_URL=http://localhost:8001
VLLM_MODEL=mistral-community/Mixtral-8x22B-v0.1-AWQ
USE_VLLM_DEFAULT=true

# API Configuration
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
EOF
    echo "✅ Created .env file"
fi
echo ""

# Create a docker-compose override for development
echo "4️⃣ Creating docker-compose.override.yml for development..."
cat > docker-compose.override.yml << 'EOF'
# Development overrides for native vLLM setup
services:
  api:
    environment:
      # Use localhost for development (when running outside Docker)
      - VLLM_URL=http://localhost:8001
    # Enable host networking for easier local development
    network_mode: host
    ports: []  # Disable port mapping when using host networking

  wait-for-vllm:
    command: >
      sh -c "
        echo 'Waiting for native vLLM service at localhost:8001...'
        until curl -f http://localhost:8001/health; do
          echo 'vLLM not ready yet, waiting 5 seconds...'
          sleep 5
        done
        echo 'Native vLLM service is ready!'
      "
EOF

echo "✅ Created docker-compose.override.yml"
echo ""

# Create systemd dependency service to ensure proper startup order
echo "5️⃣ Creating Docker service dependency..."
if systemctl list-units --type=service | grep -q docker; then
    sudo tee /etc/systemd/system/docker-api.service > /dev/null << 'EOF'
[Unit]
Description=Docker API Service (depends on vLLM)
After=docker.service vllm-mixtral.service
Requires=docker.service vllm-mixtral.service
BindsTo=vllm-mixtral.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/openproject-haystack
ExecStart=/usr/bin/docker compose up -d api
ExecStop=/usr/bin/docker compose stop api
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable docker-api.service
    echo "✅ Created Docker API service with vLLM dependency"
else
    echo "⚠️  Docker service not found, skipping systemd integration"
fi
echo ""

# Create monitoring script
echo "6️⃣ Creating monitoring script..."
cat > scripts/monitor-native-vllm.sh << 'EOF'
#!/bin/bash

# Monitor Native vLLM and API Services
echo "🔍 Native vLLM + Docker API Monitoring"
echo "======================================"
echo ""

# Check vLLM service status
echo "1️⃣ Native vLLM Service Status:"
if systemctl is-active --quiet vllm-mixtral; then
    echo "  ✅ vllm-mixtral.service: ACTIVE"
    echo "  📊 Memory usage:"
    ps -p $(pgrep -f "vllm.entrypoints.openai.api_server") -o pid,ppid,cmd,pmem,rss --no-headers 2>/dev/null || echo "  ⚠️  Process not found"
else
    echo "  ❌ vllm-mixtral.service: INACTIVE"
fi
echo ""

# Check GPU usage
echo "2️⃣ GPU Usage:"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
else
    echo "  ❌ nvidia-smi not available"
fi
echo ""

# Check vLLM health endpoint
echo "3️⃣ vLLM Health Check:"
if curl -s -f http://localhost:8001/health > /dev/null; then
    echo "  ✅ http://localhost:8001/health: OK"
    echo "  📈 Response time:"
    curl -s -w "  Time: %{time_total}s\n" -o /dev/null http://localhost:8001/health
else
    echo "  ❌ http://localhost:8001/health: FAILED"
fi
echo ""

# Check Docker API service
echo "4️⃣ Docker API Service Status:"
if docker compose ps api | grep -q "running"; then
    echo "  ✅ API container: RUNNING"
    echo "  🔗 Health check:"
    if curl -s -f http://localhost:8000/health > /dev/null; then
        echo "    ✅ http://localhost:8000/health: OK"
    else
        echo "    ❌ http://localhost:8000/health: FAILED"
    fi
else
    echo "  ❌ API container: NOT RUNNING"
fi
echo ""

# Show recent logs if there are issues
echo "5️⃣ Recent Logs (last 10 lines):"
echo "vLLM service logs:"
journalctl -u vllm-mixtral -n 10 --no-pager -q
echo ""
echo "API container logs:"
docker compose logs --tail=10 api 2>/dev/null || echo "API container not running"
echo ""

echo "✨ Monitoring complete!"
EOF

chmod +x scripts/monitor-native-vllm.sh
echo "✅ Created monitoring script"
echo ""

# Create quick test script
echo "7️⃣ Creating test script..."
cat > scripts/test-native-vllm.sh << 'EOF'
#!/bin/bash

# Test Native vLLM + API Setup
echo "🧪 Testing Native vLLM + API Setup"
echo "=================================="
echo ""

# Test vLLM directly
echo "1️⃣ Testing vLLM direct API..."
echo "Request: Hello from native vLLM!"
curl -X POST http://localhost:8001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-community/Mixtral-8x22B-v0.1-AWQ",
    "prompt": "Hello! How are you?",
    "max_tokens": 50,
    "temperature": 0.7
  }' | jq '.choices[0].text' 2>/dev/null || echo "❌ Direct vLLM test failed"
echo ""

# Test through API service
echo "2️⃣ Testing through API service..."
echo "Request: Hello through API service!"
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "test-model",
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "max_tokens": 30
  }' | jq '.choices[0].message.content' 2>/dev/null || echo "❌ API service test failed"
echo ""

echo "✨ Testing complete!"
EOF

chmod +x scripts/test-native-vllm.sh
echo "✅ Created test script"
echo ""

# Summary
echo "🎉 Docker Compose Update Complete!"
echo "=================================="
echo ""
echo "📋 Changes Made:"
echo "  • Updated docker-compose.yml (backup created)"
echo "  • Updated/created .env file (backup created if existed)"
echo "  • Created docker-compose.override.yml for development"
echo "  • Created systemd service for automatic startup"
echo "  • Created monitoring script: scripts/monitor-native-vllm.sh"
echo "  • Created test script: scripts/test-native-vllm.sh"
echo ""
echo "🔄 Next Steps:"
echo "  1. Install native vLLM: ./scripts/install-native-vllm.sh"
echo "  2. Start vLLM service: sudo systemctl start vllm-mixtral"
echo "  3. Start API service: docker compose up -d api"
echo "  4. Test the setup: ./scripts/test-native-vllm.sh"
echo "  5. Monitor services: ./scripts/monitor-native-vllm.sh"
echo ""
echo "🌐 Service Endpoints:"
echo "  • Native vLLM: http://localhost:8001"
echo "  • API Service: http://localhost:8000"
echo ""
echo "📊 Service Management:"
echo "  • vLLM: sudo systemctl {start|stop|status} vllm-mixtral"
echo "  • API: docker compose {up|down|restart} api"
echo ""
echo "✨ Configuration update complete!"
