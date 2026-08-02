# V2.1–V2.5 Schrödinger Roadmap Implementation

This development line extends the validated V2.0 compiler without replacing its deterministic SML/SIR authority.

## Pipeline

```text
README / prompt / PRD
→ RequirementsIR
→ AppFoundationPlan
→ constrained ArchitecturePlan
→ CapabilityComposition
→ SML
→ SIR / logic / latent resolution
→ deterministic FastAPI target
→ dependency graph / incremental artifact diff
→ variability and supported-profile certification
```

## V2.1 — Intent and Requirements IR

Implemented in `ssm.requirements`:

- README and free-text input adapter;
- stable requirement trace identifiers;
- explicit, inferred, and default provenance;
- contradiction detection for database, authentication, and tenancy choices;
- ambiguity and assumption registers;
- unsupported-feature visibility;
- canonical semantic fingerprints.

The extractor is deliberately conservative. It records defaults and does not treat inferred requirements as explicit user instructions.

## V2.2 — Foundation and Architecture Resolution

Implemented in `ssm.architecture` and the high-level product compiler:

- mandatory `AppFoundationPlan` after requirements normalization;
- modular layered-monolith architecture candidate;
- rejected direct-route and microservice alternatives with evidence;
- use-case, transaction-boundary, domain-event, integration-adapter, failure-model, and NFR records;
- deterministic architecture fingerprints.

The current target remains a FastAPI modular monolith. Architecture resolution cannot silently select microservices or distributed transactions.

## V2.3 — Capability Composition

Implemented in `ssm.capabilities`:

- capability-pack protocol;
- prerequisites, conflicts, guarantees, tests, evidence, assumptions, and implementation status;
- production-backed packs for RBAC, tenancy, audit, workflow, and observability;
- explicitly partial contract/scaffold packs for background jobs, notifications, idempotency, webhooks, and retention.

A partial pack is never reported as fully supported.

## V2.4 — Incremental Compilation and Repair

Implemented in `ssm.incremental`:

- cross-layer semantic dependency graph;
- content-addressed artifact index;
- incremental writer that changes only added/modified/removed artifacts;
- unchanged-artifact proof hash;
- failure classification and abstraction-aware repair routing;
- direct generated-source repair prohibition for semantic failures.

The current implementation recomputes the target result deterministically but performs incremental artifact emission. Fine-grained target regeneration can build on the dependency graph in a later target-pack revision.

## V2.5 — Variability and Senior-Grade Certification

Implemented in `ssm.certification`:

- repeated requirements, architecture, capability, SML, and generated-tree fingerprints;
- requirement coverage and explicit-requirement coverage;
- architecture consistency;
- capability-honesty scoring;
- unsupported-feature visibility;
- repair-boundary integrity;
- supported-profile certification status.

Certification is intentionally bounded to the declared FastAPI/PostgreSQL-or-InMemory/JWT modular-monolith profile. It does not claim that arbitrary application prose is automatically a complete production specification.

## CLI

```bash
python -m ssm.cli.main requirements --file README.md
python -m ssm.cli.main collapse-plan --file README.md --out build/collapse.json
python -m ssm.cli.main compile-intent --file README.md --out build/product
python -m ssm.cli.main certify-intent --file README.md
```

Use `--allow-partial` only when explicit partial/unsupported capability evidence is acceptable. The default path rejects blocking contradictions, blocking ambiguities, and unsupported foundation/capability negotiations.
