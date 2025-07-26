# MAS Cosmetic Agent System

A sophisticated multi-agent system using LangGraph to revolutionize digital marketing in the cosmetic industry by replacing traditional customer sales interactions with AI agents.

## Architecture Overview

The system consists of 9 specialized agents working together:

1. **Compliance Review Agent** - Legal/regulatory validation
2. **Sentiment Analysis Agent** - Customer emotional state assessment  
3. **Intent Analysis Agent** - Customer goal identification
4. **Sales Agent** - Primary conversation management
5. **Product Expert Agent** - RAG-powered recommendations
6. **Memory Agent** - Context persistence and retrieval
7. **Market Strategy Cluster** - Specialized approaches (Premium, Budget, Youth, Mature)
8. **Proactive Agent** - Trigger-based customer outreach
9. **AI Suggestion Agent** - Human-in-loop assistance

## Quick Start

### Prerequisites

- Python 3.11+
- uv package manager
- Docker and Docker Compose
- OpenAI API key

### Setup

1. **Initialize the development environment:**
   ```bash
   ./scripts/setup.sh
   ```

2. **Update environment variables:**
   Edit `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

3. **Start the development services:**
   ```bash
   ./scripts/docker-dev.sh up
   ```

4. **Run the application:**
   ```bash
   uv run uvicorn main:app --reload
   ```

### Manual Setup

If you prefer manual setup:

1. **Install dependencies:**
   ```bash
   uv sync --all-extras
   ```

2. **Start infrastructure services:**
   ```bash
   docker compose -f docker/docker-compose.yml up -d elasticsearch redis
   ```

3. **Run the API server:**
   ```bash
   uv run python main.py
   ```

## Development

### Project Structure

```
mas-v0.2/
├── main.py                  # FastAPI application entry point
├── src/
│   ├── agents/              # LangGraph agent implementations
│   ├── memory/              # Elasticsearch integration
│   ├── rag/                 # Retrieval-augmented generation
│   ├── multimodal/          # Voice and image processing
│   ├── api/                 # API route handlers
│   └── utils/               # Shared utilities
├── config/                  # Configuration files
├── docker/                  # Docker configurations
├── tests/                   # Test suites
├── docs/                    # Documentation
└── scripts/                 # Development scripts
```

### Available Scripts

- `./scripts/setup.sh` - Initialize development environment
- `./scripts/docker-dev.sh up` - Start all services
- `./scripts/docker-dev.sh down` - Stop all services
- `./scripts/docker-dev.sh logs` - View service logs
- `./scripts/docker-dev.sh status` - Check service status

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy src/

# Linting
uv run flake8 src/
```

## API Endpoints

Once running, the API will be available at:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root**: http://localhost:8000/

## Services

- **Elasticsearch**: http://localhost:9200
- **Redis**: localhost:6379
- **API Server**: http://localhost:8000

## Multi-Tenant Support

The system is designed for multi-tenant operation, allowing multiple cosmetic brands to use isolated instances of the agent system with:

- Separate customer data
- Brand-specific agent personalities
- Isolated product catalogs
- Tenant-specific analytics

## Next Steps

1. Implement agent communication framework
2. Build individual agent capabilities
3. Add multi-modal processing
4. Integrate with external systems
5. Deploy to production environment

## Contributing

1. Follow the code style guidelines (Black, isort)
2. Write tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

MIT License - see LICENSE file for details. 