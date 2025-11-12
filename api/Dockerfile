FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Copy and set permissions for entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY scripts/database.py /app/scripts/database.py

# Expose port
EXPOSE 8000

# Run the application via entrypoint script
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"] 