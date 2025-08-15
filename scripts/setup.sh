#!/bin/bash

# MAS Development Environment Setup Script

set -e

echo "🚀 Setting up MAS Cosmetic Agent Development Environment..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Install dependencies
echo "📦 Installing dependencies..."
uv sync --all-extras

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOL
# API Configuration
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# Database URLs (for Docker Compose)
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379

# AI Model Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo

EOL
    echo "⚠️  Please update the OPENAI_API_KEY in .env file"
fi

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
uv run pre-commit install

# Create necessary directories
echo "📁 Creating additional directories..."
mkdir -p logs
mkdir -p data/uploads
mkdir -p data/vector_store

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your OPENAI_API_KEY in .env file"
echo "2. Start services: docker compose -f docker/docker-compose.yml up -d"
echo "3. Run tests: uv run pytest"
echo "4. Start development server: uv run uvicorn main:app --reload" 