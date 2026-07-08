# V1.3 General Domain Foundation Generator

V1.3 generalizes the project from a single inventory vertical slice into a reusable semantic app-foundation generation system.

The core product is not an inventory SaaS. Inventory remains a benchmark and fixture. The product is a general-purpose compiler that can take an application idea, map it into a structured app foundation, negotiate capabilities, render SML, validate semantics, deterministically generate a FastAPI backend foundation, and run acceptance gates.

## Core pipeline

```text
Prompt
  -> AppFoundationPlan
  -> Domain pack selection
  -> Capability negotiation
  -> SML rendering
  -> SML parser / semantic analyzer
  -> symbolic facts and proofs
  -> deterministic target pack
  -> generated FastAPI backend
  -> quality gates
```

LLM providers may draft SML or app-foundation intent, but final source generation remains compiler-owned.

## Generalized domain primitives

The semantic surface now supports generalized application concepts, including:

```text
Capability
Tenant
Audit
Role
Permission
Relationship
Workflow
StateMachine
BusinessRule
Invariant
Report
Integration
```

These concepts are intentionally domain-neutral. Inventory, HR, CRM, ticketing, school records, procurement, and expense workflows are represented as combinations of the same primitives rather than as one-off compiler hacks.

## Domain-pack architecture

V1.3 adds a domain pack registry under `src/ssm/domain_packs`.

Current pack families include:

```text
generic_crud
workflow_approval
inventory
hr
expense
crm
procurement
ticketing
school
```

Domain packs describe supported semantics, workflow families, default roles, route families, SaaS primitives, and capability limitations. The planner and negotiator use these packs to determine whether a requested app is supported, supported with assumptions, partially supported, or unsupported.

## AppFoundationPlan

`AppFoundationPlan` is the new pre-SML planning representation. It captures:

```text
app_type
domain_pack_candidates
entities
relationships
roles
workflows
business_rules
routes
reports
tenant/audit flags
nonfunctional requirements
unsupported features
assumptions
questions
```

This makes the system general-purpose. Instead of asking the model to write arbitrary SML directly, the system can first form a typed application foundation and then render validated SML.

## Capability negotiation

The negotiator validates a plan or SML document against supported compiler capabilities. It checks for unsupported methods, invalid paths, unresolved relationships, missing entities, and unsupported external integrations.

Statuses:

```text
SUPPORTED
SUPPORTED_WITH_ASSUMPTIONS
PARTIALLY_SUPPORTED
UNSUPPORTED
```

This prevents unsupported features from silently becoming weak generated code.

## Full CRUD and route hardening

The deterministic FastAPI target now supports common route families beyond list/create:

```text
GET /resources/{id}
PATCH /resources/{id}
PUT /resources/{id}
DELETE /resources/{id}
```

Generated repositories, services, routes, tests, OpenAPI assertions, and mypy-clean return types are emitted for these route families.

This resolves the earlier full-CRUD DeepSeek regression where typed routes had compiled but produced placeholder-style return values.

## Generated SaaS foundation features

Generated applications now include additional SaaS foundation pieces:

```text
/healthz
/readyz with database check for SQLAlchemy builds
request IDs
structured logging
JWT auth
OpenAPI contract tests
coverage thresholds
load-smoke tests
Dockerfile
Docker Compose
GitHub Actions
PostgreSQL integration path
Alembic migrations
docs/domain_foundation.md
```

Tenant and audit semantics are represented in SML and domain foundation documentation. Full tenant-scoped repository enforcement and generated audit persistence remain the next hardening layer.

## Multi-domain benchmarks

The repository now includes app-foundation benchmark examples for:

```text
inventory_api
todo_api
hr_leave_api
expense_approval_api
crm_pipeline_api
ticketing_api
school_records_api
```

These examples are used to prove that the compiler is no longer only an inventory generator.

## New CLI commands

Plan an app foundation from a natural-language prompt:

```bash
python -m ssm.cli.main plan \
  --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, and audit logs." \
  --emit-sml \
  --out build/hr_leave/project.sml.md
```

Negotiate capability support:

```bash
python -m ssm.cli.main negotiate --file build/hr_leave/project.sml.md
```

Compile the generated SML:

```bash
python -m ssm.cli.main compile build/hr_leave/project.sml.md --out build/hr_leave_api
```

Run one-command online build through the gated provider layer:

```bash
RUN_ONLINE_AI=1 SSM_AGENT_MODE=online SSM_LLM_PROVIDER=deepseek \
python -m ssm.cli.main online-build \
  --agent-mode online \
  --provider deepseek \
  --model deepseek-chat \
  --prompt "Build an HR leave approval SaaS with employees, leave requests, manager approval, leave balance rules, tenant isolation, and audit logs." \
  --out build/hr_leave_online
```

## Version boundary

V1.3 should be presented as:

```text
General-purpose semantic app foundation generator with deterministic backend code generation and gated online drafting.
```

It should not be presented as a finished generator for every possible enterprise app. Unsupported integrations and unsupported semantics are expected to be rejected through capability negotiation.

## Next hardening layer

The next version should focus on:

```text
relationship-aware SQLAlchemy foreign keys
workflow action route generation
persistent audit log generation
tenant-scoped repository filtering
RBAC enforcement from SML roles/permissions
online-build quality-gate execution with accept/reject summaries
```
