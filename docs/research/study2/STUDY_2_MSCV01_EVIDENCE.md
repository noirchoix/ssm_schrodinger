# Study 2 — M-SCV-01 Evidence Record

## Mutant

- ID: M-SCV-01
- Intervention class: REGRESSION
- Target: SemanticConformanceVerifier
- Diagnostic family: SCV090
- Mutation: suppress required-report absence detection while preserving
  the SCV090 check invocation and unrelated conformance checks.
- Qualified source commit:
  a3bc3de2a0f9e89ff3cbd979fbf5d1a0279af85d
- Expected first causal stage: semantic_conformance

## Benchmark

- SSM-Bench v2
- Cases: 30
- Benchmark digest:
  5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7

## Provenance

- Provenance valid: true
- Branch: study2/m-scv-01
- Git clean: true
- Mutant module: ssm.product.semantic_context
- Mutant module SHA-256:
  669dd1f1b58d4260413c97cee2d134f8c84c36dc6892f0b436e46705800651ad
- Provenance SHA-256:
  6096cd68ff3b5dccb765412caeccd2dce26a944ee08db590c65acc51b8b120e3

## Frozen challenge population

Report-positive cases: 7

- SSMB2-001
- SSMB2-002
- SSMB2-010
- SSMB2-014
- SSMB2-021
- SSMB2-027
- SSMB2-028

Pipeline-reachable report-positive cases: 4

- SSMB2-002
- SSMB2-010
- SSMB2-014
- SSMB2-021

The remaining three report-positive cases are retained as verifier-unit
challenge cases but are normally blocked upstream.

## Baseline challenge

- Valid SML accepted: 7/7
- Missing-report SML accepted: 0/7
- Missing-report SCV090 detected: 7/7
- Missing ErrorHandling policy rejected: 7/7
- Missing-policy SCV100 detected: 7/7

## M-SCV-01 challenge

- Valid SML accepted: 7/7
- Missing-report SML accepted: 7/7
- Missing-report SCV090 detected: 0/7
- Missing ErrorHandling policy rejected: 7/7
- Missing-policy SCV100 detected: 7/7

## Causal comparison

- causal_input_lock: true
- target_behavior_changed: true
- target_behavior_changed_all_report_positive: true
- valid_control_preserved: true
- unrelated_control_preserved: true
- semantic_conformance_changed: true
- first_causal_stage: semantic_conformance
- qualified: true

## Interpretation

With canonical context and defective candidate SML held identical, the
baseline verifier rejects omission of a required report through SCV090,
whereas M-SCV-01 allows the identical defective candidate to pass.

The effect therefore originates at the semantic-conformance boundary rather
than requirements extraction, foundation planning, architecture resolution,
capability resolution, canonical-context construction, or stochastic SML
generation.

M-SCV-01 demonstrates the complementary failure mode to M-FN-01:
when canonical semantics are correct but verifier enforcement is weakened,
semantic loss can cross the stochastic/deterministic safety boundary.
