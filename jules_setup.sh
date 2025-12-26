#!/bin/bash
set -e

echo "Starting setup for LLM Council..."

# 1. Install uv (fast Python package manager)
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Ensure uv is in PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# 3. Install Node.js dependencies
if [ -d "frontend" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo "Setup script finished successfully!"
