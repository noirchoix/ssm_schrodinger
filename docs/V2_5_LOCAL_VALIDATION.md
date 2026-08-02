# V2.5 Local Validation Record

## Scope

This record covers the V2.1–V2.5 Schrödinger roadmap implementation layered above the existing deterministic SML/SIR compiler. The validation confirms that the high-level intent-collapse pipeline does not bypass or weaken the existing compiler authority.

Validated pipeline:

```text
README or free-form intent
→ RequirementsIR
→ AppFoundationPlan
→ constrained ArchitecturePlan
→ capability composition and negotiation
→ architecture-aware SML
→ existing deterministic SSMCompiler
→ generated application
→ incremental artifact emission
→ variability and senior-grade certification
```

## Environment

- Runtime version: `2.5.0.dev0`
- Existing V2.0 deterministic compiler retained as the source-generation authority
- Python quality tools: pytest, Ruff, mypy, compileall
- Generated target exercised: FastAPI with the existing supported PostgreSQL/InMemory, JWT, tenant, RBAC, audit, workflow, evidence, and React-admin profile

## Framework validation

```text
pytest: 50 passed
ruff check: passed
ruff format --check: passed; 71 files already formatted
mypy: passed; no issues in 61 source files
```

The framework tests include the pre-existing compiler regression suite and the new roadmap tests for:

- deterministic and traceable RequirementsIR extraction;
- rejection of vague generic application descriptions;
- contradiction blocking;
- singular constrained architecture resolution;
- honest partial-capability reporting;
- repair-boundary enforcement;
- full product artifact generation and incremental re-emission;
- CLI integration.

## V2.5 collapse-gate validation

The dedicated gate `scripts/test_v25_e2e.sh` passed end to end.

Observed results:

```text
requirements extraction: passed
foundation planning: passed
architecture resolution: layered_modular_monolith selected
capability composition: passed
capability negotiation: SUPPORTED_WITH_ASSUMPTIONS
SML compilation: passed
generated application files: 94
evidence validation: passed
evidence files hashed: 84
certification status: CONDITIONAL_SUPPORTED_PROFILE
semantic variance score across repeated runs: 0.0
final result: ALL V2.5 SCHRODINGER COLLAPSE GATES PASSED
```

The conditional certification is intentional. Assumptions and incomplete product capabilities remain visible instead of being silently promoted to full production support.

## Generated-application validation

The application generated from `examples/intent_inputs/hr_leave_readme.md` passed the existing generated-project gates:

```text
pytest: 29 passed, 1 skipped
coverage: 85.81%
ruff check: passed
ruff format --check: passed
mypy: passed; no issues in 44 source files
compileall: passed
```

The generated project also retained the existing evidence records, provenance hashes, platform primitives, database migration structure, and generated admin application contract.

## Incremental-compilation validation

The incremental writer was tested against both unchanged regeneration and manual generated-source drift.

Confirmed behavior:

- repeated identical builds do not rewrite unchanged artifacts;
- content hashes are verified against the actual files on disk rather than trusting only the previous index;
- a manually altered generated file is detected as modified;
- the deterministic compiler output restores the altered file;
- the artifact diff and unchanged-artifact proof are emitted.

The current implementation performs deterministic target compilation first and incrementally emits only changed artifacts. Fine-grained target generation by individual semantic node is a future optimization, not a claimed capability of this release.

## Variability and trust interpretation

This release proves the following bounded claim:

> For supported application descriptions within the declared FastAPI-oriented capability profile, the same normalized intent produces semantically equivalent requirements, foundation, architecture, capability, SML, and generated-contract decisions across repeated runs, while unsupported, ambiguous, inferred, and assumption-dependent requirements remain explicit.

It does not claim that every arbitrary README can be converted into a production-complete application. Vague or contradictory descriptions are blocked, and scaffold or contract-only capabilities remain classified as partial.

## Known non-blocking limitations

1. Capability packs such as background jobs, notifications, idempotency, webhooks, and retention currently establish composition contracts and support classifications; not all provide complete production runtimes.
2. Incremental emission is content-addressed at the artifact level after deterministic compilation; generation itself is not yet node-by-node incremental.
3. Requirements extraction is deterministic and conservative but is not a complete natural-language requirements-engineering substitute.
4. Certification applies only to the declared supported profile and is not a universal senior-engineering guarantee.
5. Existing dependency deprecation warnings, where present, remain separate maintenance items and do not alter the roadmap validation result.
