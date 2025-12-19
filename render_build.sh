#!/bin/bash
set -e

# Ensure uv is installed
pip install uv

# Install backend dependencies
echo "Installing backend dependencies..."
uv sync

# Install frontend dependencies and build
echo "Installing frontend dependencies..."
cd frontend
npm install

echo "Building frontend..."
npm run build
cd ..

echo "Build complete."
