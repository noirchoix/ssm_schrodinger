# SSM V2.6.0-dev.2 Implementation Report

## Milestone

**V2.6.0-dev.2 — Unified Canonical Semantic Context + Constrained Online SML Synthesis**

This milestone consolidates the deterministic product compiler and bounded online drafting path around one canonical semantic front end.

The release invariant is:

> Raw intent is interpreted by deterministic SSM stages before any online model is invoked. The online model receives a bounded `CanonicalSemanticContext`, may synthesize SML only, and its candidate must pass deterministic semantic conformance before `SSMCompiler` can execute.

## Final pipeline

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
    ├── offline: FoundationSMLRenderer
    │
    └── online: constrained LLM → candidate SML
                    ↓
          SemanticConformanceVerifier
                    ↓
       candidate capability consistency
                    ↓
                SSMCompiler
                    ↓
                  SIR
                    ↓
      deterministic target generation
                    ↓
      generated application + evidence
```

## Implementation changes

### Canonical semantic authority

Added `CanonicalSemanticContext` in `ssm.product.schemas` and construction logic in `ssm.product.semantic_context`.

The context contains source identity, RequirementsIR, foundation, architecture, capability composition, capability negotiation, protected semantics, unresolved semantics, integrity issues, and a content-addressed semantic fingerprint.

The provider-facing `llm_payload()` excludes raw input text and free-form foundation description. Online providers receive structured canonical semantics and source identity instead of unconstrained raw intent.

### Shared deterministic front end

`SchrodingerProductCompiler.prepare_semantic_context()` now owns the shared pre-synthesis path:

1. requirements extraction;
2. foundation planning;
3. architecture resolution;
4. capability composition;
5. capability negotiation;
6. canonical semantic context construction.

`collapse_text()` uses that context, performs deterministic SML rendering, then verifies the rendered SML through the same semantic conformance boundary used by online synthesis.

### Semantic conformance gate

Added `SemanticConformanceVerifier` with typed diagnostics. The verifier currently protects:

- backend/database/auth stack;
- tenancy and audit enablement;
- required domain capabilities;
- canonical data models and Create schemas;
- field descriptors;
- non-canonical data-model invention;
- relationships and relationship requiredness;
- explicit roles;
- workflows, states, transitions, and actions;
- executable business rules/invariants;
- canonical route contracts and non-canonical route invention;
- reports;
- error-handling policy;
- canonical architecture constraint.

Compiler admissibility and semantic conformance are intentionally separate. Candidate SML is parsed first, semantically checked second, and only then admitted to capability consistency and `SSMCompiler`.

### Online path consolidation

`OnlineDraftService` now synthesizes from canonical context. Direct `draft(prompt)` calls first canonicalize the input. Direct `draft_context(context)` calls fail closed if the supplied context contains blocking contradictions, ambiguities, unsupported capability results, or integrity errors.

`OnlineBuildService` now:

- persists the exact request as run-local `input.md`;
- uses stable logical source identity `input.md` so canonical fingerprints do not depend on output-directory paths;
- writes deterministic pre-LLM artifacts;
- rejects blocked canonical contexts before provider construction/invocation;
- records per-attempt semantic-conformance evidence;
- feeds structured semantic diagnostics into bounded repair;
- runs candidate capability consistency after conformance;
- invokes `SSMCompiler` only for conformant candidates;
- persists `sir.json` after deterministic compilation.

### Repair-stage semantics

The bounded repair trace now distinguishes:

```text
online_draft
semantic_conformance
candidate_capability_consistency
compile
quality_gates
```

A seeded candidate that omits canonical semantics is expected to fail at `semantic_conformance`, not at `compile`.

### Research instrumentation

Offline and online generation records now include canonical-context and semantic-conformance fingerprints. Online records also include `sir` and measured `semantic_conformance_pass` evidence.

The evolution-assay stage order now includes:

```text
requirements
foundation
architecture
capabilities
negotiation
canonical_semantic_context
sml
semantic_conformance
sir
generated_tree
quality_gates
```

This allows first-changed-stage attribution to identify whether a release changed before the stochastic boundary, at candidate SML synthesis, at semantic verification, or downstream in compilation/generation.

### Planner consistency hardening

Two deterministic planning defects exposed by the new fail-closed context boundary were corrected:

- inventory requests containing the phrase `Docker support` can no longer be misclassified as ticketing solely because of the word `support`;
- generic approval workflows and supplier relationships are no longer emitted with references to undeclared entities.

The frozen SSM-Bench v1 corpus is not modified.

## New/persisted run artifacts

Canonical/offline runs persist, where applicable:

- `requirements_ir.json`
- `foundation_plan.json`
- `architecture_plan.json`
- `capability_composition.json`
- `capability_negotiation.json`
- `canonical_semantic_context.json`
- `project.sml.md`
- `semantic_conformance.json`
- `sir.json`
- generated application/evidence
- `generation_trace.jsonl`
- `generation_run.json`

Online runs additionally persist:

- `input.md`
- `semantic_conformance_attempt_XX.json`
- `repair_trace.json` with conformance diagnostic codes.

## Test additions

A dedicated canonical-context test suite now verifies:

- deterministic/source-addressed canonical context construction;
- shared offline conformance;
- rejection when canonical entities/routes are dropped;
- rejection of tenancy drift;
- provider conditioning on canonical context rather than raw request text;
- canonical artifact/evidence persistence;
- pre-provider fail-closed contradiction handling;
- `online-build --file` input persistence;
- inventory `Docker support` routing regression;
- direct service fail-closed behavior;
- output-directory-independent canonical identity;
- rejection of non-canonical model/route invention;
- rejection of architecture/error-policy drift;
- no dangling planner workflow/relationship references;
- all 30 frozen SSM-Bench v1 inputs crossing the canonical boundary and compiling.

Auto Research tests also verify the new stage fingerprints and canonical-context-first attribution ordering.

## Internal validation completed in the artifact environment

```text
runtime version                     2.6.0.dev2
compileall                          PASS
bash syntax: test_v20_e2e.sh       PASS
bash syntax: Auto Research E2E     PASS
pytest                              84 passed
SSM-Bench v1 manifest              valid, 30 cases, frozen digest unchanged
SSM-Bench v1 canonical/compile     30 / 30
mock canonical online build        ACCEPTED
seeded mock repair                 semantic_conformance reject → accepted attempt 2
Auto Research E2E                  PASS
Auto determinism census            22 / 22 witnessed deterministic
Auto divergent observations        0
Auto replay                         11 matched, equivalent=true
Auto evolution assay               NO_MATERIAL_CHANGE
```

The frozen SSM-Bench v1 identifiers remain unchanged:

```text
benchmark_id: sha256:840a6ad178ed7c4c2d157e0ccfc0d1f74fb848201e73375f015478b57da375fe
corpus_sha256: 650d129b6602fd024ff94e8d292468df905da303698caccc1d9a43e8e14706bf
```

## Validation not claimed in this artifact environment

Ruff and mypy are not installed in the execution environment used to assemble this artifact, and external-provider internet access is unavailable. Therefore this report does **not** claim:

- authoritative Ruff validation;
- authoritative mypy validation;
- live DeepSeek certification for dev.2;
- full `scripts/test_v20_e2e.sh` completion for dev.2.

Those gates must be run in the project development venv before dev.2 is frozen as the Study 1 research instrument.

Recommended authoritative sequence:

```bash
python -m compileall -q src tests
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
python -m pytest -q
RUN_DEEPSEEK_LIVE=1 bash scripts/test_v20_e2e.sh
bash scripts/test_auto_research_e2e.sh
```

The V2.0 E2E script has been updated for the new architecture: the deliberately incomplete seed is now expected to fail at `semantic_conformance`, and a successful live run terminates with `LIVE DEEPSEEK FORCED-CONFORMANCE-REPAIR GATE PASSED`.

## Research-readiness consequence

V2.6.0-dev.2 creates the experiment boundary required for the next Study 1 benchmark design. The same input can now be deterministically collapsed to one canonical semantic context and then evaluated under either deterministic offline rendering or probabilistic online SML synthesis. This permits the synthesis strategy/provider/model to become an explicit experimental variable while holding upstream semantic interpretation constant.

SSM-Bench v2 and the 30-case Study 1 oracle/contract corpus are intentionally **not** included in this milestone. They should be created only after the authoritative dev.2 release gates are green and the research instrument is frozen.
