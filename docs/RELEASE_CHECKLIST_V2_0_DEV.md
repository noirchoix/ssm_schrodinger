# V2.0.0-dev Release Checklist

## Deterministic framework

- [ ] Framework tests and coverage pass.
- [ ] Ruff check and format check pass.
- [ ] Mypy and compileall pass.
- [ ] Bandit passes.
- [ ] Dependency audit passes when enabled.

## Trust and evidence

- [ ] All eight evidence records are generated.
- [ ] Evidence schema 2.0 validation passes.
- [ ] Generated-file SHA-256 provenance validates.
- [ ] Tampering is detected.

## SaaS runtime

- [ ] Tenant context is propagated.
- [ ] SQLAlchemy and in-memory repositories enforce tenant isolation.
- [ ] Tenant-relative uniqueness passes.
- [ ] RBAC rejects unauthorized writes.
- [ ] Audit events persist across database sessions.
- [ ] Seed/admin CLI executes successfully.
- [ ] `/readyz` reports database and evidence readiness.

## Workflow runtime

- [ ] Exact transition edges are enforced.
- [ ] Workflow state persists across requests.
- [ ] Business rules can accept and reject transitions.
- [ ] Workflow mutations emit audit events.

## Admin frontend

- [ ] Generated admin contract and CRUD pages exist.
- [ ] TypeScript strict typecheck passes.
- [ ] Vite production build passes.
- [ ] `admin/dist/index.html` exists.
- [ ] Generated CI includes Node/typecheck/build steps.

## Repair loop

- [ ] Seeded mock attempt one is rejected by the compiler.
- [ ] Mock provider repairs and accepts attempt two.
- [ ] Repair trace schema 2.0 records both outcomes.
- [ ] Live DeepSeek forced-repair gate passes for final 2.0.0 promotion.

## Final release

- [ ] Secret scan passes.
- [ ] `build/e2e_v20/release_gate_summary.json` is retained.
- [ ] Full E2E log is retained.
- [ ] Runtime version is changed from `2.0.0.dev0` to `2.0.0` only after live certification.
