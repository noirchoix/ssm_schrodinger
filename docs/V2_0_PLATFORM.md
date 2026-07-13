# SSM V2.0 Product Platform

SSM V2.0 preserves the compiler-first architecture:

```text
Prompt or application idea
→ AppFoundationPlan
→ capability negotiation
→ SML
→ SIR and semantic validation
→ deterministic FastAPI, SaaS runtime, evidence, and admin-client generation
→ release gates
```

Models draft or repair SML only. Final Python, SQLAlchemy, Alembic, React, TypeScript, Docker, CI, and evidence artifacts remain deterministic compiler output.

## Product-platform boundary

The V2.0 boundary is reached when generated applications carry both a stable SaaS backend runtime and a buildable operator-facing admin client. The generated platform now includes tenant-enforced repositories, JWT/RBAC authorization, persistent audit events, persistent workflow state, exact transition checks, safe business-rule evaluation, readiness checks, seed/admin tooling, provenance-backed evidence records, and a React/Vite CRUD frontend.

## Tenant security contract

For tenant-enabled applications, `tenant_id` is server managed. It is injected from request context, never trusted from create/update payloads, and included in repository predicates for list, get, update, delete, and uniqueness checks. The same contract is generated for SQLAlchemy and in-memory repositories.

## Audit contract

SQLAlchemy applications persist audit events in `platform_audit_events`. CRUD services and workflow transitions write audit events inside the same database transaction as the domain mutation. Audit listing is tenant scoped. In-memory applications retain an equivalent deterministic API for local compiler validation.

## Workflow contract

A workflow transition is accepted only when the requested action matches an explicit edge from the persisted current state and all applicable business rules pass. State is keyed by tenant, workflow, and resource. Version increments provide an observable transition sequence, while `expected_state` supports optimistic state checks.

## Admin-client contract

Every generated application contains a React/Vite admin project with contract-driven resource pages, CRUD actions, an auth-aware and tenant-aware API wrapper, an OpenAPI loader, persistent local settings, TypeScript strict mode, and a production Vite build command. Generated CI and Make targets execute the frontend typecheck and build.

## Release gate

Run:

```bash
./scripts/test_v20_e2e.sh
```

For final external-provider certification:

```bash
RUN_DEEPSEEK_LIVE=1 ./scripts/test_v20_e2e.sh
```

The live stage begins from a deliberately invalid SML seed. A passing run therefore proves that a real provider receives a compiler diagnostic, repairs the SML within the bounded retry window, and produces an application that passes backend, evidence, migration, and frontend gates.
