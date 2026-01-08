# MAS Deployment Guide

This guide provides comprehensive instructions for deploying the MAS (Marketing Agent System) platform in both development and production environments. The system is built with FastAPI and LangGraph, featuring a multi-agent architecture for intelligent marketing automation.

## Table of Contents

- [System Requirements](#system-requirements)
- [Architecture Overview](#architecture-overview)
- [Local Development Setup](#local-development-setup)
- [Container Deployment](#container-deployment)
- [Testing Environment](#testing-environment)
- [Production Deployment](#production-deployment)
- [Monitoring and Observability](#monitoring-and-observability)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS 11+, or Windows with WSL2
- **Python**: 3.13 or higher
- **Package Manager**: [uv](https://docs.astral.sh/uv/) (recommended) or pip
- **Docker**: 20.10+ with Docker Compose V2
- **Memory**: 8GB RAM minimum (16GB recommended for production)
- **Storage**: 20GB available disk space

### Required Services

- **PostgreSQL**: 14+ (for persistent storage)
- **Redis**: 7.0+ (for caching and session management)
- **Elasticsearch**: 8.0+ (for long-term memory and search)
- **Milvus**: 2.3+ (for vector embeddings and semantic search)

### API Keys

At least one LLM provider API key is required:
- OpenAI (`OPENAI_API_KEY`)
- Anthropic (`ANTHROPIC_API_KEY`)
- Google Gemini (`GOOGLE_API_KEY`)
- DeepSeek (`DEEPSEEK_API_KEY`)
- OpenRouter (`OPENROUTER_API_KEY`)

## Architecture Overview

```
┌─────────────────┐      ┌──────────────────┐
│   Next.js UI    │◄────►│   Nginx Proxy    │
│   (Port 3000)   │      │   (Port 80/443)  │
└─────────────────┘      └──────────┬───────┘
                                    │
                         ┌──────────▼──────────┐
                         │   FastAPI Backend   │
                         │   (Port 8000)       │
                         └──────────┬──────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐      ┌───────────▼──────┐      ┌───────────▼─────────┐
│  PostgreSQL    │      │     Redis        │      │   Elasticsearch     │
│  (Port 5432)   │      │   (Port 6379)    │      │   (Port 9200)       │
└────────────────┘      └──────────────────┘      └─────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   Milvus Vector DB  │
                         │   (Port 19530)      │
                         └─────────────────────┘
```

## Local Development Setup

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd mas

# Navigate to API directory
cd api

# Copy environment template and configure environment variables
cp .env.example .env
```

### Step 2: Start Infrastructure Services

From the project root directory:

```bash
cd mas/docker

# Start core services
docker compose -f docker-compose.dev.yml up -d
```

Verify services are running:
```bash
docker compose -f docker-compose.dev.yml ps
```

### Step 3: Initialize Database

```bash
cd api

# Install dependencies
uv sync

# Run database migrations
uv run scripts/database.py
```

### Step 4: Start the API Server

```bash
# Method 1: Using the main script (recommended)
uv run main.py

# Method 2: Using uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Verify Installation

Access the following endpoints:

- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### Step 6: Frontend Setup (Optional)

```bash
cd web

# Install dependencies
pnpm install

# Start development server
pnpm dev
```

The frontend will be available at http://localhost:3000

## Container Deployment

### Building Images

The project uses Docker Compose for building production container images.

```bash
cd mas/docker

# Build all images
docker compose -f docker-compose.build.yml build

# Build specific service
docker compose -f docker-compose.build.yml build api

# View built images
docker image ls
```

### Tagging and Publishing

```bash
# Set your registry URL
export REGISTRY_URL=registry.example.com/mas

# Tag images
docker tag api:latest ${REGISTRY_URL}/api:latest
docker tag api:latest ${REGISTRY_URL}/api:v1.0.0

# Push to registry
docker push ${REGISTRY_URL}/api:latest
docker push ${REGISTRY_URL}/api:v1.0.0
```

### Image Components

The build process creates the following images:

- **api**: FastAPI backend with all dependencies
- **frontend**: Next.js application (if using web/)
- **langfuse-worker**: Background task worker for async operations

## Testing Environment

### Starting the Test Environment

To start the test environment with all required services:

```bash
cd mas/docker

# Start test environment
docker compose --profile test up -d
```

This command will:
1. Start all base infrastructure services (if not already running)
2. Start the `api-test` service with test-specific configuration
3. Run in detached mode in the background

### Stopping the Test Environment

To stop only the test API service:

```bash
docker compose --profile test down api-test
```

To stop all services including infrastructure:

```bash
docker compose --profile test down
```

### Test-Specific Environment Variables

Configure the following variables in your `.env` file for the test environment:

```env
# Test Database
DB_NAME_TEST=mas_test

# Test Redis Database
REDIS_DB_TEST=1

# Test Elasticsearch Index
ELASTIC_MEMORY_INDEX_TEST=memory_test

# Test Temporal Namespace
TEMPORAL_NAMESPACE_TEST=mas-test
```

## Production Deployment

### Pre-deployment Checklist

- [ ] Review and update all environment variables
- [ ] Configure TLS/SSL certificates
- [ ] Set up persistent volume mounts for data
- [ ] Configure firewall rules and network policies
- [ ] Set up backup strategy
- [ ] Configure monitoring and alerting
- [ ] Review security settings and access controls

### Environment Configuration

Create a production `.env` file with secure values:

```bash
# Copy from template
cp .env.example .env

# Edit with production values
vim .env
```

### Docker Compose Deployment

```bash
cd mas/docker

# Start all services
docker compose up -d

# Verify deployment
docker compose ps

# View logs
docker compose logs api
```

### Service Configuration

The production stack includes:

**Core Services**
- `api`: FastAPI backend API
- `nginx`: Reverse proxy with TLS termination
- `postgres`: PostgreSQL database
- `redis`: Redis cache and session store

**Memory and Search**
- `elasticsearch`: Full-text search and long-term memory
- `milvus-standalone`: Vector database for embeddings

**Observability** (Optional)
- `langfuse-web`: Tracing and monitoring dashboard
- `langfuse-worker`: Background processing for traces
- `clickhouse`: Analytics database for Langfuse
- `minio`: Object storage for artifacts

### Nginx Configuration

Configure TLS certificates for HTTPS:

```bash
# Copy your certificates
cp /path/to/cert.pem docker/nginx/ssl/
cp /path/to/key.pem docker/nginx/ssl/

# Set environment variables
export NGINX_SSL_CERT=/etc/nginx/ssl/cert.pem
export NGINX_SSL_KEY=/etc/nginx/ssl/key.pem
```

## Monitoring and Observability

### Langfuse Integration

Langfuse provides complete observability for LLM interactions and agent workflows.

**Setup**:
1. Ensure Langfuse services are running
2. Configure environment variables in `.env`
3. Access dashboard at http://localhost:3000

**Features**:
- Real-time trace visualization
- Performance metrics and analytics
- Cost tracking per LLM provider
- Error and exception tracking
- Agent workflow visualization

### Database Monitoring

```bash
# PostgreSQL connection stats
docker compose exec postgres psql -U postgres -d mas -c "SELECT * FROM pg_stat_activity;"

# Database size
docker compose exec postgres psql -U postgres -d mas -c "SELECT pg_size_pretty(pg_database_size('mas'));"
```

### Redis Monitoring

```bash
# Redis info
docker compose exec redis redis-cli info

# Monitor commands in real-time
docker compose exec redis redis-cli monitor

# Check memory usage
docker compose exec redis redis-cli info memory
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U postgres mas > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose exec -T postgres psql -U postgres mas < backup_20231216_120000.sql
```

### Redis Backup

```bash
# Trigger save
docker compose exec redis redis-cli BGSAVE

# Copy RDB file
docker compose cp redis:/data/dump.rdb ./backup/redis_$(date +%Y%m%d).rdb
```

### Debug Mode

Enable detailed logging for troubleshooting:

```env
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
SQLALCHEMY_ECHO=true
```

Restart services:
```bash
docker compose restart api
```

### Version Upgrades

Upgrade process:
```bash
# Stop services
docker compose down

# Pull new version
git fetch && git checkout 0.2.2

# Remove old image
docker rmi ${REGISTRY_URL}/api:latest

# Start services with new version
docker compose up -d
```
