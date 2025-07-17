#!/bin/bash

# Setup script for Ollama embedding model
# This script pulls the required embedding model for the RAG system

set -e

echo "Setting up Ollama embedding model for RAG system..."

# Configuration
EMBEDDING_MODEL=${EMBEDDING_MODEL:-"nomic-embed-text"}
OLLAMA_URL=${OLLAMA_URL:-"http://localhost:11434"}

echo "Embedding model: $EMBEDDING_MODEL"
echo "Ollama URL: $OLLAMA_URL"

# Check if Ollama is running
echo "Checking Ollama availability..."
if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null; then
    echo "Error: Ollama is not running or not accessible at $OLLAMA_URL"
    echo "Please start Ollama first:"
    echo "  ollama serve"
    exit 1
fi

echo "Ollama is running ✓"

# Check if embedding model is already available
echo "Checking if embedding model '$EMBEDDING_MODEL' is available..."
if ollama list | grep -q "$EMBEDDING_MODEL"; then
    echo "Embedding model '$EMBEDDING_MODEL' is already available ✓"
else
    echo "Pulling embedding model '$EMBEDDING_MODEL'..."
    ollama pull "$EMBEDDING_MODEL"
    echo "Successfully pulled embedding model '$EMBEDDING_MODEL' ✓"
fi

# Test the embedding model
echo "Testing embedding model..."
if ollama run "$EMBEDDING_MODEL" "test" > /dev/null 2>&1; then
    echo "Embedding model test successful ✓"
else
    echo "Warning: Embedding model test failed, but model appears to be installed"
fi

echo ""
echo "Embedding model setup complete!"
echo ""
echo "Available models:"
ollama list

echo ""
echo "You can now start the application with the RAG system enabled."
echo "The embedding model '$EMBEDDING_MODEL' will be used for document embeddings."
