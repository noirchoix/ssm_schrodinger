# Study 2 — M-RQ-01 Evidence Record

## Mutant
- ID: M-RQ-01
- Mutation: drop first explicit business-rule requirement
- Qualified source commit: c4b93b99d5821cdf4909d33f31e54cbe5d53d428
- Provenance-locked harness commit: 9182fb268909401e06a3d84c4d11589a52407905

## Frozen benchmark
- SSM-Bench v2
- Cases: 30
- Digest: 5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7

## Deterministic qualification
- Affected cases: 8
- Negative controls: 22
- First causal stage: requirements
- Verdict: REGRESSION
- Requirement recall: 1.000000 -> 0.9537566137566138
- Semantic score: 0.9812037037037037 -> 0.9734964726631393
- p = 0.0078125 for both semantic endpoints

## Online 30x10 experiment
- Records: 300
- Provider-invoked: 200
- Accepted: 189
- Rejected: 111
- Infrastructure errors after recovery: 0
- Runtime pass: 178/189
- Settings SHA-256: f6a6ef82e4cacde1c966224a61a8657adff7b84923c536ef209e96bab5f2f8a7

## Primary case-level comparison against Study 1B noise floor
- Compile success effect: 0.0, p=1.0
- Generated-file-count effect: -0.08333333333333333, p=1.0
- First-pass-conformance effect: +0.04, p=1.0
- Final-conformance effect: 0.0, p=1.0
- Repair-round effect: -0.03666666666666667, p=1.0
- Runtime-contract-pass effect: -0.005263157894736841, p=1.0
- Requirement-recall effect: -0.04624338624338624, p=0.0078125
- Foundation-recall effect: 0.0, p=1.0
- Capability-recall effect: 0.0, p=1.0
- Semantic-score effect: -0.007707231040564366, p=0.0078125

## Causal locks
- Expected first stage: requirements
- Expected affected-case lock: PASS
- Negative-control upstream lock: PASS

## External evidence assets
- study2_mrq01_online_repeated.zip
  SHA-256: dd2492877cf8cfe9e339eaa80c36bbaf94a5e1062c0049fc744bd57295889dee
- study2_mrq01_online_analysis.zip
  SHA-256: 1755b41299572a46e0c3ec075a76b34fdd46d760842b0b3b22c4b33ddb261791
