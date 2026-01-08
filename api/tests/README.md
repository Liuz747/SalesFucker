Test Suite Structure

Standardized layout:

- auth/: Authentication & authorization tests
- api/: FastAPI endpoint tests
- agents/: Agent unit/integration tests
- llm/: Multi-LLM providers, router, optimizer tests
- integration/: Cross-module integration tests
- perf/: Performance/load tests
- mocks/: Mock frameworks and helpers

Conventions:
- Prefer fast unit tests; isolate network calls via monkeypatch/mocks
- Place new auth tests under tests/auth/
- Place endpoint tests under tests/api/


