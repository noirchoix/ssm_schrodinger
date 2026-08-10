# Changelog

## v2.6.0-dev.2 — Unified Canonical Semantic Context + Constrained Online SML Synthesis

### Added

- Added content-addressed `CanonicalSemanticContext` as the deterministic semantic authority between capability negotiation and SML synthesis.
- Added structural `SemanticConformanceVerifier` with typed diagnostics for stack, tenancy, audit, capabilities, data models, relationships, roles, workflows, rules/invariants, routes, reports, and required scaffolding.
- Added persisted `input.md`, canonical front-end artifacts, semantic-conformance reports, and corresponding generation-run fingerprints for online builds.
- Added `online-build --file` so file and prompt entry paths converge on the same run-local input-document boundary.
- Added fail-closed pre-provider rejection for contradictory, blocking, unsupported, or internally inconsistent canonical semantic contexts.
- Added canonical-context-aware mock synthesis for deterministic online-path testing.

### Changed

- Unified offline and online generation behind the same RequirementsIR → foundation → architecture → capability composition → negotiation → canonical-context front end.
- Online providers now receive a bounded canonical semantic payload rather than unconstrained raw intent as the semantic authority.
- Candidate online SML is parsed, then checked for semantic conformance before candidate capability consistency and `SSMCompiler` invocation.
- Bounded repair now distinguishes semantic-conformance rejection from compiler rejection and quality-gate rejection.
- Offline deterministic SML passes through the same semantic-conformance verifier.
- Corrected inventory/product entity planning so the phrase `Docker support` cannot accidentally route an inventory request into the ticketing/helpdesk entity branch.
- Runtime/package identity advanced to `2.6.0.dev2`.

### Research impact

- Establishes a measurable stochastic boundary: deterministic canonical semantic collapse precedes the optional LLM, and deterministic verification/compiler stages resume after candidate synthesis.
- Adds canonical-context and semantic-conformance fingerprints for first-changed-stage attribution and later SSM-Bench v2 controlled experiments.
- Does not claim new live-provider certification until the V2.0 live DeepSeek gate is rerun against this dev.2 build.

## v2.6.0-dev — SSM Schrödinger Auto Research

- Restored the certified deterministic FastAPI target omitted from the uploaded GitHub archive.
- Added canonical content-addressed `GenerationRunRecord` emission for offline and online builds.
- Added strict Auto-style JSONL tracing for compiler stages and model calls.
- Added replay comparison and witnessed determinism census.
- Added behavioural contracts with three-valued verification and content-addressed evaluation runs.
- Added a local immutable SHA-256 registry with optional HMAC integrity signatures.
- Added paired release assays with four-state verdicts, change-intent envelopes, slice analysis, and stage attribution.
- Added frozen content-addressed SSM-Bench v1 with 30 stratified application intents.
- Added research CLI commands, schema documentation, examples, and an integrated E2E gate.
- Kept sequential production monitoring, unknown-slice discovery, conformal guard/deopt, and WASM cognition binaries explicitly deferred.

## v2.0.0-dev — Product-platform acceptance branch

### Added

- Evidence schema 2.0 with SHA-256 provenance for generated files and tamper detection.
- Automatic tenant fields for every route-owned entity in tenant-enabled applications.
- Tenant-scoped SQLAlchemy and in-memory CRUD/uniqueness enforcement.
- JWT role claims and generated RBAC permission checks on protected routes.
- SQLAlchemy tenant, audit-event, and workflow-state persistence models with Alembic revision `0002_platform_runtime`.
- CRUD and workflow audit writes, persistent workflow orchestration, exact transition checks, and safe business-rule evaluation.
- Production-buildable React/Vite admin client with CRUD pages, OpenAPI loader, auth/tenant request wrapper, strict TypeScript, and generated CI/Make build stages.
- Seeded `online-build --initial-draft` path for deterministic and live-provider repair validation.
- Dedicated `scripts/test_v20_e2e.sh` product-platform release gate.

### Hardened

- Full tenant isolation across API, service, and repository boundaries.
- Database-backed audit persistence and tenant-scoped retrieval.
- Workflow state persistence and optimistic state conflict handling.
- Generated readiness checks and seed/admin CLI execution tests.
- Frontend production typecheck/build validation.

## v1.5.0-dev — Platform layer development build

Release type: development milestone, not locked stable.

### Added

- Generated evidence records: manifest, app contract, eval run, capability report, assumptions, unsupported features, provenance hashes, and evidence bundle.
- `evidence-check` CLI command for generated app evidence validation.
- Generated platform primitives for tenancy, RBAC, audit capture, workflow transition runtime, and seed/admin CLI scaffold.
- Generated platform API routes under `/platform`.
- Generated admin UI shell under `admin/`.
- Online-build bounded repair attempts and `repair_trace.json`.
- V1.5 E2E script with evidence, platform, online repair, and admin shell checks.

### Notes

- Internal `online-build --quality-gates` uses fast deterministic gates by default: evidence-check, Ruff, format check, compileall, and Bandit. Full generated-app pytest and mypy remain in the secondary E2E generated-app quality pass. Set `SSM_ONLINE_FULL_GATES=1` to include pytest and mypy inside the repair loop.
- Tenant-scoped repository filtering, DB-backed audit persistence, full workflow orchestration, and production frontend build hardening remain future hardening layers.

## v1.3.2 — Version-lock release

Release type: release hygiene and validation lock.

### Fixed

- Bumped the runtime package version exposed by `ssm.__version__` to `1.3.2` so package metadata and runtime metadata are aligned.
- Replaced the earlier E2E shell script with the merged V1.3.2 script that saves timestamped logs, detects project root robustly, validates `scripts/`, and runs the boundary-aware secret scanner.
- Confirmed the online-build mock output path `build/e2e/online_mock/generated_app` is recognized and receives a secondary generated-app quality pass.

### Added

- `docs/CAPABILITY_MATRIX.md` to define the supported, partial, and out-of-scope capabilities for the V1.3.2 release.
- `docs/RELEASE_CHECKLIST_V1_3_2.md` with the version-lock procedure and Git tag commands.
- `RELEASE_NOTES.md` describing the release state, acceptance gates, and known limitations.
- `scripts/tag_v1_3_2.sh` as a convenience helper for local Git tagging.

### Validation target

The approved V1.3.2 release gate is:

```bash
chmod +x scripts/test_v13_e2e.sh
./scripts/test_v13_e2e.sh
```

Optional gates remain available with:

```bash
RUN_POSTGRES=1 ./scripts/test_v13_e2e.sh
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v13_e2e.sh
```

## v1.3.1 — Generated-app coverage hotfix

- Removed unused generated DTO persistence stubs.
- Added generated service contract tests.
- Restored generated-app coverage above the 80% threshold for multi-entity apps.

## v1.3.0 — General Domain Foundation Generator

- Added `AppFoundationPlan`.
- Added domain-pack selection and capability negotiation.
- Added multi-domain benchmark examples.
- Added full CRUD route hardening.
- Added initial online-build acceptance loop.
