# SSM V2.0 Acceptance Matrix

Version under evaluation: `2.0.0.dev0`

The V2.0 product-platform gate is the cumulative acceptance boundary for the V1.3.2–V1.5 implementation line. A criterion is accepted only when it is represented in generated output and exercised by deterministic tests or the dedicated `scripts/test_v20_e2e.sh` release gate.

| Phase | Acceptance criterion | Implementation | Release evidence |
|---|---|---|---|
| A — Trust | Generated app manifest | `generated_app_manifest.json` schema 2.0 | Evidence tests and `evidence-check` |
| A — Trust | App contract | `app_contract.json` with entities, routes, SaaS, workflow, and admin contracts | Evidence tests |
| A — Trust | Eval run and capability report | `eval_run.json`, `capability_report.json` | Evidence bundle validation |
| A — Trust | Assumptions and unsupported features | Dedicated JSON records | Evidence bundle validation |
| A — Trust | Provenance hashes | SHA-256 for every non-evidence generated file | Tamper-detection framework test and generated evidence test |
| A — Trust | Release evidence bundle | JSON bundle plus `docs/release_evidence.md` | `evidence-check` |
| B — SaaS | Tenant model | Generated `platform_tenants` persistence model for SQLAlchemy builds | Alembic 0002 cycle |
| B — SaaS | Tenant propagation | Header dependency injects tenant context; client payload cannot select tenant | Generated API tests |
| B — SaaS | Tenant-scoped repositories | SQLAlchemy and in-memory list/get/create/update/delete and uniqueness are tenant scoped | Cross-tenant API and service tests |
| B — SaaS | RBAC role/permission runtime | Generated role map, JWT roles/scopes, and route permission enforcement | Read-only write-rejection test |
| B — SaaS | Audit event model | Generated typed audit event API | Platform tests |
| B — SaaS | DB-backed audit persistence | SQLAlchemy `platform_audit_events` model and service mutation audit writes | New-session persistence test |
| B — SaaS | Seed/admin CLI | Generated tenant seed and admin-token CLI | Generated CLI execution test |
| B — SaaS | Readiness | Database connectivity plus evidence-record readiness checks | `/readyz` test |
| C — Workflow | Workflow/state definitions | Deterministic workflow metadata and transition map | Generated workflow module |
| C — Workflow | Persistent state | `platform_workflow_states` for SQLAlchemy; tenant-keyed memory state otherwise | Repeated-request transition test |
| C — Workflow | Allowed transition checks | Exact current-state/action edge enforcement | Transition acceptance/rejection tests |
| C — Workflow | Business-rule runtime | Safe AST evaluator for boolean, comparison, dotted-context, and basic arithmetic expressions | Allowed and rule-rejected transition tests |
| C — Workflow | Workflow action routes | Generated `/platform/workflows/...` route | Platform API tests |
| D — Repair | Failed generation diagnosis | Compiler/capability/gate diagnostics persisted in trace | Seeded repair test |
| D — Repair | Repair prompt construction | Prior exact issue appended to the next model prompt | Builder test |
| D — Repair | Bounded retries | Explicit `repair_attempts` limit | Builder and E2E tests |
| D — Repair | Trace persistence | `repair_trace.json` schema 2.0 | Trace assertions |
| D — Repair | Accepted/rejected status | Final status and attempt count persisted | Trace assertions |
| D — Repair | Live-provider validation | `--initial-draft` forces a real provider repair after attempt-one compiler rejection | Optional DeepSeek stage in V2.0 E2E |
| E — UI | Admin frontend shell | Generated React 19/Vite application | Static and production build tests |
| E — UI | CRUD pages | Contract-driven list/create/update/delete page | TypeScript typecheck and Vite build |
| E — UI | OpenAPI client | Generated typed OpenAPI loader | Static output check and build |
| E — UI | Auth-aware request wrapper | Bearer token and tenant header injection | Static test and TypeScript build |
| E — UI | Run documentation | Generated admin/backend instructions and Make targets | Generated README checks |
| E — UI | Production frontend pipeline | Node setup in generated CI, typecheck, and Vite production build | `npm run typecheck`, `npm run build`, `dist/index.html` |

## Release interpretation

`2.0.0.dev0` means the implementation and local deterministic V2.0 product-platform gates are available. Promotion to a final `2.0.0` tag requires the dedicated E2E run to pass with the live-provider gate enabled in the release environment and the resulting log to be retained as release evidence.
