# SSM Schrödinger Auto Research Integration

## Status

Implemented development baseline: `2.6.0.dev2`.

This release implements the production boundary defined in the three-way integration plan:

1. **SSM compiler plane** owns semantic intent collapse, SML/SIR validation, deterministic target generation, and generated-product evidence.
2. **Auto research observation plane** owns run records, strict traces, replay comparison, determinism census, behavioural contracts, immutable evaluation records, and content-addressed registry storage.
3. **Evolution-assurance plane** owns paired longitudinal comparison, four-state release verdicts, change-intent envelopes, labelled-slice analysis, and first-changed-stage attribution.

The observation and assay planes may qualify or block promotion. They do not mutate RequirementsIR, SML, SIR, target-pack code, or their own baselines.

## Implemented capability map

| Plan requirement | Implementation | State |
|---|---|---|
| Canonical GenerationRunRecord | `ssm.auto_research.schemas.GenerationRunRecord`; emitted by `compile-intent`, `research-run`, and `online-build` | Implemented |
| Measured-only evidence | `MetricObservation` rejects non-null values when `measured=false` | Implemented |
| Environment identity | Compiler/Python/platform/provider/model/scaffold/prompt/dependency-lock fingerprint | Implemented |
| Trace SDK | Strict append-only JSONL v0-style recorder with task header, spans, and single task output | Implemented |
| Online model-call tracing | Provider/model, prompt digest, response digest, usage, timing, errors, and retry branches | Implemented |
| Replay comparison | Ordered effectful-call signature and outcome comparison | Implemented |
| Determinism census | Witnessed deterministic, witnessed divergent, and unwitnessed classifications | Implemented |
| Content-addressed eval runs | `EvaluationRun` identities derived from canonical payloads | Implemented |
| Behavioural contracts | Metric rules with `PASS`, `FAIL`, or `UNCHECKED` verification | Implemented |
| Differential release assay | Matched records, exact paired sign test, effect direction and magnitude | Implemented |
| Four-state verdict | `NO_MATERIAL_CHANGE`, `INTENDED_EVOLUTION`, `REGRESSION`, `INCONCLUSIVE` | Implemented |
| ChangeIntentContract | Protected metrics and approved increase/decrease/absolute-change envelopes | Implemented |
| Stage attribution | First changed fingerprint across requirements, foundation, architecture, capability, canonical semantic context, SML, semantic conformance, SIR/tree, and quality stages | Implemented |
| Hidden labelled slices | Domain pack, backend, tenancy, workflow, update model, and rule-complexity slice assays | Implemented |
| Frozen SSM-Bench v1 | 30 content-addressed intent cases across the required capability/complexity strata | Implemented |
| Local registry | Immutable SHA-256 object store with optional detached HMAC-SHA256 integrity record | Implemented |
| Sequential anytime-valid production assay | Not included in this offline research baseline | Deferred |
| Unknown-slice discovery | Not included; current assays use declared slices | Deferred |
| Conformal guard/deopt/ratchet | Kept outside the initial study boundary | Deferred |
| WASM cognition binary / zero-import runtime | Explicitly not required by this research release | Deferred |

## Canonical run workflow

```text
intent / README
    -> RequirementsIR
    -> AppFoundationPlan
    -> ArchitecturePlan
    -> capability composition and negotiation
    -> CanonicalSemanticContext
    -> offline deterministic or online constrained SML synthesis
    -> SemanticConformanceVerifier
    -> SML
    -> SIR and deterministic target generation
    -> certification and generated evidence
    -> generation_trace.jsonl
    -> generation_run.json
    -> optional behavioural contract evaluation
    -> optional content-addressed registry
    -> baseline/candidate evolution assay
```

Every `GenerationRunRecord` links:

- source digest and task/benchmark identity;
- compiler and environment lock;
- stage fingerprints;
- measured or absent metrics;
- generated/evidence artifact hashes;
- trace and evaluation IDs;
- capability slices;
- warnings and errors.

## CLI

### Instrumented generation

```bash
python -m ssm.cli.main research-run \
  --file benchmarks/ssm_bench_v1/intents/ssmb-005-hr-leave-approval.md \
  --out build/research/baseline/SSMB-005/run-00 \
  --task-id ssm-bench-v1 \
  --benchmark-case-id SSMB-005 \
  --replicate-id 00 \
  --provider mock \
  --model mock \
  --scaffold-version scaffold-v1 \
  --prompt-version prompt-v1
```

The output includes `generation_run.json` and `generation_trace.jsonl` in addition to the normal compiler artifacts.

### Validate the frozen corpus

```bash
python -m ssm.cli.main research-bench-validate \
  benchmarks/ssm_bench_v1/manifest.json
```

### Determinism census

```bash
python -m ssm.cli.main research-trace-report \
  --trace build/research/run-1/generation_trace.jsonl \
  --trace build/research/run-2/generation_trace.jsonl \
  --out build/research/determinism_report.json
```

### Replay comparison

```bash
python -m ssm.cli.main research-replay-compare \
  build/research/run-1/generation_trace.jsonl \
  build/research/run-2/generation_trace.jsonl \
  --out build/research/replay_comparison.json
```

### Behavioural contract

```bash
python -m ssm.cli.main research-contract-verify \
  --contract examples/research/default_behavioural_contract.json \
  --run build/research/run-1/generation_run.json \
  --out build/research/run-1/eval_run.json \
  --registry build/research/registry
```

### Evolution assay

```bash
python -m ssm.cli.main research-assay \
  --baseline build/research/baseline \
  --candidate build/research/candidate \
  --metric compile_success \
  --metric semantic_variance_score \
  --metric build_duration_ms \
  --change-intent examples/research/change_intent_contract.json \
  --out build/research/evolution_assay.json
```

The command exits non-zero for `REGRESSION` or `INCONCLUSIVE`, preserving fail-closed release use.

## Statistical boundary

The current assay implements an exact two-sided paired sign test over matched benchmark case and replicate IDs. This is intentionally dependency-light and auditable. It is not presented as the final research method for all metric families.

For binary task outcomes, a future research iteration should add an explicit matched-pair McNemar implementation and pre-register the choice between exact and asymptotic forms. For continuous production streams, sequential anytime-valid tests remain future work.

`INCONCLUSIVE` is distinct from success. It is returned when matched evidence is below the configured minimum or when usable measured observations are absent.

## Governance rules

- Baseline directories and registry objects are immutable by content identity.
- A monitor cannot update its own baseline.
- Change intent must be approved before candidate evaluation to qualify as intended evolution.
- Missing required observations fail behavioural verification.
- Evidence hash mismatches are hard errors.
- A statistical result may open an engineering repair branch; it cannot patch compiler semantics automatically.
- Metrics are measured or null. No manifest may reconstruct an unobserved value from assumptions.

## Current limitations

- Registry signing is optional local HMAC integrity, not public-key release signing. Ed25519 or Sigstore remains a production hardening step.
- Replay comparison compares recorded effectful sequences; it does not yet substitute a recorded world into a live execution.
- The determinism census is file-backed rather than SQLite-backed.
- Hidden-slice analysis uses declared benchmark labels; automatic unknown-subpopulation discovery is deferred.
- The offline assay does not yet implement sequential production monitoring.
- Token and cost metrics remain null unless the provider supplies measured usage; they are not estimated.
