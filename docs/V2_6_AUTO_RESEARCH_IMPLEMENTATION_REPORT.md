# SSM Schrödinger Auto Research — V2.6.0-dev Implementation Report

## Upgrade basis

This repository upgrade implements the bounded offline integration defined by the **SSM Schrödinger + Auto + Evolution Assurance** plan. The compiler, observation, and statistical judgement planes remain separate.

The uploaded GitHub archive did not contain `src/ssm/backends/python_fastapi/target.py` although the package imported it. The target module and its existing compiler regression suite were restored byte-for-byte from the previously certified V2.5.0-rc.1 source before the V2.6 work was applied.

## Implemented product boundary

### Lane 1 — Canonical SSM run evidence

- Canonical content-addressed `GenerationRunRecord`.
- Compiler/environment identity and stage fingerprints.
- Measured-or-absent metrics.
- Automatic `generation_run.json` and `generation_trace.jsonl` emission for intent compilation and online-build paths.
- Existing manifests, contracts, capability reports, assumptions, unsupported features, provenance, repair trace, and evidence bundle remain compiler-owned.

### Lane 2 — Auto-inspired research instrumentation

- Strict append-only JSONL trace recorder and validator.
- Replay comparison over ordered effectful spans.
- Witnessed determinism census.
- Three-valued behavioural contract verification.
- Content-addressed evaluation runs.
- Immutable local SHA-256 registry with optional HMAC integrity records.
- Frozen content-addressed SSM-Bench v1 corpus with 30 stratified intents.

### Lane 3 — Offline evolution assurance

- Matched baseline/candidate pairing by benchmark case and replicate.
- Exact two-sided paired sign test.
- Four-state release verdict: `NO_MATERIAL_CHANGE`, `INTENDED_EVOLUTION`, `REGRESSION`, or `INCONCLUSIVE`.
- Approved change-intent envelopes and protected metrics.
- Labelled capability-slice analysis.
- First-changed-stage attribution.

## Validation

- Runtime package identity: `2.6.0.dev0`.
- Framework tests: **67 passed**.
- Python bytecode compilation: passed for `src` and `tests`.
- Editable package installation: passed with local build isolation disabled because the execution environment package mirror did not expose build requirements.
- SSM-Bench v1: **30 valid cases**.
- Benchmark identity: `sha256:840a6ad178ed7c4c2d157e0ccfc0d1f74fb848201e73375f015478b57da375fe`.
- Corpus digest: `650d129b6602fd024ff94e8d292468df905da303698caccc1d9a43e8e14706bf`.
- Generated-app evidence validation: **84 files hashed, 0 errors**.
- Two-run determinism census: **18/18 witnessed observations deterministic**.
- Replay comparison: **9 matched effectful spans, 0 mismatches**.
- Behavioural contract result: **PASS**.
- Registry add/verify: passed.
- Offline assay control result: **NO_MATERIAL_CHANGE**.
- Dedicated gate footer: `ALL SSM V2.6 AUTO RESEARCH GATES PASSED`.

## Determinism defect found and fixed

The first cross-process census identified nondeterministic generated RBAC source caused by direct Python `set` representation. Element order varied with `PYTHONHASHSEED`. Generation now emits sorted set literals, with an explicit hash-seed independence regression test.

## Deferred claims

This release does not claim:

- sequential anytime-valid production monitoring;
- automatic unknown-slice discovery;
- conformal guard/deoptimisation/ratchet integration;
- a WASM cognition binary or zero-import runtime;
- public-key release signing;
- full world-substitution replay;
- a final statistically preregistered research method for every metric family.

Ruff and mypy executables were not available in the packaging container. The repository CI remains configured to run both tools, plus Bandit and dependency audit, in a normal development environment.
