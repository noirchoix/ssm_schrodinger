# V2.0.0-dev Version State

- `pyproject.toml`: `2.0.0.dev0`
- `src/ssm/__init__.py`: `__version__ = "2.0.0.dev0"`
- Current release gate: `scripts/test_v20_e2e.sh`
- Local product-platform gate: passed on 2026-07-13
- Final `2.0.0` lock: pending retained live DeepSeek forced-repair certification

See `docs/V2_0_LOCAL_VALIDATION.md` and `docs/V2_0_ACCEPTANCE_MATRIX.md`. The V1.3.2 report below is retained as historical release evidence.

---

# V1.3.2 Version Lock Report

## Version state

- `pyproject.toml`: `1.3.2`
- `src/ssm/__init__.py`: `__version__ = "1.3.2"`
- Release banner: `SSM V1.3.2 GENERAL DOMAIN FOUNDATION`

## Implemented release-lock fixes

- Aligned runtime package version with project metadata.
- Replaced `scripts/test_v13_e2e.sh` with the merged timestamped-output E2E script.
- Added release notes, changelog, capability matrix, release checklist, `.gitignore`, and a local tag helper script.
- Updated CI framework checks to include `scripts/secret_scan.py` in Ruff, mypy, Bandit, and secret-scan validation.
- Preserved the V1.3.2 boundary-aware secret scanner.

## Validation performed in sandbox

The default single-command E2E script was started from a clean extracted root and passed the framework quality stage before the sandbox command runtime limit interrupted the later benchmark stage. The same release gates were then executed in smaller chunks from the same clean extracted root.

Passed gates:

- Runtime version import: `1.3.2`
- Framework pytest: `23 passed`, coverage `83.47%` against `70%`
- Ruff check: passed
- Ruff format check: passed
- mypy: passed
- compileall: passed
- Bandit: passed
- Multi-domain validate/negotiate/compile: inventory, todo, HR leave, expense approval, CRM pipeline, ticketing, school records all passed
- Full CRUD regression validate/negotiate/compile: passed
- HR Leave foundation generated app: `12 passed, 1 skipped`, coverage `91.54%`
- Full CRUD inventory generated app: `12 passed, 1 skipped`, coverage `89.91%`
- HR Leave benchmark generated app: `18 passed, 1 skipped`, coverage `92.39%`
- Online-build mock: `ACCEPTED`
- Online-build mock generated app: `9 passed, 1 skipped`, coverage `88.92%`
- Generated app Ruff / format / mypy / compileall / Bandit / Alembic cycles: passed
- Boundary-aware secret scan: passed

Not rerun successfully in sandbox:

- `pip-audit` could not complete because the sandbox could not resolve `pypi.org`. The E2E script still includes `pip-audit` by default. Run locally or in CI with network access.
- `RUN_POSTGRES=1` was not run in sandbox.
- `RUN_DEEPSEEK_LIVE=1` was not run in sandbox.

## Final lock command for your local machine

```bash
chmod +x scripts/test_v13_e2e.sh
./scripts/test_v13_e2e.sh
```

Then tag:

```bash
git add .
git commit -m "Release v1.3.2 general domain foundation"
git tag -a v1.3.2 -m "SSM Framework v1.3.2 general domain foundation release"
git push origin main --follow-tags
```
