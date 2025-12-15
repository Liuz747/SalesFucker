# Repository Guidelines

## Project Structure & Module Organization

Composing repository contribution guide (56s • Esc to interrupt)
The API root groups production code under domain-focused folders: `core/` holds agent logic, workflows, and
multimodal utilities; `controllers/` exposes FastAPI routers and middleware; `infra/` manages db, cache, and runtime
integrations. Persistence models live in `models/` and `repositories/`, while configuration helpers sit in `config/
`. Tests mirror this layout inside `test/`, with subdirectories for `api/`, `agents/`, `llm/`, and `auth/`. Reusable
helpers and constants are in `libs/` and `utils/`. Entry points include `main.py` for the FastAPI app and `scripts/`
for environment automation.

## Build, Test, and Development Commands
Run `uv sync` after cloning to install dependencies from `pyproject.toml`. Launch the API locally with `uv run main.py`, which boots Uvicorn using configuration in
`config/mas_config`. Execute automated checks with `uv run pytest`; append `-k <pattern>` to scope suites (e.g., `uv run pytest -k agents`). Database migrations use
Alembic via `uv run alembic upgrade head`.

## Coding Style & Naming Conventions
Code targets Python 3.13 with 4-space indentation and type hints. Keep modules cohesive and prefer explicit imports from package `__init__.py` exports. Follow
Pydantic model conventions for request/response schemas and snake_case filenames (see `controllers/workspace/assistants_controller.py`). Loggers should come from
`utils.get_component_logger` to align formatting.

## Testing Guidelines
Use `pytest` with `pytest-asyncio` for async routines and adhere to the directory-specific scopes documented in `test/README.md`. Name test modules after the unit
under test (e.g., `test_thread_performance.py`) and functions with `test_`. Mock external services—Redis, LLM providers, HTTP calls—via fixtures or monkeypatching. Add
regression tests whenever changing agent behaviors or routing logic.

## Commit & Pull Request Guidelines
Follow the conventional `type: summary` pattern seen in history (`feat: ...`, `fix: ...`). Commits should be focused and reference issue IDs when available. PRs need a
concise summary, validation notes (commands run, screenshots for API responses if applicable), and call out configuration or migration impacts. Link related tickets and
ensure reviewers understand any new environment requirements.

## Security & Configuration Tips
Keep secrets out of version control; populate `.env` using `scripts/setup.sh`. Regenerate API keys and database passwords for shared environments. When adding new
services, update `config/models.yaml` and the corresponding `config/service` providers with minimal privileges, and document required credentials in the PR.