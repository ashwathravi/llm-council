# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# Build production assets
# Note: VITE_GOOGLE_CLIENT_ID should be passed as build generic argument if using .env, 
# but for now we hardcoded it in main.jsx so it's fine.
RUN npm run build

# Stage 2: Setup Backend
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies (none needed for pure python/fastapi usually)
# If using uv, we can install it, but standard pip is fine for deployment container
# to keep image size small if we just export requirements.
# However, we are using `uv` in development. Let's use `uv` in Docker for consistency 
# OR just export requirements.txt. Using pip is more standard for simple deploys.
# Let's assume requirements.txt or just install directly.
# We don't have a requirements.txt yet! We should create one.

# Let's genericize the install:
COPY pyproject.toml .
# We can use uv to install
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install dependencies into system python
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (Render sets PORT env var, we'll use CMD to bind to it)
ENV PORT=8000
EXPOSE 8000

# Command to run the application
# We use shell form to expand $PORT
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT
