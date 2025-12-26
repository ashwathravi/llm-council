#!/bin/bash
# Startup script for Codex environment
set -e

echo "Initializing Codex environment for LLM Council..."

# 1. Ensure UV is installed (Package Manager)
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Sync Python Environment
echo "Syncing Python dependencies..."
rm -f uv.lock  # <--- Add this line to remove the bad lockfile
uv sync

# 3. Setup Frontend
if [ -d "frontend" ]; then
    echo "Setting up frontend..."
    cd frontend
    # Check if npm is installed
    if command -v npm &> /dev/null; then
        npm install
    else
        echo "Warning: npm not found. Skipping frontend setup."
    fi
    cd ..
fi

# 4. Environment Variables
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    # You might want to copy a sample env or just warn
    echo "# OPENROUTER_API_KEY=your_key_here" > .env
    echo "Created .env file. Please populate it with your API keys."
fi

echo "✓ Codex environment setup complete!"
