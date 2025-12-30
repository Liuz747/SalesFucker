# MAS - Marketing Agent System

<div align="center">

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://langchain-ai.github.io/langgraph/)

</div>

## 📖 Overview

MAS (Marketing Agent System) is a production-grade multi-agent marketing assistant platform focused on intelligent solutions for digital marketing scenarios. Built on FastAPI and LangGraph, the system implements a layered "Thread → Workflow → Agent" architecture, providing comprehensive conversation management, intelligent dialogue, content generation, sentiment analysis, and more.

The platform integrates mainstream storage solutions including Redis, Elasticsearch, and Milvus, supports full-chain observability with Langfuse, and provides complete Docker Compose environments for both development and deployment, enabling rapid integration into existing business systems.

## ✨ Key Features

### 🤖 Multi-Agent Workflows
- Modular agent architecture built on LangGraph
- Built-in specialized modules for chat, compliance checking, product recommendations, sentiment analysis, and memory management
- Flexible workflow orchestration capabilities located in `api/core/agents` and `api/core/graphs`

### 🏗️ Clean Service Architecture
- **Controllers**: RESTful API routing layer
- **Services**: Business logic orchestration layer
- **Models/Schemas**: Data modeling and validation layer
- Follows Domain-Driven Design (DDD) best practices

### 🔌 Flexible LLM Integration
- Lightweight multi-LLM runtime system (`api/infra/runtimes`)
- Built-in support for OpenAI, Anthropic, and Gemini
- Easy model extension via `api/data/models.yaml`
- Support for custom model adapters

### 💾 Multi-Tier Memory System
- **Short-term Storage**: High-performance conversation caching with Redis ConversationStore
- **Long-term Indexing**: Elasticsearch integration for full-text search
- **Vector Retrieval**: Milvus vector database for semantic similarity search

### 🔍 Complete Observability
- Integrated Langfuse tracing platform
- Full call chain monitoring
- Real-time performance metrics and analytics

### 🐳 Out-of-the-Box Deployment
- Development and production Compose configurations in `docker/` directory
- One-command deployment of complete technology stack
- Support for horizontal scaling and high-availability deployment

### 🖥️ Modern Frontend Interface
- Next.js operational platform in `web/` directory
- Visual management panels and data dashboards
- Detailed documentation in subdirectories

## 📂 Project Structure

```text
mas-v0.2/
├── api/                      # FastAPI backend service and LangGraph agent workflows
│   ├── controllers/          # API routing layer
│   ├── core/                 # Core business capability modules
│   │   ├── agents/           # Agent implementations
│   │   ├── graphs/           # LangGraph workflow definitions
│   │   ├── memory/           # Memory management system
│   │   └── prompts/          # Prompt engineering
│   ├── infra/                # Infrastructure layer
│   │   ├── database/         # Database adapters
│   │   ├── cache/            # Cache adapters
│   │   └── runtimes/         # LLM runtime manager
│   ├── services/             # Business service orchestration layer
│   ├── models/               # Data models
│   ├── schemas/              # API request/response models
│   ├── scripts/              # Utility scripts (database migrations, initialization, etc.)
│   └── tests/                 # Test suite (Pytest)
├── docker/                   # Docker orchestration configuration
│   ├── docker-compose.dev.yml    # Development environment config
│   └── docker-compose.yml        # Production environment config
├── docs/                     # Project documentation
│   ├── deployment.md         # Deployment guide
│   ├── LLM_usage.md    # Multi-LLM configuration guide
│   └── database_migrations.md # Database migration guide
├── web/                      # Next.js frontend application
└── README.md                 # Main README (Chinese)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Compose
- At least one valid LLM API Key (OpenAI, Anthropic, Gemini, or OpenRouter)

### Installation Steps

#### 1. Clone the Repository

```bash
git clone <repo-url>
cd mas-v0.2
```

#### 2. Start Infrastructure Services

```bash
cd docker
docker compose -f docker-compose.dev.yml up -d
```

#### 3. Configure Environment Variables

Copy and edit the environment configuration file:

```bash
cd ../api
cp .env.example .env
```

#### 4. Initialize Database

```bash
uv run scripts/database.py
```

#### 5. Start API Service

```bash
# Development mode (hot reload)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the shortcut
uv run main.py
```

#### 6. Verify Deployment

- **Health Check**: Visit http://localhost:8000/health
- **API Documentation**: Visit http://localhost:8000/docs

### Frontend Deployment

The frontend application is located in the `web/` directory. For detailed instructions, see:
- `web/README.md` - Frontend project documentation
- `web/REVIEW.md` - Technical architecture documentation

## 🧪 Development & Testing
```bash
# Run all tests
cd api
uv run pytest

# Run specific test file
uv run pytest tests/agents/test_agents.py

# Generate coverage report
uv run pytest --cov=. --cov-report=term-missing
```


## 🗄️ Database Management

### Database Migrations

This project uses Alembic for database version management. The `api/scripts/database.py` script wraps common operations:

```bash
cd api

# Apply all pending migrations
uv run scripts/database.py

# Create new migration file (auto-detect model changes)
uv run scripts/database.py revision "add user preferences table"

# Rollback to previous version
uv run scripts/database.py downgrade -1

# Rollback to specific version
uv run scripts/database.py downgrade <revision_id>
```

> For more details, see [`database_migrations.md`](database_migrations.md)


## 📡 API Documentation

### General Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check, returns system status |
| `/docs` | GET | Swagger UI interactive API documentation |

### Authentication Module (`/v1/auth`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/auth/token` | POST | Issue service-to-service JWT via `X-App-Key` |
| `/v1/auth/verify` | GET | Verify JWT and return parsed information |
| `/v1/auth/test` | GET | Permission verification example |

### Conversation Threads (`/v1/threads`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/threads` | POST | Create new conversation thread |
| `/v1/threads/{thread_id}` | GET | Query thread metadata |
| `/v1/threads/{thread_id}/info` | POST | Update thread metadata |
| `/v1/threads/{thread_id}/runs/wait` | POST | Synchronously run workflow and wait for result |
| `/v1/threads/{thread_id}/runs/async` | POST | Asynchronously trigger workflow, background processing |
| `/v1/threads/{thread_id}/runs/{run_id}/status` | GET | Query background run status |

### Direct LLM Access (`/v1/messages`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/messages` | POST | Send message directly and get response |
| `/v1/messages/responses` | POST | Call OpenAI Responses API |
| `/v1/messages/responses/structured` | POST | Structured output (based on Pydantic models) |

### Assistant Management (`/v1/assistants`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/assistants` | POST | Create intelligent assistant |
| `/v1/assistants/{assistant_id}` | GET | View assistant details |
| `/v1/assistants/{assistant_id}/info` | POST | Update assistant configuration |
| `/v1/assistants/{assistant_id}` | DELETE | Delete assistant |

### Marketing Specialist (`/v1/marketing`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/marketing/plans` | POST | Marketing specialist intelligent conversation |

### Social Media Tools (`/v1/social-media`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/social-media/comment` | POST | Generate comment content |
| `/v1/social-media/reply` | POST | Generate interactive reply |
| `/v1/social-media/keywords` | POST | Extract topic keywords |
| `/v1/social-media/chat` | POST | Social media scenario conversation |
| `/v1/social-media/reload-prompt` | POST | Reload social media scenario prompt |

### Tenant Management (`/v1/tenants`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/tenants/sync` | POST | Sync tenant information from business system |
| `/v1/tenants/{tenant_id}` | GET | Query tenant status |
| `/v1/tenants/{tenant_id}` | POST | Update tenant configuration |
| `/v1/tenants/{tenant_id}` | DELETE | Delete tenant |

> For complete request/response parameter details, visit http://localhost:8000/docs


## 📚 Technical Documentation

| Document | Description |
|----------|-------------|
| [`deployment.md`](deployment.md) | Deployment guide (development/production environments) |
| [`database_migrations.md`](database_migrations.md) | Database migration best practices |
| [`LLM_usage.md`](LLM_usage.md) | Multi-LLM runtime configuration guide |
| [`message-storage-strategy.md`](message-storage-strategy.md) | Conversation storage strategy documentation |


## 🤝 Support

- **Email**: consumerclone@outlook.com
- **Team**: HuanMu Team

<div align="center">

**Made with ❤️ by HuanMu Team**

</div>