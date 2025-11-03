# MAS Deployment Guide

This guide explains how to run the MAS backend locally and how to promote it to a containerised environment. The instructions reflect the current repository layout (FastAPI backend in `api/`, Compose files in `docker/`, frontend in `web/`).

---

## 1. Local Development

### 1.1 Bootstrap the backend
```bash
# 1. Clone and enter the backend directory
cd mas-v0.2/api

# 2. Install dependencies and create .env if missing
./scripts/setup.sh

# 3. Edit .env with API keys and infrastructure endpoints
vim .env  # or editor of your choice
```
Key variables:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `POSTGRES_USER`, `POSTGRES_PWD`
- `REDIS_URL` (or individual Redis host/port/password)
- `ELASTICSEARCH_URL`, `ELASTIC_PASSWORD`
- `MILVUS_HOST`, `MILVUS_PORT`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (when observability is enabled)

### 1.2 Bring up dependencies (optional but recommended)
Run from the repository root (`mas-v0.2/`):
```bash
docker compose -f docker/docker-compose.dev.yml up -d postgres redis
```
Add extra services as needed:
- `elasticsearch` – enable long-term memory indices
- `milvus-standalone` – enable vector memory search
- `langfuse-web`, `langfuse-worker`, `clickhouse`, `minio` – enable Langfuse observability and artifact storage
- `temporal`, `openobserve`, etc. – only when explicitly required by your workflow

### 1.3 Start the API
```bash
cd mas-v0.2/api
uv run uvicorn main:app --reload
# or uv run python main.py
```
FastAPI will listen on `http://localhost:8000`. Verify with:
- `http://localhost:8000/` – basic status payload
- `http://localhost:8000/docs` – auto-generated OpenAPI documentation

### 1.4 Run tests & migrations
```bash
# Pytest
uv run pytest
uv run pytest test/agents/test_agents.py

# Database migrations
uv run python scripts/database.py                     # upgrade to head
uv run python scripts/database.py revision "add foo"  # autogenerate revision
uv run python scripts/database.py downgrade -1        # roll back
```
See `docs/database_migrations.md` for detailed team workflow guidance.

### 1.5 Frontend & observability
The Next.js frontend and Langfuse worker/web apps live under `web/`. Typical flow:
```bash
cd mas-v0.2/web
pnpm install
pnpm dev  # serves the frontend on http://localhost:3000
```
When using Langfuse, export `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` in the API `.env`. Metrics will become visible once the backend emits traces.

---

## 2. Container Images

Use `docker/docker-compose.build.yml` to build ready-to-ship images for the API, frontend, and auxiliary services.
```bash
cd mas-v0.2
docker compose -f docker/docker-compose.build.yml build
# Optional: tag & push to your own registry
REGISTRY_URL=registry.example.com/mas-v0.2 \ 
  docker compose -f docker/docker-compose.build.yml push
```
The Compose file expects `REGISTRY_URL` and shares build contexts for:
- `api` – FastAPI backend image
- `frontend` – Langfuse UI bundle packaged as static assets
- `worker` – Langfuse background worker
- Supporting services (ClickHouse, Elasticsearch, Temporal images are referenced for convenience)

---

## 3. Production-Like Deployment

`docker/docker-compose.yml` orchestrates the full stack with prebuilt images, Nginx, and optional observability components. Before running it, export the environment variables referenced in the file (LLM keys, database credentials, Langfuse keys, TLS settings, etc.). A minimal example:
```bash
cd mas-v0.2
export REGISTRY_URL=registry.example.com/mas-v0.2
export DB_HOST=db
export DB_NAME=mas
export POSTGRES_USER=postgres
export POSTGRES_PWD=**redacted**
export REDIS_HOST=redis
export REDIS_PASSWORD=**redacted**
export OPENAI_API_KEY=sk-...
export APP_KEY=backend-secret
# ...and so on for each service

docker compose -f docker/docker-compose.yml up -d
```
Main services included:
- `mas` – FastAPI backend
- `nginx` – public entrypoint (HTTP/HTTPS configurable via env vars)
- `langfuse-web` / `langfuse-worker` – observability dashboards
- `postgres`, `redis`, `elasticsearch`, `milvus-standalone` – stateful dependencies
- `clickhouse`, `minio`, `temporal` – required by Langfuse in the provided stack

Adjust exposed ports through `EXPOSE_*` variables and mount TLS certificates under `docker/nginx/ssl` when enabling HTTPS.

To update the stack, rebuild or retag the images, then run `docker compose ... up -d` again. For troubleshooting, inspect logs per service:
```bash
docker compose -f docker/docker-compose.yml logs mas        # backend
docker compose -f docker/docker-compose.yml logs nginx      # reverse proxy
```

---

## 4. Maintenance Checklist
- Rotate `.env` secrets and JWT `APP_KEY` regularly
- Back up PostgreSQL, Redis snapshots, and any Langfuse ClickHouse volumes
- Monitor Elasticsearch and Milvus disk usage when long-term memory is enabled
- Keep Compose images up to date (`docker compose pull`) to receive security patches
- Run `uv run pytest` before tagging releases to ensure workflows remain healthy

With these steps you can spin up MAS locally for development, build deterministic images, and deploy the full stack behind Nginx with Langfuse observability.
