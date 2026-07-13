# V2.0.0-dev Local Validation Record

Validation date: 2026-07-13  
Runtime: `2.0.0.dev0`  
Gate: `scripts/test_v20_e2e.sh`  
Mode: deterministic framework + generated applications + bounded mock repair; live DeepSeek disabled.

## Result

```text
ALL V2.0.0-dev LOCAL E2E GATES PASSED
LIVE DEEPSEEK GATE NOT EXECUTED IN THIS RUN
```

## Framework

- Pytest: 32 passed.
- Coverage: 82.27%, threshold 70%.
- Ruff check and format check: passed.
- Mypy: passed across 43 source files.
- Compileall: passed.
- Bandit: passed.
- Secret scan: passed.

## Generated product-platform applications

| Generated application | Tests | Coverage | Backend gates | Migration gate | Admin gate |
|---|---:|---:|---|---|---|
| HR Leave SQLAlchemy benchmark | 29 passed, 1 skipped | 86.42% | mypy, pytest, Ruff, format, compileall, Bandit | Alembic `0001` → `0002` → base → `0002` passed | TypeScript and Vite production build passed |
| Inventory SQLAlchemy benchmark | 18 passed, 1 skipped | 84.74% | mypy, pytest, Ruff, format, compileall, Bandit | Alembic `0001` → `0002` → base → `0002` passed | TypeScript and Vite production build passed |
| Tenant-enabled in-memory application | 22 passed | 91.55% | mypy, pytest, Ruff, format, compileall, Bandit | Not applicable | TypeScript and Vite production build passed |
| Repaired mock-provider application | 17 passed | 88.50% | mypy, pytest, Ruff, format, compileall, Bandit | Not applicable | TypeScript and Vite production build passed |

Seven benchmark specifications also completed validation, capability negotiation, deterministic compilation, and evidence verification.

## Repair-loop proof

The release gate began from a deliberately incomplete SML document. Attempt one was rejected at the compiler boundary; the mock provider received the diagnostic and produced an accepted repair on attempt two. `repair_trace.json` schema 2.0 retained both outcomes.

## Environment-dependent gates

- Live DeepSeek forced repair was not executed because no provider credentials are available in this environment.
- `pip-audit` could not query `pypi.org` because external DNS resolution was unavailable. The gate remains enabled by default for network-capable CI/release hosts.
- SQLAlchemy migrations were fully cycled locally with SQLite. Generated CI and integration tests retain the PostgreSQL 16 service path for a Docker/network-capable host.

Final `2.0.0` promotion requires a retained successful run with:

```bash
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v20_e2e.sh
```
