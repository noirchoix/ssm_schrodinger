# Changelog

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
