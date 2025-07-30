#!/bin/bash

# Fix CUDA Installation Issues
# This script handles common CUDA download/installation problems

set -e

echo "🔧 CUDA Installation Fix Script"
echo "==============================="
echo ""

# Check current directory and disk space
echo "1️⃣ Checking disk space..."
df -h .
echo ""

# Remove any partial/corrupted CUDA downloads
echo "2️⃣ Cleaning up any previous CUDA downloads..."
if [ -f "cuda_12.1.1_530.30.02_linux.run" ]; then
    echo "Found existing CUDA installer, removing..."
    rm -f cuda_12.1.1_530.30.02_linux.run
fi

# Check if CUDA is already installed
echo "3️⃣ Checking if CUDA is already available..."
if command -v nvcc &> /dev/null; then
    echo "✅ CUDA is already installed:"
    nvcc --version
    echo ""
    echo "Skipping CUDA installation and continuing with vLLM setup..."
    SKIP_CUDA=true
else
    echo "❌ CUDA not found, will need to install"
    SKIP_CUDA=false
fi
echo ""

if [ "$SKIP_CUDA" = false ]; then
    # Try to install CUDA via package manager (easier and more reliable)
    echo "4️⃣ Attempting CUDA installation via package manager..."
    
    # Add NVIDIA package repository
    if ! dpkg -l | grep -q cuda-keyring; then
        echo "Adding NVIDIA CUDA repository..."
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb
        sudo dpkg -i cuda-keyring_1.0-1_all.deb
        sudo apt-get update
        rm -f cuda-keyring_1.0-1_all.deb
    fi
    
    # Install CUDA toolkit
    echo "Installing CUDA toolkit..."
    sudo apt-get install -y cuda-toolkit-12-1
    
    # Add to PATH
    echo 'export PATH=/usr/local/cuda-12.1/bin:$PATH' >> ~/.bashrc
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
    export PATH=/usr/local/cuda-12.1/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH
    
    echo "✅ CUDA installation completed"
else
    echo "✅ Using existing CUDA installation"
fi

echo ""
echo "5️⃣ Verifying CUDA installation..."
if command -v nvcc &> /dev/null; then
    nvcc --version
    echo "✅ CUDA is working properly"
else
    echo "❌ CUDA installation may have failed"
    echo "You may need to restart your terminal or run: source ~/.bashrc"
fi

echo ""
echo "🎉 CUDA fix complete! You can now continue with:"
echo "    ./scripts/install-native-vllm.sh"
