# SSM-Bench v2 — End-to-End Semantic Evolution Benchmark

## Purpose

SSM-Bench v2 is a frozen, evaluator-separated benchmark for the complete SSM semantic pipeline. Each case starts from natural-language intent and is evaluated across RequirementsIR, foundation planning, architecture resolution, capability composition/negotiation, CanonicalSemanticContext, SML, semantic conformance, SIR/target generation, and generated runtime behaviour.

The benchmark is intentionally not a collection of thirty identical README templates. It contains structured READMEs, semi-structured product requirements, stakeholder notes, narrative requests, bullet notes, ambiguous briefs, contradictory briefs, and unsupported requests. The aim is to test semantic extraction and fail-closed behaviour rather than prompt-template memorisation.

## Case isolation rule

Each case contains four files:

- `input.md` — the only file allowed to enter the product compiler or online synthesis path.
- `oracle.json` — independent semantic obligations authored from the source intent.
- `runtime_contract.json` — independent black-box runtime checks.
- `metadata.json` — case labels and analysis slices.

Oracle, runtime-contract, and metadata contents must never be included in the synthesis prompt or CanonicalSemanticContext. This prevents evaluator leakage and circular validation.

## Coverage design

The 30 cases jointly exercise every RequirementsIR kind: actor, entity, workflow, business rule, integration, security, stack, capability, non-functional requirement, constraint, report, and use case. They also cover PostgreSQL and in-memory persistence; public and JWT-protected APIs; single- and multi-tenant semantics; workflows; local, multi-field, and contextual rules; production and contract-only capabilities; explicit ambiguity; contradiction; unsupported requirements; domain inference; and multiple source-document styles.

The benchmark deliberately contains requirements that the current deterministic front-end may not preserve perfectly. Qualification therefore distinguishes **harness validity** from **system semantic performance**. A low oracle score is a measured result, not a reason to rewrite the benchmark to match the current implementation.

## Qualification criterion

The corpus is eligible for freezing when:

1. all 30 case packs validate structurally;
2. the evaluator completes all cases without harness/instrumentation errors;
3. expected fail-closed cases are measurable as rejections;
4. independent runtime probes execute wherever a generated application exists; and
5. corpus and qualification evidence are content-addressed.

Compiler semantic misses remain recorded as baseline limitations and are not tuned away after observation.
