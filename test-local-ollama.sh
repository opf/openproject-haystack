#!/bin/bash

# Test script for comparing local vs Docker Ollama performance
# This script helps you easily switch between configurations and test performance

set -e

echo "🚀 Ollama Performance Testing Script"
echo "===================================="

# Function to check if local Ollama is running
check_local_ollama() {
    echo "🔍 Checking if local Ollama is running..."
    if curl -s -f "http://localhost:11434/api/tags" > /dev/null 2>&1; then
        echo "✅ Local Ollama is running on port 11434"
        return 0
    else
        echo "❌ Local Ollama is not running or not accessible on port 11434"
        return 1
    fi
}

# Function to test with local Ollama
test_local_ollama() {
    echo ""
    echo "🏠 Testing with LOCAL Ollama"
    echo "----------------------------"
    
    if ! check_local_ollama; then
        echo "Please start your local Ollama first with: ollama serve"
        exit 1
    fi
    
    echo "📦 Starting API service with local Ollama configuration..."
    echo "Using docker-compose.local-ollama.yml and .env file"
    echo "Environment variables:"
    echo "  OLLAMA_URL=http://host.docker.internal:11434"
    echo "  OLLAMA_MODEL=mistral:latest"
    
    # Stop any running containers first
    docker compose down 2>/dev/null || true
    docker compose -f docker-compose.local-ollama.yml down 2>/dev/null || true
    
    # Start with local Ollama configuration
    docker compose -f docker-compose.local-ollama.yml up --build api
}

# Function to test with Docker Ollama
test_docker_ollama() {
    echo ""
    echo "🐳 Testing with DOCKER Ollama"
    echo "-----------------------------"
    
    # Temporarily rename .env to disable local configuration
    if [ -f ".env" ]; then
        mv .env .env.backup
        echo "📝 Temporarily disabled .env file (backed up as .env.backup)"
    fi
    
    echo "📦 Starting full Docker stack with Ollama container..."
    
    # Stop any running containers first
    docker compose -f docker-compose.local-ollama.yml down 2>/dev/null || true
    
    # Start with original Docker configuration
    docker compose up --build
}

# Function to restore original configuration
restore_config() {
    echo ""
    echo "🔄 Restoring original configuration"
    echo "----------------------------------"
    
    # Stop all containers
    docker compose down 2>/dev/null || true
    docker compose -f docker-compose.local-ollama.yml down 2>/dev/null || true
    
    # Restore .env if it was backed up
    if [ -f ".env.backup" ]; then
        mv .env.backup .env
        echo "✅ Restored .env file from backup"
    fi
    
    echo "✅ Configuration restored to original state"
}

# Function to show usage
show_usage() {
    echo ""
    echo "Usage: $0 [local|docker|restore]"
    echo ""
    echo "Commands:"
    echo "  local   - Test with local Ollama instance"
    echo "  docker  - Test with Docker Ollama container"
    echo "  restore - Restore original configuration"
    echo ""
    echo "Examples:"
    echo "  $0 local    # Test local Ollama performance"
    echo "  $0 docker   # Test Docker Ollama performance"
    echo "  $0 restore  # Clean up and restore original setup"
}

# Main script logic
case "${1:-}" in
    "local")
        test_local_ollama
        ;;
    "docker")
        test_docker_ollama
        ;;
    "restore")
        restore_config
        ;;
    *)
        show_usage
        ;;
esac
