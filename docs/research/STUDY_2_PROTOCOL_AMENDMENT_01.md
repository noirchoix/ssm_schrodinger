# Study 2 Protocol Amendment 01

## Status

Post-hoc documentation of a scope decision made before execution of M-SCV-01
and M-TG-01.

The amendment file itself was added after those experiments. This timing is
stated explicitly to avoid representing the document as a contemporaneously
committed preregistration artifact.

## Original protocol

The original Study 2 protocol proposed the following source mutants:

- M-RQ-01 — Requirements extraction
- M-FN-01 — Foundation planning
- M-AR-01 — Architecture resolution
- M-CP-01 — Capability composition
- M-SCV-01 — Semantic conformance verification
- M-TG-01 — Target generation

It also proposed a later Study 2B drift-class program.

## Amendment

For the August 2026 research checkpoint, experimental scope was reduced to:

- M-RQ-01
- M-FN-01
- M-SCV-01
- M-TG-01

The following were deferred:

- M-AR-01
- M-CP-01
- Study 2B alternate model/provider/scaffold drift classes
- additional mutants
- benchmark/oracle expansion

## Rationale

M-RQ-01 and M-FN-01 already supplied adjacent upstream source-regression
localization evidence.

M-AR-01 and M-CP-01 would have added further stage coverage but comparatively
less new causal information within the available execution window.

M-SCV-01 was retained because it tests the stochastic/deterministic safety
boundary directly.

M-TG-01 was retained because it tests deterministic downstream generation
using fixed recorded SML, removing online-model variation as a confound.

No M-AR-01 or M-CP-01 experimental results existed when the scope decision
was made.

The research question, frozen SSM-Bench v2 corpus, benchmark digest, Study 1
baseline, and statistical interpretation were not changed by this scope
decision.

## Claim restriction

The amended study does not claim exhaustive all-stage mutation coverage.

The supported claim is:

Across controlled mutations placed at distinct upstream, semantic-conformance
boundary, and downstream generation locations, SSM distinguished deterministic
regressions from characterized stochastic generation variance and localized
their earliest observable causal stage.

## Future work

M-AR-01, M-CP-01, Study 2B drift classes, broader provider/model coverage,
and enhanced benchmark/oracle coverage remain future research extensions.
