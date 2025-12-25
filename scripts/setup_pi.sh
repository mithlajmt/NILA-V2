#!/bin/bash

echo "🚀 Setting up NILA on Raspberry Pi..."

# 1. Update System
echo "📦 Updating system packages..."
sudo apt-get update

# 2. Install Build Dependencies (Critical for wheels)
echo "🛠️ Installing build essentials..."
sudo apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    libatlas-base-dev \
    python3-dev \
    libasound2-dev \
    portaudio19-dev

# 3. Upgrade Python Build Tools
echo "🐍 Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

# 4. Install Requirements with extra verbosity if it fails
echo "📥 Installing Python requirements..."
pip install -r requirements.txt || {
    echo "⚠️ Simple install failed. Trying to force binary wheels where possible..."
    pip install -r requirements.txt --prefer-binary
}

echo "✅ Setup Complete! Try running: python main.py"
