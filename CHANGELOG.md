# Changelog

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
