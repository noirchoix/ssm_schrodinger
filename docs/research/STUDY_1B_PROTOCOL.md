# SSM Research Study 1B — Canonical-Context-Constrained Online Synthesis

## Purpose

Study 1B measures the stochastic component of SSM V2.6 dev.2 without changing the frozen SSM-Bench v2 corpus or the deterministic semantic front-end established in Study 1A.

The experimental boundary is:

```text
same input.md
    -> RequirementsIR
    -> AppFoundationPlan
    -> ArchitectureIR
    -> Capability Composition
    -> Negotiation
    -> CanonicalSemanticContext
       ============================ stochastic boundary
    -> DeepSeek candidate SML
    -> SemanticConformanceVerifier
    -> bounded repair when required
    -> SSMCompiler / SIR
    -> deterministic target generation
    -> independent runtime contract
```

Only `input.md` is supplied as source intent. `oracle.json`, `runtime_contract.json`, and `metadata.json` remain evaluator-only artifacts.

## Freeze conditions

Study 1B reuses the existing frozen SSM-Bench v2 corpus. The harness validates the declared corpus digest before any provider-backed run. Study 1A remains unchanged and is used as the deterministic reference arm.

The online harness additionally records and verifies the `CanonicalSemanticContext` fingerprint for every observation. A mismatch between the locally reconstructed canonical context and the online build context is an instrumentation failure, not an ordinary model outcome.

The dev.2 raw canonical-context fingerprint also carries source-provenance naming. Study 1A records the benchmark path while `OnlineBuildService` persists the same bytes as `input.md`. Study 1B therefore preserves each raw fingerprint for audit, but paired offline/online attribution uses a normalized semantic-context signature derived from the five deterministic upstream semantic stage fingerprints. A provenance-only filename difference cannot therefore be misclassified as semantic drift.

## Qualification

The first live phase is 30 cases x 1 replicate. Cases blocked by the deterministic semantic front-end are expected to invoke the provider zero times. All other cases may invoke DeepSeek and produce an accepted or rejected online outcome.

Qualification separates research outcomes from infrastructure integrity. The pre-run engineering readiness thresholds are:

- zero infrastructure/provider exceptions;
- zero canonical-context lock failures;
- zero provider invocations for upstream-blocked cases;
- at least one provider-invoked case;
- >= 0.70 acceptance rate among provider-invoked cases;
- >= 0.80 independent runtime-contract pass rate among executed runtime probes.

These thresholds gate the expensive 30 x 10 repeated run. They do not modify the benchmark, oracle, or observed results.

## Repeated online arm

After qualification is ready, run 30 cases x 10 replicates using replicate IDs `R00` through `R09`, matching Study 1A for paired analysis. The harness is resumable: valid content-addressed observations already present on disk are not repeated unless resume is disabled.

The repeated arm does not require byte-identical model output. It measures the natural stochastic noise floor of the unchanged online system.

## Measurements

Each online `GenerationRunRecord` includes deterministic upstream stage fingerprints and, where observed, candidate SML, semantic-conformance, SIR, generated-tree, quality-gate, and runtime-contract fingerprints. Metrics include provider invocation, model-call count, synthesis attempts, repair rounds, first/final conformance, generated-file count, runtime-contract success, independent oracle scores, model latency, and provider token usage. Cost remains explicitly unmeasured because the provider adapter does not currently report price.

## Analysis

The Study 1B analysis compares the repeated online arm to the Study 1A deterministic baseline and reports:

- exact upstream semantic-stage lock;
- candidate-SML surface diversity;
- SIR and generated-tree diversity;
- first-pass and final semantic-conformance rates;
- repair frequency;
- compile/generation acceptance;
- independent runtime-contract pass rate;
- token and model-latency observations;
- per-stage exact-match rates against the offline strategy;
- a paired strategy assay using common measured metrics;
- first-changed-stage attribution.

A central empirical question is whether candidate SML can vary while accepted semantics and generated behaviour remain stable under a fixed canonical semantic context.

## Commands

Qualification:

```bash
RUN_DEEPSEEK_LIVE=1 bash scripts/run_study1b_online_qualification.sh build/study1b_online_qualification
```

Review `build/study1b_online_qualification/qualification_summary.json`. Do not start the formal repeated arm unless `ready_for_repeated_run` is `true` or the protocol is explicitly amended before data collection.

Repeated arm and offline/online analysis:

```bash
RUN_DEEPSEEK_LIVE=1 bash scripts/run_study1b_online_repeated.sh \
  build/study1b_online_repeated \
  build/study1b_online_qualification/qualification_summary.json \
  build/study1_local_replication/baseline
```

The repeated script defaults to 10 replicates per case and resumes completed observations after interruption.
