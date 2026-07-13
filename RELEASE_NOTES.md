# SSM V2.0.0-dev Product Platform Notes

`2.0.0.dev0` is the acceptance branch for the product-platform boundary. It combines the locked general-domain foundation with schema-2.0 release evidence, tenant-enforced SaaS repositories, RBAC, database audit persistence, persistent workflow/business-rule runtime, bounded online repair validation, and a production-buildable React/Vite admin client.

The final `2.0.0` tag remains conditional on a retained `scripts/test_v20_e2e.sh` run with `RUN_DEEPSEEK_LIVE=1`. Local deterministic and mock-provider gates can certify `2.0.0.dev0`; they do not substitute for the external-provider release gate.

See:

- `docs/V2_0_PLATFORM.md`
- `docs/V2_0_ACCEPTANCE_MATRIX.md`
- `docs/RELEASE_CHECKLIST_V2_0_DEV.md`

---

# SSM Framework v1.3.2 Release Notes

## Release status

`v1.3.2` is the version-lock release for the General Domain Foundation Generator line. It should be treated as the portfolio/developer-tool release that proves the project can move beyond a single inventory benchmark into a reusable app-foundation compiler flow.

The release target is:

```text
Prompt / app idea
→ AppFoundationPlan
→ domain-pack selection
→ capability negotiation
→ SML
→ semantic validation
→ deterministic FastAPI generation
→ generated-app quality gates
→ audit/secret checks
```

## What is locked in this version

- Generalized planning through `AppFoundationPlan`.
- Domain-pack registry for common application categories.
- Capability negotiation before deterministic code generation.
- Full CRUD route generation for generated FastAPI services.
- Multi-domain benchmark validation/compilation.
- Generated-app tests, coverage, Ruff, mypy, Bandit, pip-audit, compileall, and Alembic checks.
- Mock online-build acceptance loop.
- Boundary-aware secret scan that avoids false positives on ordinary slugs while still catching likely key material.
- E2E script with timestamped log capture.

## Known scope limits

- Live provider builds are supported through the provider layer but are not required for the default release gate.
- PostgreSQL integration is available through `RUN_POSTGRES=1`, but defaults to skipped for local developer convenience.
- Workflow semantics are represented in SML and planning, but a full workflow runtime engine is V1.4 scope.
- Tenant/RBAC/audit primitives are represented, but full tenant-scoped runtime enforcement is V1.4 scope.
- This is a backend foundation generator/compiler, not a complete no-code product.

## Version-lock command

From a clean extracted release root:

```bash
chmod +x scripts/test_v13_e2e.sh
./scripts/test_v13_e2e.sh
```

Expected final line:

```text
ALL V1.3.2 E2E GATES PASSED
```

## Git tagging

After the clean E2E gate passes:

```bash
git add .
git commit -m "Release v1.3.2 general domain foundation"
git tag -a v1.3.2 -m "SSM Framework v1.3.2 general domain foundation release"
git push origin main --follow-tags
```


# V1.5.0-dev Development Notes

V1.5.0-dev is a platform-layer development build. It should be treated as the next implementation branch after the locked V1.3.2 release, not as a stable lock.

The main product gain is trustable generated-app output: each generated backend now carries a manifest, app contract, capability report, provenance hashes, assumptions, unsupported features, eval run record, and evidence bundle. The generated app also includes platform primitives, workflow transition runtime, and a static admin UI shell.

Do not claim this version as full SaaS enforcement yet. Tenant propagation, RBAC metadata, audit capture, and workflow transitions are present; full tenant-scoped repositories, DB-backed audit, workflow orchestration, and a production frontend remain future hardening layers.
