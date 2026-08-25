# Study 2 — M-FN-01 Evidence Record

## Mutant

- ID: M-FN-01
- Intervention: remove the first relationship from every non-empty AppFoundationPlan.relationships list
- Mutant commit: 1e06ce0092c97bfd8c787b86546ba76f1ce189d9
- Harness commit: d78f117
- Expected first causal stage: foundation

## Benchmark

- SSM-Bench v2
- Cases: 30
- Digest: 5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7

## Deterministic qualification

- Matched pairs: 30
- Requirements-stage changes: 0
- Foundation-stage affected cases: 16
- Negative controls: 14
- Observed first changed stage: foundation
- Generic assay verdict: NO_MATERIAL_CHANGE
- Compile success: unchanged
- Generated file count: unchanged
- Requirement oracle: unchanged
- Existing foundation oracle: unchanged
- Capability oracle: unchanged
- Composite semantic oracle: unchanged

This establishes a measurement-coverage limitation in SSM-Bench v2:
foundation relationships are represented in stage fingerprints but are not
scored by the frozen semantic oracle.

## Online 30x10 experiment

- Records: 300
- Provider-invoked: 200
- Accepted: 190
- Rejected: 110
- Infrastructure errors: 0
- Runtime passes: 180/190
- Runtime pass rate: 0.9473684210526315
- Provenance-stamped records: 300
- Settings SHA-256:
  f6a6ef82e4cacde1c966224a61a8657adff7b84923c536ef209e96bab5f2f8a7

## Primary case-level comparison against Study 1B

- Compile-success effect: +0.0033333333333333327, p=1.0
- Generated-file-count effect: +0.23333333333333287, p=1.0
- First-pass-conformance effect: -0.27, nominal p=0.0390625
- Final-conformance effect: +0.005, p=1.0
- Repair-round effect: +0.16333333333333333, p=0.1796875
- Runtime-contract-pass effect: 0.0, p=1.0
- Requirement-oracle effect: 0.0, p=1.0
- Foundation-oracle effect: 0.0, p=1.0
- Capability-oracle effect: 0.0, p=1.0
- Composite-semantic-oracle effect: 0.0, p=1.0

The first-pass-conformance result is nominal and should not be described as
family-wise significant without the planned multiplicity correction.

## SCV042 mechanistic analysis

Provider-invoked affected observations:

Study 1B:
- n = 90
- first-pass failures = 0
- SCV042 = 0

M-FN-01:
- n = 90
- first-pass failures = 55
- SCV042 = 55
- SCV042 rate = 0.6111111111111112

Provider-invoked negative-control observations:

Study 1B:
- n = 110
- first-pass failures = 29
- SCV042 = 0

M-FN-01:
- n = 110
- first-pass failures = 28
- SCV042 = 0

Affected case-level SCV042 deltas:
- SSMB2-004: +0.2
- SSMB2-005: +1.0
- SSMB2-006: +0.9
- SSMB2-008: +1.0
- SSMB2-012: 0.0
- SSMB2-016: +0.4
- SSMB2-018: 0.0
- SSMB2-022: +1.0
- SSMB2-026: +1.0

Mean affected delta: +0.6111111111111112
Mean negative-control delta: 0.0

Seven affected cases had positive deltas, two were unchanged, and none
decreased. The two-sided exact sign-test p-value over the seven non-zero
case-level deltas is 0.015625.

The SCV042 analysis was specified after the 30x1 qualification exposed the
candidate mechanism and before the formal 30x10 run. It is therefore treated
as a prospectively specified secondary mechanistic analysis rather than an
original preregistered primary endpoint.

## Interpretation

M-FN-01 demonstrates that causal stage attribution can detect a real
foundation-stage source regression even when the frozen outcome oracle is
blind to the mutated semantic feature.

The online model frequently reconstructs the omitted relationship from the
remaining domain structure. The SemanticConformanceVerifier then rejects the
reconstructed relationship because it is absent from the mutated canonical
semantic context. Repair restores conformance by removing the relationship.

Thus canonical semantic authority successfully suppresses stochastic
non-conformance, but can also suppress useful neural recovery when an upstream
deterministic semantic stage is itself defective.
