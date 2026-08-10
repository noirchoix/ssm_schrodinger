# V2.6.0-dev.2 — Unified Canonical Semantic Context and Constrained Online SML Synthesis

## Status

Implementation target: `2.6.0.dev2`.

This milestone consolidates the product compiler and online drafting path around one deterministic semantic front end. It does not make the LLM the source of product semantics. The LLM is an optional SML synthesizer operating inside a previously negotiated semantic envelope.

## Architectural invariant

> No online provider receives unconstrained raw intent as the sole semantic authority. Every online SML proposal is conditioned on a deterministic `CanonicalSemanticContext` derived from the same persisted input and must pass `SemanticConformanceVerifier` before entering `SSMCompiler`.

The canonical flow is:

```text
raw intent / input.md
        ↓
RequirementsIR
        ↓
AppFoundationPlan
        ↓
ArchitecturePlan
        ↓
CapabilityCompositionResult
        ↓
CapabilityNegotiationResult
        ↓
CanonicalSemanticContext
        ↓
   ┌────┴─────────────────────────────┐
   │                                  │
OFFLINE                            ONLINE
   │                                  │
FoundationSMLRenderer          constrained LLM
   │                                  │
   │                           candidate SML
   └──────────────┬───────────────────┘
                  ↓
      SemanticConformanceVerifier
                  ↓
    candidate capability consistency
                  ↓
             SSMCompiler
                  ↓
        SIR / symbolic resolution
                  ↓
      deterministic target generation
                  ↓
       generated application/evidence
```

## Input-document boundary

`online-build --prompt` and `online-build --file` converge at a run-local `input.md` artifact. The exact source bytes are hashed and become part of the generation identity. File input is read and persisted unchanged as UTF-8 text; direct prompt input is persisted as the equivalent run-local document.

The raw source remains available to the deterministic requirements/foundation stages and to local provenance. It is not embedded as free-form provider authority after canonical collapse.

## CanonicalSemanticContext

`CanonicalSemanticContext` contains:

- source name and SHA-256 identity;
- typed `RequirementsIR`;
- `AppFoundationPlan`;
- `ArchitecturePlan`;
- capability composition;
- capability negotiation;
- protected semantics;
- unresolved semantics;
- context-integrity issues;
- semantic fingerprint.

Its `llm_payload()` is deliberately bounded. It removes the raw source text and free-form foundation description while retaining structured requirements and negotiated semantics. This prevents the online provider from receiving a second unconstrained opportunity to reinterpret the original request.

## Fail-closed pre-provider boundary

The online build exits before provider invocation when the canonical context contains a blocking condition, including:

- contradictory high-impact requirements;
- blocking ambiguities;
- unsupported capability composition or negotiation;
- canonical context integrity errors such as rules/workflows/relationships referencing unknown entities.

This makes capability honesty and unresolved uncertainty deterministic upstream decisions rather than LLM discretion.

## SemanticConformanceVerifier

Compiler admissibility and semantic fidelity are distinct gates. A candidate can parse successfully and still omit or mutate required product semantics.

The verifier therefore checks the candidate structurally against the canonical context before `SSMCompiler` is allowed to run. Current conformance families include:

| Family | Examples |
|---|---|
| Stack | backend, database, authentication |
| Platform | tenancy and audit enablement |
| Capabilities | required canonical domain packs |
| Domain model | entities, Create models, required field descriptors, forbidden non-canonical base entities |
| Relationships | source, target, cardinality, requiredness |
| Roles | explicitly requested actors/roles |
| Workflows | entity binding, states, transitions, actions |
| Rules | business rules/invariants by entity and normalized expression |
| Routes | method, path, auth, body compatibility, returns |
| Reports | required report semantics |
| Scaffolding | required policy and architecture constraints |

The verifier is intentionally semantic/structural rather than byte-for-byte. Representationally admissible derived Update schemas and canonical Create-vs-Update PATCH body variants can be accepted without requiring the online SML to equal the offline renderer output.

## Repair ordering

Online bounded repair now has explicit stages:

```text
candidate SML
   ↓
parse / draft-shape validation
   ↓
semantic_conformance
   ↓
candidate_capability_consistency
   ↓
compile
   ↓
quality_gates
```

Structured semantic-conformance diagnostics are returned as repair feedback. The repair model is not asked to change product requirements; it is asked to repair the SML representation so that it satisfies the same canonical context.

A seeded non-conformant candidate is therefore expected to fail at `semantic_conformance`, not at `compile`.

## Offline/online symmetry

Offline generation uses `FoundationSMLRenderer` after the canonical context is created. Its output passes through the same `SemanticConformanceVerifier` before compilation.

This yields one semantic policy boundary for both strategies:

```text
same input
→ same canonical context
→ [offline renderer | online synthesizer]
→ same conformance verifier
→ same deterministic compiler
```

This symmetry is required for controlled comparisons of synthesis strategy.

## Observation and evidence

Online builds now persist:

- `input.md`;
- `requirements_ir.json`;
- `foundation_plan.json`;
- `architecture_plan.json`;
- `capability_composition.json`;
- `capability_negotiation.json`;
- `canonical_semantic_context.json`;
- `semantic_conformance.json`;
- `sir.json`;
- per-attempt semantic-conformance reports;
- `repair_trace.json` with diagnostic codes;
- `generation_trace.jsonl`;
- `generation_run.json`.

Generation-run stage fingerprints include the canonical semantic context and semantic conformance result. Online records also expose measured `semantic_conformance_pass` evidence.

## Research boundary

The architecture creates an explicit stochastic boundary for later controlled experiments:

```text
D0 input normalization
D1 requirements
D2 foundation
D3 architecture
D4 capabilities
D5 negotiation
D6 canonical semantic context
-------------------------------- stochastic boundary
P1 candidate SML synthesis        [online only]
-------------------------------- deterministic boundary resumes
D7 semantic conformance
D8 SML/SIR compiler analysis
D9 deterministic target generation
D10 generated product/evidence
```

For offline mode, P1 is replaced by deterministic SML rendering. This permits matched experiments to hold the canonical semantic interpretation constant while varying only the synthesis strategy/provider/model.

## Non-goals

This milestone does not:

- let an LLM modify RequirementsIR, foundation, architecture, capability negotiation, or the canonical context;
- treat model output as final source code;
- weaken deterministic compiler validation;
- silently resolve contradictions or unsupported capabilities;
- claim that semantic conformance is a formal proof of full behavioural equivalence;
- replace independent runtime contracts or later benchmark oracles;
- claim live-provider release certification until the live E2E gate is rerun against this exact dev.2 build.

## Validation targets

Internal deterministic validation:

```bash
python -m compileall -q src tests
python -m pytest -q
```

Authoritative local release validation in the project development environment:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
RUN_DEEPSEEK_LIVE=1 bash scripts/test_v20_e2e.sh
bash scripts/test_auto_research_e2e.sh
```

Only after those gates pass should dev.2 be frozen as the Study 1 research instrument.
