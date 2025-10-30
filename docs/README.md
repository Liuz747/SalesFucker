# MAS Intelligent Marketing Assistant

MAS (Marketing Agent System) is a multi-agent marketing assistant. The backend combines FastAPI with LangGraph to orchestrate conversations through a "Thread → Workflow → Agent" pipeline. Supporting services such as Redis, Elasticsearch, Milvus, and Langfuse can be enabled via Docker Compose, and the repository also ships with a Next.js operator console.

## Highlights

- LangGraph workflows with specialised agents for chat, compliance, product expertise, sentiment, memory, and proactive actions (`api/core/agents`, `api/core/workflows`)
- Layered FastAPI service: routers live in `controllers`, business logic in `services`, and data contracts in `models`/`schemas`
- Lightweight multi-LLM runtime (`api/infra/runtimes`) with OpenAI & Anthropic out of the box and pluggable models through `data/models.yaml`
- Conversation memory backed by Redis short-term storage with optional Elasticsearch indices and Milvus vector recall
- Docker Compose definitions under `docker/` for local infrastructure and Langfuse observability
- Next.js frontend and worker apps under `web/` for dashboards and review tooling

## Repository Layout

```text
mas-v0.2/
├── api/                  # FastAPI backend and LangGraph workflows
│   ├── controllers/      # v1 REST routers (auth, threads, assistants, prompts, social, ...)
│   ├── core/             # Agents, memory, workflows, prompt management
│   ├── infra/            # DB/cache/LLM/observability integrations
│   ├── services/         # Business services (assistants, threads, orchestrator)
│   ├── models/           # Pydantic and SQLAlchemy models
│   ├── scripts/          # Setup and Alembic helpers
│   └── test/             # Pytest suites
├── docker/               # Development & production Compose files, Nginx config
├── docs/                 # Project documentation (deployment, migrations, LLM, memory)
├── web/                  # Next.js frontend + Langfuse web assets
└── README.md             # Chinese overview
```

## Backend Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose (optional, for local dependencies)
- At least one valid LLM API key (OpenAI, Anthropic, Gemini, or OpenRouter)

### Steps
1. Clone the repository and move into the backend directory:
   ```bash
   git clone <repo-url>
   cd mas-v0.2/api
   ```
2. Bootstrap the environment (installs dependencies, prepares `.env`, creates data folders):
   ```bash
   ./scripts/setup.sh
   ```
3. Edit `.env` with your API keys and infrastructure endpoints (PostgreSQL/Redis/Elasticsearch/Milvus as needed).
4. Start local infrastructure if required:
   ```bash
   docker compose -f ../docker/docker-compose.dev.yml up -d postgres redis
   # Add langfuse-web, langfuse-worker, clickhouse, minio when observability is needed
   ```
5. Launch the API:
   ```bash
   uv run uvicorn main:app --reload
   # or uv run python main.py
   ```
6. Visit `http://localhost:8000/docs` for the interactive API reference.

Frontend and Langfuse assets live under `web/`; consult that directory for build and deployment instructions.

## Useful Commands
```bash
cd api
uv run pytest                            # full test suite
uv run pytest test/agents/test_agents.py  # targeted agent workflow test
uv run pytest --cov=. --cov-report=term-missing
```

## Database Migrations
Use `api/scripts/database.py` for Alembic workflows:
```bash
cd api
uv run python scripts/database.py                     # upgrade to head
uv run python scripts/database.py revision "add foo"  # auto-generate revision
uv run python scripts/database.py downgrade -1        # roll back one revision
```
Existing revisions are stored in `api/migrations/versions/6ee06edc35dd_modify_data_model.py`. See `docs/database_migrations.md` for collaboration tips.

## API Overview
- `GET /` – health information
- `/v1/auth/*` – service-to-service JWT issuance and verification
- `/v1/threads/*` – thread creation plus synchronous/async LangGraph runs
- `/v1/messages/*` – direct access to the lightweight `LLMClient`
- `/v1/assistants/*` – CRUD for agent assistants
- `/v1/prompts/*` – prompt versioning, testing, cloning, and rollback
- `/v1/social-media/*` – utilities for comments, replies, keyword extraction, chat, and prompt reload
- `/v1/tenants/*` – tenant synchronisation from upstream systems

Refer to the auto-generated docs or the `schemas/` module for detailed payloads.

## Further Reading
- `docs/DEPLOYMENT.md` – development and production deployment playbooks
- `docs/database_migrations.md` – Alembic workflow & best practices
- `docs/MULTI_LLM_USAGE.md` – configuring and calling the multi-LLM runtime
- `docs/message-storage-strategy.md` – Redis/Elasticsearch/Milvus memory strategy

## Support
- Email: consumerclone@outlook.com
- Team: HuanMu Team
