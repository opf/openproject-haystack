#!/bin/bash

# Ollama Model Initialization Script
# This script pulls required models for the Haystack application

set -e  # Exit on any error

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
MODELS_TO_PULL="${MODELS_TO_PULL:-mistral:latest}"
MAX_RETRIES=30
RETRY_DELAY=10

echo "🚀 Starting Ollama model initialization..."
echo "📍 Ollama host: $OLLAMA_HOST"
echo "📦 Models to pull: $MODELS_TO_PULL"

# Function to check if Ollama is ready
check_ollama_ready() {
    curl -s -f "$OLLAMA_HOST/api/tags" > /dev/null 2>&1
}

# Function to check if a model exists
check_model_exists() {
    local model_name="$1"
    curl -s "$OLLAMA_HOST/api/tags" | grep -q "\"name\":\"$model_name\""
}

# Function to pull a model
pull_model() {
    local model_name="$1"
    echo "📥 Pulling model: $model_name"
    
    # Use curl to pull the model via Ollama API
    curl -X POST "$OLLAMA_HOST/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$model_name\"}" \
        --max-time 1800 \
        --retry 3 \
        --retry-delay 5
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pulled model: $model_name"
        return 0
    else
        echo "❌ Failed to pull model: $model_name"
        return 1
    fi
}

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
retry_count=0
while ! check_ollama_ready; do
    if [ $retry_count -ge $MAX_RETRIES ]; then
        echo "❌ Timeout waiting for Ollama to be ready after $((MAX_RETRIES * RETRY_DELAY)) seconds"
        exit 1
    fi
    
    echo "⏳ Ollama not ready yet, waiting... (attempt $((retry_count + 1))/$MAX_RETRIES)"
    sleep $RETRY_DELAY
    retry_count=$((retry_count + 1))
done

echo "✅ Ollama is ready!"

# Pull each required model
MODEL_ARRAY=$(echo "$MODELS_TO_PULL" | tr ',' ' ')
for model in $MODEL_ARRAY; do
    # Trim whitespace
    model=$(echo "$model" | xargs)
    
    if [ -z "$model" ]; then
        continue
    fi
    
    echo "🔍 Checking if model exists: $model"
    if check_model_exists "$model"; then
        echo "✅ Model already exists: $model"
    else
        echo "📥 Model not found, pulling: $model"
        if ! pull_model "$model"; then
            echo "❌ Failed to pull required model: $model"
            exit 1
        fi
    fi
done

# Final verification
echo "🔍 Verifying all models are available..."
for model in $MODEL_ARRAY; do
    model=$(echo "$model" | xargs)
    if [ -z "$model" ]; then
        continue
    fi
    
    if check_model_exists "$model"; then
        echo "✅ Verified model: $model"
    else
        echo "❌ Model verification failed: $model"
        exit 1
    fi
done

echo "🎉 All models successfully initialized!"
echo "📋 Available models:"
curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | sort

echo "✅ Model initialization complete!"
