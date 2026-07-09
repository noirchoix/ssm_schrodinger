# V1.3.2 Status Update

Status: patched and accepted for the coverage issue exposed by the E2E HR Leave foundation run. The previous failure was not a runtime defect; it was a generated-app coverage gate failure caused by unexercised generated service/repository paths and unused DTO persistence stubs.

# Phase Status — V1.1 Pre-Online Hardening

| Phase | Status | Notes |
|---|---:|---|
| Phase 1 — Compiler core | Complete | Parser, AST, CLI validate/inspect/compile, plus offline `draft` and `repair-missing-schema` agent-boundary commands. |
| Phase 2 — Semantic layer | Complete | SIR graph, symbol table, reference validation, fact extraction. |
| Phase 3 — Symbolic logic | Complete | Horn-style rules, admissibility, proof trace, invalid candidate rejection. |
| Phase 4 — Latent resolver | Complete | Hard logic filter, soft score, deterministic tie-break. |
| Phase 5 — FastAPI target | V1.1 hardened | Generated apps now include coverage thresholds, OpenAPI contract tests, load-smoke tests, PostgreSQL docker-compose/CI integration path, Docker, Bandit, pip-audit, mypy, Ruff, and Alembic gates. |
| Phase 6 — Agent layer | Pre-online ready | PydanticAI-compatible contracts remain offline by default; agents draft/patch SML only and never final generated source. |

## Current acceptance status

- Framework tests: 12 passed.
- Framework coverage gate: passed, threshold 70%.
- Framework Ruff check/format: passed.
- Framework mypy: passed.
- Framework Bandit: passed.
- Offline/no-AI compile and deterministic diff: passed.
- Generated Inventory API tests: 8 passed, 1 PostgreSQL integration test skipped unless enabled.
- Generated Inventory coverage gate: passed, threshold 80%.
- Generated Inventory Ruff check/format: passed.
- Generated Inventory mypy: passed.
- Generated Inventory Bandit: passed.
- Generated Inventory Alembic SQLite upgrade/downgrade/upgrade: passed.
- Generated Todo API tests: 7 passed.
- Generated Todo coverage gate: passed, threshold 80%.
- Generated Todo Ruff check/format: passed.
- Generated Todo mypy: passed.
- Generated Todo Bandit: passed.

## Remaining intentionally online/environmental gates

- `pip-audit` should be run in a network-enabled environment or against an internal advisory mirror.
- PostgreSQL integration should be run with `RUN_POSTGRES_INTEGRATION=1` and a real `DATABASE_URL`; generated GitHub Actions config already defines this path.
- Docker compose and live container smoke should be run on a Docker-enabled host.

## Next phase candidate

Move to online AI testing with real provider keys, model retry budgets, structured PydanticAI outputs, online RAG retrieval, cost/latency logging, and explicit tests proving agents only emit SML or semantic patches.

## V1.2 Online Agent Integration

This build adds a gated online agent layer for prompt-to-SML drafting. Generation providers supported by the online layer are `openai`, `deepseek`, `gemini`, and `mock`. Embedding providers supported are `gemini`, `voyageai`, and `mock`.

Online models are restricted to SML drafting and semantic assistance. Final source generation remains deterministic and compiler-owned. See `docs/V1_2_ONLINE_AGENT.md`.

Validated local gates include framework tests, Ruff, formatting, mypy, Bandit, offline determinism, mock online draft, validate, compile, and generated-app quality checks.


## V1.2 Online Agent Status

Status: implemented and locally validated through mock online mode.

Production controls added:

- Explicit `RUN_ONLINE_AI=1` and `SSM_AGENT_MODE=online` gate.
- Provider selection for `openai`, `deepseek`, `gemini`, and `mock`.
- Typed online settings with CLI overrides.
- API-key discovery through provider-specific env vars and neutral override env vars.
- Request timeout, retry, temperature, and output-token limits.
- JSON-only response contract.
- Pydantic validation into `SMLDocumentDraft`.
- Compiler validation before accepting an online draft.
- Source-code emission guardrails.
- Secret redaction and audit logging.
- Embedding adapters for `gemini`, `voyageai`, and `mock`.
- Mock-provider CI path for online behavior without live API usage.

## V1.3 General Domain Foundation Status

Status: implemented and locally validated.

| Capability | Status | Notes |
|---|---:|---|
| AppFoundationPlan | Complete | Typed pre-SML application foundation representation. |
| Domain-pack registry | Complete | Generic CRUD, workflow approval, inventory, HR, expense, CRM, procurement, ticketing, and school packs. |
| Capability negotiation | Complete | Supports supported/assumptions/partial/unsupported statuses with actionable issues. |
| Generalized SML semantics | Complete | Capability, tenant, audit, roles, permissions, relationships, workflows, business rules, invariants, reports, and integrations. |
| General CRUD hardening | Complete | GET/PATCH/PUT/DELETE resource routes now generate repository, service, route, test, and OpenAPI support. |
| Multi-domain benchmarks | Complete | Inventory, todo, HR leave, expense approval, CRM pipeline, ticketing, and school records validate and compile. |
| SaaS foundations | V1.3 foundation complete | Health, readiness, Docker, CI, request IDs, JWT, OpenAPI, coverage, PostgreSQL path, and domain foundation docs are generated. Tenant/audit persistence is next. |
| Online-build loop | Initial complete | Draft, negotiate, compile, and optional quality gate structure is implemented. Further live provider hardening remains roadmap. |

Acceptance summary:

```text
Framework: 23 tests passed, coverage 83.39%, Ruff passed, format passed, mypy passed, compileall passed, Bandit passed.
DeepSeek full CRUD regression: accepted after compiler hardening.
HR leave benchmark: accepted as a non-inventory domain foundation benchmark.
```


## V1.3.2 secret-scan hotfix

V1.3.2 adds `scripts/secret_scan.py` and `scripts/test_v13_e2e.sh`. The scanner is boundary-aware so ordinary app slugs such as `helpdesk--ticketing--api--tickets` are not misclassified as `sk-` API tokens while real environment secrets and standalone `sk-...` keys are still detected.

## V1.3.2 version-lock release

V1.3.2 aligns package metadata and runtime metadata, replaces the E2E script with the timestamped log-saving release script, and adds release documentation for capability scope, changelog, and tagging. The version-lock gate is `./scripts/test_v13_e2e.sh` from a clean extracted release root.
