# V1.3.1 Coverage Hotfix

- Fixed generated app coverage failure for multi-entity foundation apps by no longer emitting unused `app/models/*Create.py` persistence-model stubs for DTO schemas.
- Added generated `tests/test_service_contracts.py` to exercise repository/service full CRUD contracts for each generated entity, including generated apps whose route surface is intentionally list/create only.
- Revalidated HR Leave foundation and full-CRUD inventory regression apps against pytest coverage, Ruff, mypy, Bandit, and Alembic migration cycling.

# Build Report — SSM Framework V1.1 Pre-Online Hardening

## Patch date
2026-06-30

## Scope
This patch starts from the approved V1 runtime-tested version and adds the necessary-and-sufficient hardening surface before online AI-provider testing.

## Issues addressed

- Added generated-app coverage thresholds with `pytest-cov` and `--cov-fail-under=80`.
- Added generated OpenAPI contract tests for paths, methods, schemas, and bearer security contracts.
- Added deterministic generated load-smoke tests.
- Added optional Locust load-test scaffold under `load/locustfile.py`.
- Added generated `docker-compose.yml` with PostgreSQL service for SQLAlchemy builds.
- Added generated GitHub Actions workflows; SQLAlchemy builds include a PostgreSQL service and gated PostgreSQL integration execution.
- Added root framework GitHub Actions workflow that tests framework quality and generated example quality.
- Added generated `.dockerignore` to keep image contexts cleaner.
- Added generated PostgreSQL integration test gated by `RUN_POSTGRES_INTEGRATION=1`.
- Added root Makefile targets for generated quality and coverage.
- Added offline agent-boundary CLI commands: `draft` and `repair-missing-schema`.
- Added offline agent interface tests proving agents produce SML/semantic patches, not final source code.
- Added `docs/V1_1_PRE_ONLINE_HARDENING.md` documenting the pre-online acceptance surface.

## Validation performed in sandbox

Framework gates:

```bash
ruff check src tests
ruff format --check src tests
mypy src/ssm
pytest --cov=ssm --cov-report=term-missing -q
python -m compileall -q src tests
bandit -q -r src/ssm
```

Result:

```text
Ruff check: passed
Ruff format check: passed
Mypy: passed
Pytest: 12 passed
Coverage: passed, threshold 70%
Compileall: passed
Bandit: passed
```

Generated Inventory API gates:

```bash
python -m ssm.cli.main compile examples/inventory_api/project.sml.md --out build/inventory_api
cd build/inventory_api
python -m pip install -e '.[dev]'
pytest -q
ruff check .
ruff format --check .
mypy app
python -m compileall -q app tests
bandit -q -r app
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Result:

```text
Compile: passed, 49 files
Pytest: 8 passed, 1 skipped
Coverage: passed, threshold 80%
Ruff check: passed
Ruff format check: passed
Mypy: passed
Compileall: passed
Bandit: passed
Alembic SQLite upgrade/downgrade/upgrade: passed
```

Generated Todo API gates:

```bash
python -m ssm.cli.main compile examples/todo_api/project.sml.md --out build/todo_api
cd build/todo_api
python -m pip install -e '.[dev]'
pytest -q
ruff check .
ruff format --check .
mypy app
python -m compileall -q app tests
bandit -q -r app
```

Result:

```text
Compile: passed, 40 files
Pytest: 7 passed
Coverage: passed, threshold 80%
Ruff check: passed
Ruff format check: passed
Mypy: passed
Compileall: passed
Bandit: passed
```

Determinism/offline gate:

```bash
unset OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY
python -m ssm.cli.main compile examples/inventory_api/project.sml.md --out build/a
python -m ssm.cli.main compile examples/inventory_api/project.sml.md --out build/b
diff -r build/a build/b
```

Result: passed. `diff -r` returned no output.

## Not executed in sandbox

`pip-audit` was installed but could not complete because the sandbox cannot resolve `pypi.org`. Run it locally or in CI with network access.

PostgreSQL integration is implemented and gated, but the sandbox did not run a real PostgreSQL service. The generated GitHub Actions workflow and generated `docker-compose.yml` provide the execution path.

Docker compose/live container tests require a Docker-enabled host and should be run locally or in CI.

## Remaining intentional limitations

This is still scoped V1.1 hardening, not the online model phase. Live LLM calls, online RAG retrieval, model cost/latency logging, provider retry budgets, and provider-specific integration tests are intentionally deferred to the next phase.

## V1.2 Online Agent Integration

This build adds a gated online agent layer for prompt-to-SML drafting. Generation providers supported by the online layer are `openai`, `deepseek`, `gemini`, and `mock`. Embedding providers supported are `gemini`, `voyageai`, and `mock`.

Online models are restricted to SML drafting and semantic assistance. Final source generation remains deterministic and compiler-owned. See `docs/V1_2_ONLINE_AGENT.md`.

Validated local gates include framework tests, Ruff, formatting, mypy, Bandit, offline determinism, mock online draft, validate, compile, and generated-app quality checks.


## V1.2 Online Agent Build Report

Implemented gated online agent support for prompt-to-SML drafting with provider adapters for OpenAI-compatible APIs, DeepSeek, Gemini, and deterministic mock mode. Added embedding provider abstractions for Gemini, VoyageAI, and mock embeddings.

Validation completed in this build:

```text
framework pytest with coverage: 19 passed, coverage 81.13%, threshold 70%
ruff check src tests: passed
ruff format --check src tests: passed
mypy src/ssm: passed
python -m compileall src tests: passed
bandit -q -r src/ssm: passed
mock online draft -> validate -> compile: passed
mock online generated Inventory app tests: 8 passed, 1 skipped, coverage 84.54%, threshold 80%
mock online generated Inventory ruff/mypy/compileall/bandit: passed
```

Network-backed provider calls were not executed in the sandbox because live API keys are not available. The online boundary was tested with the mock provider through the same CLI path used by live providers.

## V1.3 General Domain Foundation Build Report

Implemented the V1.3 generalization layer. Inventory is retained as a benchmark, but the compiler now includes generalized app-foundation planning, domain-pack selection, capability negotiation, generalized semantic SML sections, full CRUD route hardening, multi-domain benchmarks, and the `plan`, `negotiate`, and `online-build` CLI commands.

Key implementation areas:

```text
src/ssm/foundation/*
src/ssm/domain_packs/*
src/ssm/semantic/analyzer.py
src/ssm/backends/python_fastapi/target.py
src/ssm/agents/sml_agent.py
src/ssm/agents/online.py
src/ssm/cli/main.py
examples/*_api/project.sml.md
docs/V1_3_GENERAL_DOMAIN_FOUNDATION.md
```

Validated local gates in this build:

```text
framework pytest: 23 passed
framework coverage: 83.39%, threshold 70%
ruff check src tests: passed
ruff format --check src tests: passed
mypy src/ssm: passed
python -m compileall src tests: passed
bandit -q -r src/ssm: passed
multi-domain validate/compile: inventory, todo, HR leave, expense approval, CRM pipeline, ticketing, school records: passed
plan -> negotiate -> compile HR leave: passed
online-build mock path: ACCEPTED
DeepSeek full-CRUD regression SML: validate passed, compile passed, generated tests passed, generated mypy passed
```

Generated app validations completed:

```text
DeepSeek full CRUD Inventory app: 11 passed, 1 skipped, coverage 88.08%, ruff passed, format passed, mypy passed, compileall passed, bandit passed, Alembic upgrade/downgrade/upgrade passed.
HR Leave benchmark app: 16 passed, 1 skipped, coverage 89.55%, ruff passed, format passed, mypy passed, compileall passed, bandit passed, Alembic upgrade/downgrade/upgrade passed.
```

Sandbox limitation: `pip-audit` could not complete because the sandbox could not resolve `pypi.org`. Run `pip-audit` locally or in CI with network/advisory access.
