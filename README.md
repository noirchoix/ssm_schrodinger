# Semantic Software Markup Compiler — V2.0.0-dev Product Platform

SSM V2.0 is the product-platform development line built on the locked V1.3.2 general-domain foundation. It generates deterministic FastAPI backends, tenant/RBAC/audit/workflow runtime primitives, provenance-backed release evidence, and production-buildable React/Vite admin clients. Online models remain constrained to SML drafting and repair; compiler code emits final source.

## V2.0 release gate

```bash
./scripts/test_v20_e2e.sh
```

Final live-provider certification:

```bash
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v20_e2e.sh
```

See `docs/V2_0_PLATFORM.md`, `docs/V2_0_ACCEPTANCE_MATRIX.md`, and `docs/V2_0_LOCAL_VALIDATION.md` for the product boundary, criterion-by-criterion evidence, and latest local gate record.

---

## Historical V1.5 development documentation

# Semantic Software Markup Compiler — V1.5.0-dev Platform Layer


This development build extends the locked V1.3.2 general domain foundation compiler with an Auto-inspired platform layer: generated app manifests, app contracts, evidence records, SaaS primitives, workflow transition runtime, bounded online repair traces, and a generated admin UI shell. The core contract remains compiler-first: models may draft SML, but deterministic compiler code emits final source.

This repository is the V1.5.0-dev general-purpose semantic app foundation compiler. It keeps the compiler-first contract while adding typed app planning, domain packs, capability negotiation, multi-domain benchmarks, and gated online drafting:

```text
SML parser → SIR builder → symbolic logic → latent resolver → deterministic target pack → generated project → validation/tests/provenance
```

Agents may create or patch SML, but the deterministic compiler owns final source generation.

## What is implemented

- Phase 1: SML parser, AST, strict syntax diagnostics, CLI validation.
- Phase 2: Semantic analyzer, SIR graph, symbol table, reference validation, fact extraction.
- Phase 3: Symbolic Logic Decision Layer with Horn-style forward chaining, invalid-state detection, missing required artifact checks, and proof traces.
- Phase 4: Latent Resolution Engine with hard admissibility filtering before soft scoring and deterministic tie-breaks.
- Phase 5: advanced `python.fastapi` target pack with route/service/repository layering, request-scoped DB sessions, Alembic migrations, Pydantic settings, JWT validation, request IDs, structured error responses, business-rule validation, Docker/CI/pre-commit scaffolding, real FastAPI integration tests, OpenAPI contract tests, coverage thresholds, load-smoke tests, and PostgreSQL integration scaffolding.
- Phase 6: PydanticAI-compatible agent interfaces and gated online provider layer. Agents draft or patch SML only; they do not generate final source code.
- Phase 7: General Domain Foundation layer with AppFoundationPlan, domain packs, capability negotiation, generalized SML primitives, and multi-domain benchmarks.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m ssm.cli.main validate examples/todo_api/project.sml.md
python -m ssm.cli.main inspect examples/todo_api/project.sml.md --stage facts
python -m ssm.cli.main compile examples/inventory_api/project.sml.md --out build/inventory_api
pytest
python -m ssm.cli.main draft --prompt "Build a FastAPI inventory API with PostgreSQL and JWT auth"
```

## Advanced generated FastAPI project features

The generated SQLAlchemy/FastAPI project now includes:

- `app/core/config.py` using `pydantic-settings` instead of scattered `os.getenv` calls.
- `app/db/session.py` with `get_db()` request-scoped session injection.
- Alembic scaffolding and an initial deterministic migration.
- No repository-level `init_db()` calls.
- Centralized domain exceptions and FastAPI exception handlers.
- Real JWT bearer token validation with PyJWT.
- Request ID middleware and response headers.
- Pagination parameters on list endpoints.
- Service-layer business rules and transactional boundaries.
- Tests with fixtures, factories, auth coverage, duplicate handling, validation failure coverage, and request ID assertions.
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml`.
- OpenAPI contract tests.
- Coverage thresholds through `pytest-cov`.
- Load-smoke tests and optional Locust load-test scaffold.
- PostgreSQL GitHub Actions service path for SQLAlchemy builds.

## Determinism contract

For identical SML input, compiler version, target pack, and resolution policy, the generated files, manifest, and proof trace are stable.

## Design rule

Invalid candidates are rejected by symbolic admissibility before scoring. A heuristic cannot rescue a logically invalid candidate.

## Production acceptance gates

Framework gates:

```bash
ruff check src tests
ruff format --check src tests
mypy src/ssm
pytest --cov=ssm --cov-report=term-missing -q
bandit -q -r src/ssm
```

Generated app gates:

```bash
cd build/inventory_api
ruff check .
ruff format --check .
mypy app
pytest -q
bandit -q -r app
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Generated SQLAlchemy apps also include a gated real-PostgreSQL test path:

```bash
RUN_POSTGRES_INTEGRATION=1 DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/app pytest tests/test_postgres_integration.py
```

Security audit tooling is included in generated app dev dependencies:

```bash
pip-audit
bandit -q -r app
```

`pip-audit` requires access to advisory/package metadata, so it should be run in an environment with internet access or a configured internal advisory mirror.

## Offline mode

The deterministic compiler path is offline by default. It does not call OpenAI, Anthropic, Gemini, embeddings, vector databases, or external APIs during `validate`, `inspect`, or `compile`. The test suite includes an offline determinism test that removes common LLM API keys and fails on outbound socket attempts during compilation.

## V1.1 pre-online hardening

The current approved version is ready to move toward online AI testing after these offline gates. The online phase should connect model providers only through the agent layer, keep final code generation deterministic, and test that agents return structured SML drafts or semantic patches rather than arbitrary source code.


## V1.3 General Domain Foundation Generator

This build generalizes the project beyond the inventory benchmark. Inventory is now one reference vertical slice, not the product. The product is a reusable semantic app generator/compiler for app idea X:

```text
Prompt -> AppFoundationPlan -> domain packs -> capability negotiation -> SML -> validation -> deterministic FastAPI generation -> quality gates
```

New V1.3 capabilities include:

- `AppFoundationPlan` typed pre-SML planning.
- Domain-pack registry for `generic_crud`, `workflow_approval`, `inventory`, `hr`, `expense`, `crm`, `procurement`, `ticketing`, and `school`.
- Capability negotiation with `SUPPORTED`, `SUPPORTED_WITH_ASSUMPTIONS`, `PARTIALLY_SUPPORTED`, and `UNSUPPORTED`.
- General SML sections for capability, tenant, audit, roles, permissions, relationships, workflows, business rules, invariants, reports, and integrations.
- Full CRUD route hardening for `GET/PATCH/PUT/DELETE /resources/{id}`.
- Multi-domain benchmark examples including HR leave, expense approval, CRM pipeline, ticketing, and school records.
- New CLI commands: `plan`, `negotiate`, and `online-build`.

See `docs/V1_3_GENERAL_DOMAIN_FOUNDATION.md`.

## V1.2 Online Agent Integration

This build adds a gated online agent layer for prompt-to-SML drafting. Generation providers supported by the online layer are `openai`, `deepseek`, `gemini`, and `mock`. Embedding providers supported are `gemini`, `voyageai`, and `mock`.

Online models are restricted to SML drafting and semantic assistance. Final source generation remains deterministic and compiler-owned. See `docs/V1_2_ONLINE_AGENT.md`.

Validated local gates include framework tests, Ruff, formatting, mypy, Bandit, offline determinism, mock online draft, validate, compile, and generated-app quality checks.



## V1.3.2 secret-scan hotfix

V1.3.2 adds `scripts/secret_scan.py` and `scripts/test_v13_e2e.sh`. The scanner is boundary-aware so ordinary app slugs such as `helpdesk--ticketing--api--tickets` are not misclassified as `sk-` API tokens while real environment secrets and standalone `sk-...` keys are still detected.

## V1.3.2 version-lock release

V1.3.2 aligns package metadata and runtime metadata, replaces the E2E script with the timestamped log-saving release script, and adds release documentation for capability scope, changelog, and tagging. The version-lock gate is `./scripts/test_v13_e2e.sh` from a clean extracted release root.


## V1.5.0-dev Platform Layer

V1.5.0-dev adds five platform capabilities while preserving the V1.3.2 product identity:

- Trust layer: generated app manifest, app contract, eval record, capability report, assumptions, unsupported features, provenance hashes, and release evidence bundle.
- SaaS primitives: tenant context propagation, RBAC role/permission model, audit event capture, platform routes, and seed/admin CLI scaffold.
- Workflow runtime: generated workflow metadata and transition endpoint.
- Online repair loop: bounded repair attempts and `repair_trace.json` output.
- Admin shell: generated `admin/` frontend scaffold with an OpenAPI-aware API client shell.

Use the V1.5 E2E script for the dev platform layer:

```bash
chmod +x scripts/test_v15_e2e.sh
RUN_PIP_AUDIT=0 ./scripts/test_v15_e2e.sh
```

`pip-audit` remains enabled by default when network/advisory access is available.
