# Advanced Production Hardening Notes

This hardening pass converts the first generated FastAPI scaffold from strong-intermediate backend output into a more senior-oriented production V1 target pack.

## Backend architecture upgrades

- Routes no longer own persistence concerns.
- Repositories no longer create database sessions or initialize the database.
- `get_db()` provides request-scoped SQLAlchemy sessions through FastAPI dependency injection.
- Services own transactional boundaries and domain validation.
- Domain exceptions are mapped centrally to HTTP responses in `app/main.py`.

## Database upgrades

- SQLAlchemy 2.0 style `select()` is used for repository reads.
- Unique fields receive SQLAlchemy unique/index metadata.
- Alembic scaffolding and deterministic `0001_initial.py` migration are emitted for SQLAlchemy projects.
- Tests build and tear down schema in fixtures instead of adding production test-only methods.

## Security upgrades

- Bearer tokens are decoded and validated with PyJWT.
- JWT issuer, audience, algorithm, secret, and token lifetime are settings-driven.
- `require_scopes()` is generated as an authorization extension point.
- Secrets are read from environment/config, not hard-coded in business code.

## Observability and operations upgrades

- Request ID middleware attaches `x-request-id` to responses.
- Health checks include app/version/request ID.
- Generated projects include Docker, CI, Makefile, and pre-commit scaffolding.
- Generated `pyproject.toml` includes pytest, ruff, and mypy configuration.

## Testing upgrades

- Generated tests now use factories and real FastAPI `TestClient` behavior.
- Authentication-required behavior is tested.
- Successful create/list behavior is tested against the generated API contract.
- Duplicate unique-field behavior is tested only when the SML model actually declares a unique field.
- Invalid payload/domain validation behavior is tested.
- In-memory target tests reset repository state in test fixtures without adding test-only production APIs.

## Deliberate V1 boundary

The target remains synchronous SQLAlchemy by default. This is intentional for the V1 production slice because it keeps dependency footprint, generated code complexity, and runtime validation stable. The next senior-level extension should add an explicit `python.fastapi.async_sqlalchemy` target policy rather than silently mixing async and sync patterns.
