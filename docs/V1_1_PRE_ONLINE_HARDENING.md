# V1.1 Pre-Online Hardening

This pass defines the necessary-and-sufficient hardening layer before connecting online AI providers.

## Necessary and sufficient gates

The framework is ready for online AI testing when these gates are green:

1. Framework quality: `ruff`, `ruff format --check`, `mypy`, `pytest`, `bandit`.
2. Deterministic offline compile: no API keys and no network calls are required for `validate`, `inspect`, or `compile`.
3. Generated app quality: `ruff`, `ruff format --check`, `mypy`, `pytest`, `bandit`, `pip-audit`.
4. Generated app coverage: generated apps enforce `--cov-fail-under=80`.
5. OpenAPI contract tests: generated routes, schemas, and bearer auth contract are tested through `/openapi.json`.
6. Database migrations: SQLAlchemy builds execute Alembic upgrade/downgrade/upgrade.
7. Real PostgreSQL integration path: SQLAlchemy builds include `docker-compose.yml`, GitHub Actions PostgreSQL service configuration, and a gated PostgreSQL integration test.
8. Runtime smoke: Uvicorn and Docker smoke tests still boot `/healthz` and `/openapi.json`.
9. Load smoke: generated apps include deterministic load-smoke tests and an optional Locust load-test scaffold.
10. Agent boundary: agents may draft or patch SML, but final source generation remains deterministic compiler output.

## What remains intentionally deferred to online testing

- Live LLM provider calls.
- Online RAG retrieval.
- Model quality evaluation across prompts.
- API-key handling across OpenAI, Anthropic, Gemini, or other model providers.
- Cost, latency, retry, and rate-limit measurement.

Those belong to the next phase because the runtime compiler path must remain green without any online dependency.
