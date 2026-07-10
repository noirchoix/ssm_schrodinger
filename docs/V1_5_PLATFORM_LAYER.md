# V1.5.0-dev Platform Layer

V1.5.0-dev builds on the locked V1.3.2 general domain foundation compiler. The product identity remains unchanged: SSM is a semantic app foundation compiler, not a cognition-runtime compiler. The Auto-inspired additions are limited to release trust, contracts, provenance, bounded repair traces, SaaS primitives, workflow runtime scaffolding, and generated admin UI scaffolding.

## Implemented phases

### Phase A — Trust layer

Every generated FastAPI app now includes deterministic evidence records:

- `generated_app_manifest.json`
- `app_contract.json`
- `eval_run.json`
- `capability_report.json`
- `assumptions.json`
- `unsupported_features.json`
- `provenance_hashes.json`
- `evidence_bundle.json`
- `docs/release_evidence.md`

The compiler also exposes an evidence validator through:

```bash
python -m ssm.cli.main evidence-check build/generated_app
```

### Phase B — SaaS primitives

Generated apps now include a platform module:

```text
app/platform/tenancy.py
app/platform/rbac.py
app/platform/audit.py
app/api/routes/platform.py
app/cli/seed_admin.py
```

The generated platform API exposes manifest, contract, capability, tenant, RBAC, audit, and workflow endpoints.

### Phase C — Workflow runtime

Workflow sections now lower into generated workflow metadata and transition checks. The runtime exposes workflow listing and transition endpoints. This is a generated transition runtime, not yet a full business-process orchestration engine.

### Phase D — Online repair loop

`online-build` now supports bounded repair attempts and writes `repair_trace.json`.

```bash
python -m ssm.cli.main online-build \
  --agent-mode online \
  --provider mock \
  --model mock \
  --prompt "Build a FastAPI inventory API with PostgreSQL, JWT auth, and CRUD." \
  --out build/online_mock \
  --quality-gates \
  --repair-attempts 1
```

By default, internal online-build gates are fast deterministic gates: evidence-check, Ruff, format check, compileall, and Bandit. The release E2E script runs the full secondary generated-app pass, including pytest and mypy, after the online app is written. Set `SSM_ONLINE_FULL_GATES=1` to include pytest and mypy inside the repair loop.

### Phase E — Admin UI shell

Generated apps now include a static admin UI scaffold:

```text
admin/package.json
admin/index.html
admin/src/apiClient.ts
admin/src/App.tsx
admin/README.md
```

The UI is a generated shell for CRUD/platform inspection. It is not yet a full production frontend application.

## Known limitations

- Tenant context propagation exists, but entity repositories are not yet fully tenant-filtered across all generated domain models.
- Audit capture is in-memory in generated platform scaffolding; DB-backed audit persistence is a future hardening layer.
- Workflow runtime supports transition metadata and action checks, but not full process orchestration or business-rule evaluation.
- Admin UI is static scaffold output; full build tooling and richer interaction are planned for later.
- Live provider repair was architected and mock-tested; live provider validation remains environment/key dependent.
