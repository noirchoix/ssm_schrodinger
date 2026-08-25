# SSM Evolution Assurance — Cross-Study Synthesis

## Research question

Can SSM distinguish actual compiler or synthesis regression from stochastic
variation in an unchanged online generator while preserving causal stage
attribution and independent semantic/runtime evidence?

## Experimental architecture

The research program separates two sources of change:

1. stochastic representational variation produced by online SML synthesis;
2. deterministic behavioral changes introduced by controlled compiler-source
   mutations.

SSM-Bench v2 remained frozen throughout, with 30 benchmark cases and benchmark
digest:

`5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7`

## Study 1A — deterministic no-change control

The unchanged deterministic compiler produced exact repeatability across the
30-case × 10-replicate control:

- status equality: 300/300
- metric-map equality: 300/300
- stage-fingerprint equality: 300/300
- verdict: NO_MATERIAL_CHANGE

This establishes the deterministic noise floor.

## Study 1B — unchanged online stochastic generator

With DeepSeek-based constrained SML synthesis:

- provider calls: 200
- final accepted: 189/200 (94.5%)
- runtime contract pass: 179/189 (94.71%)
- normalized offline/online outcome agreement: 299/300
- all provider cases exhibited repeated SML variation
- independent requirement, foundation, capability, and semantic-oracle
  measurements remained effectively unchanged.

The principal result is that structural SML/SIR/tree variance can occur without
corresponding semantic regression.

## Study 2 — controlled source regressions

### M-RQ-01 — Requirements extraction

Mutation:
remove the first explicit business rule.

Affected benchmark cases:
8/30.

First causal divergence:
`requirements`.

Independent requirement-obligation recall changed from:

`1.000000 -> 0.9537566`

and semantic-oracle score changed from:

`0.9812037 -> 0.9734965`.

Both effects occurred in exactly the eight affected benchmark cases.

Headline compilation remained stable, demonstrating that aggregate operational
metrics can fail to expose semantic loss.

### M-FN-01 — Foundation planning

Mutation:
remove the first applicable foundation relationship.

Affected cases:
16/30.

First causal divergence:
`foundation`.

RequirementsIR remained unchanged in all 30 cases.

The frozen benchmark oracle contained no relationship obligation, so its
semantic metrics did not expose this defect. Stage fingerprinting nevertheless
localized the real source regression.

In the formal online arm, affected provider cases produced SCV042 on 55/90
first attempts. The online model frequently reconstructed the omitted
relationship, but semantic conformance rejected that reconstruction because it
was absent from the corrupted canonical context.

This exposes a central architectural trade-off: deterministic canonical
authority controls hallucination, but can also suppress useful probabilistic
recovery when canonicalization itself is wrong.

### M-SCV-01 — Semantic-conformance boundary

Mutation:
suppress required-report diagnostic SCV090 while retaining the check invocation
and unrelated verifier behavior.

Report-positive cases:
7.

Pipeline-reachable report-positive cases:
4.

Baseline:
- valid SML accepted: 7/7
- missing-report SML rejected: 7/7
- SCV090 detected: 7/7

Mutant:
- valid SML accepted: 7/7
- missing-report SML accepted: 7/7
- SCV090 detected: 0/7
- unrelated SCV100 enforcement preserved: 7/7

Canonical context and candidate SML bytes were identical.

First causal divergence:
`semantic_conformance`.

This demonstrates the safety-boundary function of semantic conformance.

### M-TG-01 — Target generation

Mutation:
omit the first deterministic domain-router registration from generated
`app/main.py`.

Fixed recorded Study 1B accepted SML cases replayed:
19.

All 19 were affected.

Across baseline and mutant replay:

- recorded SML SHA-256: identical
- manifest SML hash: identical
- SIR hash: identical
- resolved-IR hash: identical
- generated route-module paths: identical
- router registration count: -1
- generated file count: unchanged
- generated-tree fingerprint: changed

First causal divergence:
`generated_tree`.

A provenance-locked runtime-sensitive test independently reproduced the
application-level consequence:

`POST /leave-requests`

expected:

`HTTP 201`

observed:

`HTTP 404 Not Found`

The natural negative-control population for this replay was empty; the
reported negative-control lock is therefore vacuous and is not treated as
substantive evidence.

## Cross-study result

The combined evidence distinguishes three materially different phenomena:

### Stochastic representational variance

Study 1B demonstrated large natural variation in SML, SIR, and generated-tree
representations while independent semantic measurements remained stable.

### Upstream deterministic semantic regression

M-RQ-01 and M-FN-01 introduced real source changes whose earliest observable
divergence appeared at their corresponding deterministic semantic stages.

### Boundary and downstream deterministic regression

M-SCV-01 showed that a weakened semantic-conformance boundary permits defective
candidate semantics to enter compilation.

M-TG-01 showed that identical accepted SML and identical SIR do not guarantee
an identical or correct application when deterministic target generation
changes.

## Principal architectural finding

Canonical semantics are both:

1. a hallucination-control boundary; and
2. a potential error-amplification boundary.

When canonical semantics are correct, semantic conformance prevents stochastic
candidate loss.

When canonical semantics are incorrect, a capable online model may reconstruct
missing information, yet semantic conformance can force the candidate back
toward the defective deterministic representation.

Accordingly, deterministic authority must itself remain independently
observable and regression-tested.

## Supported claim

Across controlled mutations placed at distinct upstream,
semantic-conformance-boundary, and downstream generation locations, SSM
distinguished deterministic regressions from characterized stochastic
generation variance and localized their earliest observable causal stage.

## Claim limitations

This checkpoint does not establish exhaustive all-stage localization.

M-AR-01 and M-CP-01 were not executed.

Study 2B alternate-provider, alternate-model, and scaffold-drift classes were
deferred.

The relationship dimension exposed by M-FN-01 is not represented by the frozen
SSM-Bench v2 semantic oracle.

M-TG-01 had no naturally occurring negative-control case in the 19-case fixed
replay corpus.

These limitations define the next research program rather than invalidating
the current causal findings.