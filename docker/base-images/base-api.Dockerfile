FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment variables for uv
ENV UV_SYSTEM_PYTHON=1

# Copy dependency files and install all Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

# This base image now includes all Python dependencies
# Application images only need to copy code