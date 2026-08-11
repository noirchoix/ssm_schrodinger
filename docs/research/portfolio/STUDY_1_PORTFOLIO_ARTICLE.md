# Specification-Conditioned Evolution Assurance for AI-Assisted Software Generation

## Design and Controlled Evaluation of the SSM Platform

### Abstract

AI-assisted software generation combines probabilistic model behavior with software-engineering requirements for repeatability, semantic fidelity and controlled evolution. This technical research study evaluates an architecture in which a deterministic semantic front-end converts natural-language application requirements into typed intermediate representations and a `CanonicalSemanticContext` before any online model is allowed to synthesize executable SML. Candidate model outputs must pass a `SemanticConformanceVerifier` before compilation.

I evaluated the platform using a frozen 30-case benchmark with evaluator-separated semantic oracles and independent runtime contracts. The first experiment established a deterministic reference across 300 baseline and 300 no-change observations, then tested controlled requirements-, SML- and generated-tree regressions together with an approved intended-evolution condition. The unchanged system produced `NO_MATERIAL_CHANGE`; the three known degradation controls produced `REGRESSION` and were attributed to their injected first-change stages; the approved non-semantic change produced `INTENDED_EVOLUTION`.

A second experiment held the same semantic front-end and benchmark constant while replacing deterministic SML rendering with repeated DeepSeek synthesis. Across 300 online observations, the deterministic upstream stages matched the offline reference exactly. The provider was invoked for 200 observations; 85.5% of first candidates passed semantic conformance and 94.5% passed after bounded repair. Of 189 accepted generated applications, 179 passed independent runtime contracts. Every provider-invoked case exhibited repeated SML variation, while the independent requirement, foundation, capability and composite semantic-oracle metrics remained exactly unchanged between offline and online arms. First-changed-stage attribution localised the strategy difference to SML synthesis.

The results support a distinction between artifact variability and measured semantic stability. They also expose limitations: canonicalization defects are inherited by constrained synthesis, independent runtime contracts provide bounded rather than exhaustive behavioral evidence, and a release-oriented statistical classifier can mislabel expected cross-strategy structural differences as regression. The study motivates further work on source-level compiler mutants, provider/model drift, larger independently annotated benchmarks and strategy-specific evolution contracts.

## 1. Research question

The central question is not whether a language model can produce source code. It is:

> **Can an AI-assisted software-generation system preserve an explicit semantic authority while allowing probabilistic synthesis, and can changes be detected, classified and attributed with reproducible evidence?**

This question matters because direct prompt-to-code systems confound at least three phenomena: interpretation of the user's requirement, stochastic model behavior, and deterministic compiler/runtime behavior. SSM separates these concerns.

## 2. Architecture

The evaluated pipeline is:

```text
raw intent
  ↓
RequirementsIR
  ↓
AppFoundationPlan
  ↓
ArchitectureIR
  ↓
Capability composition and negotiation
  ↓
CanonicalSemanticContext
  ↓
  ├─ deterministic SML rendering
  └─ constrained online SML synthesis
          ↓
     SemanticConformanceVerifier
  ↓
accepted SML
  ↓
SSMCompiler → SIR
  ↓
deterministic target generation
  ↓
generated application
  ↓
quality, evidence and research gates
```

The design changes the role of the online model. It is not the sole semantic interpreter of the user's request. It receives an upstream canonical interpretation and may propose a representation of that interpretation. A separate verifier rejects missing required semantics, invented protected semantics, architecture/capability drift and other violations before compilation.

**Figure 1** in the accompanying figure pack summarizes the controlled first-change attribution used to validate the assurance machinery in Study 1A.

![Study 1A controlled attribution](figures/figure_1_study1a_first_changed_stage.png)

## 3. Benchmark and evaluator separation

SSM-Bench v2 contains 30 end-to-end case packs. Only `input.md` enters the generation pipeline. `oracle.json`, `runtime_contract.json` and research metadata remain evaluator-only. Inputs include structured READMEs, semi-structured PRDs, narrative requests, stakeholder notes, ambiguous requirements, contradictory requirements and unsupported feature requests.

The corpus was frozen even though the current compiler did not pass every intended-generatable case. This was deliberate: failures discovered during qualification become part of the baseline defect profile rather than being edited away.

## 4. Study 1A: deterministic evolution assurance

Study 1A generated 300 baseline and 300 no-change control observations. Every paired status, measured metric map and stage fingerprint was identical. The assay returned `NO_MATERIAL_CHANGE` with no first-changed stage.

Three known degradation controls were then introduced at different semantic boundaries. Requirements degradation was detected as `REGRESSION` and attributed to `requirements`; an SML rule degradation was detected and attributed to `sml`; and a generated-tree degradation was detected and attributed to `generated_tree`. An approved evidence-file addition produced a material generated-file-count change but preserved protected semantic metrics and remained inside an explicit change envelope, so it was classified as `INTENDED_EVOLUTION`.

This experiment validated the mechanics of pairing, stage fingerprinting, change-intent envelopes, slice-aware analysis and first-change attribution under controlled ground truth.

## 5. Study 1B: repeated probabilistic synthesis

Study 1B used the same 30 frozen inputs and the same upstream semantic interpretation. The provider condition was DeepSeek `deepseek-chat` at temperature 0, with JSON mode, bounded retries and a locked settings digest. Ten replicates were executed per case, producing 300 online observations.

The provider was invoked for 200 observations. The remaining 100 were stopped before the stochastic boundary because the deterministic semantic front-end rejected or blocked those cases. No blocked case was sent to the provider.

The upstream semantic lock held across all 300 matched pairs: RequirementsIR, foundation, architecture, capabilities, negotiation and the normalized canonical semantic context matched the deterministic Study 1A reference exactly.

![Exact offline–online stage match rates](figures/figure_2_study1b_stage_match_rates.png)

The stage-match figure makes the experimental boundary explicit: exact identity is preserved through canonical semantics and diverges at SML synthesis.

Among provider-invoked observations, 171/200 first candidates passed semantic conformance. After bounded repair, 189/200 passed and were accepted. Repair was especially visible in cases where the model omitted required reports or invented an executable business rule not authorized by the canonical context. These proposals were rejected before compilation and usually repaired on a later attempt.

The remaining final failures were concentrated. Ten came from a pre-existing no-auth representation mismatch already present in the deterministic baseline. One additional replicate exhausted repair after recurring semantic-conformance errors. This concentration is important: the observed 94.5% final acceptance rate is not the result of diffuse random failure across the benchmark.

![Online synthesis, repair and runtime outcomes](figures/figure_3_study1b_online_outcomes.png)

![Case-level repair and runtime-failure concentration](figures/figure_4_study1b_case_concentration.png)

## 6. Representation variance versus measured semantic stability

The online arm was not deterministic at the artifact level, even at temperature 0. Every provider-invoked benchmark case produced multiple candidate-SML fingerprints across ten replicates. Among cases that generated applications, SIR and generated-tree identities also varied across repeated runs.

Yet the independent semantic-oracle metrics were unchanged between Study 1A and Study 1B across all 300 matched observations. Requirement recall remained 1.0, foundation recall 0.8872, capability recall 1.0, and the composite semantic score 0.9812 in both arms. Every paired value for these metrics was equal.

Of 189 accepted online applications, 179 passed the independent runtime contracts. The ten runtime failures all came from one benchmark case whose deterministic canonical front-end already misinterpreted the domain in Study 1A. This shows both the value and the limitation of the architecture: conformance can prevent the model from redefining canonical semantics, but it cannot correct an upstream canonical interpretation that is itself wrong.

First-changed-stage attribution localized online/offline divergence to SML synthesis. The deterministic semantic stages did not drift.

The empirical pattern is therefore:

```text
deterministic upstream semantics    stable
            ↓
probabilistic SML representation    variable
            ↓
semantic conformance                corrective
            ↓
measured semantic outcomes          stable
```

This supports the proposition that surface-form variability need not imply semantic variability when probabilistic synthesis is conditioned on a deterministic semantic authority and constrained before compilation.

## 7. An unexpected methodological finding

A generic release-comparison assay labelled the overall Study 1A-versus-Study 1B comparison `REGRESSION`. The label was triggered by a statistically significant +0.08 change in mean generated-file count, even though all independent semantic-oracle metrics were identical and compile success differed by only one observation.

The classifier behaved consistently with its release-assurance design: any statistically material change outside an approved change envelope is adverse. But an offline-versus-online strategy comparison is not the same problem as a software-release comparison. A small structural difference in generated artifacts is not automatically a semantic regression.

This result exposes a methodological requirement for future work: **strategy comparison needs its own contract and verdict semantics.** The present Study 1B result is better described as *structural divergence with preserved measured semantic fidelity* than as a semantic regression.

A second analysis artifact reported only 36.7% exact status-string matches between the two arms. This is similarly misleading because Study 1A labels successfully generated observations `CONDITIONAL`, whereas Study 1B labels them `ACCEPTED`. A normalized outcome taxonomy is needed for cross-arm analysis.

## 8. Consolidated quantitative tables

### Study 1A controlled evolution

| condition           | verdict            | first_changed_stage   | primary_metric            |   baseline_mean |   candidate_mean |    effect |     p_value |
|:--------------------|:-------------------|:----------------------|:--------------------------|----------------:|-----------------:|----------:|------------:|
| no_change           | NO_MATERIAL_CHANGE | none                  | compile_success           |        0.633333 |         0.633333 |  0        | 1           |
| requirements_drop   | REGRESSION         | requirements          | oracle_requirement_recall |        1        |         0.766667 | -0.233333 | 1.02951e-84 |
| sml_rule_drop       | REGRESSION         | sml                   | compile_success           |        0.633333 |         0.3      | -0.333333 | 1.57772e-30 |
| generated_tree_drop | REGRESSION         | generated_tree        | compile_success           |        0.633333 |         0        | -0.633333 | 1.27447e-57 |
| intended_evolution  | INTENDED_EVOLUTION | generated_tree        | generated_file_count      |       55.0333   |        55.6667   |  0.633333 | 1.27447e-57 |

### Study 1B aggregate outcomes

| measure                                 |      value | interpretation                                   |
|:----------------------------------------|-----------:|:-------------------------------------------------|
| Total online observations               | 300        | 30 cases × 10 replicates                         |
| Provider-invoked observations           | 200        | Stochastic boundary reached                      |
| First-candidate conformance             |   0.855    | 171/200 provider-invoked                         |
| Final conformance / acceptance          |   0.945    | 189/200 provider-invoked                         |
| Runtime-contract pass                   |   0.94709  | 179/189 accepted applications                    |
| Normalized offline↔online outcome match |   0.996667 | ACCEPTED and CONDITIONAL normalized to GENERATED |
| Upstream stage lock                     |   1        | Requirements through canonical semantic context  |
| Cases with SML surface variance         |  20        | 20/20 provider-invoked cases                     |
| Cases with SIR variance                 |  19        | 19 accepted-generating cases                     |
| Cases with generated-tree variance      |  19        | 19 accepted-generating cases                     |

### Offline–online semantic fidelity

| metric                    |   offline_mean |   online_mean |   effect |
|:--------------------------|---------------:|--------------:|---------:|
| oracle_requirement_recall |       1        |      1        |        0 |
| oracle_foundation_recall  |       0.887222 |      0.887222 |        0 |
| oracle_capability_recall  |       1        |      1        |        0 |
| oracle_semantic_score     |       0.981204 |      0.981204 |        0 |

## 9. Limitations

The independent semantic and runtime oracles are bounded. Equality under these tests is evidence of measured equivalence, not proof of complete behavioral equivalence.

The benchmark contains 30 cases and one provider/model condition. The semantic oracles were not independently double-annotated. Larger and held-out corpora, multi-annotator agreement, long-form requirements and adversarial textual variation are required before generalizing beyond the evaluated scope.

The online experiment also reveals that deterministic canonicalization quality places an upper bound on constrained synthesis quality. A model that is prevented from contradicting the canonical context will also faithfully inherit an incorrect canonical context.

Finally, the controlled regression conditions in Study 1A were evidence-record interventions with known first-stage ground truth rather than separately compiled source-mutant releases. Source-level mutation is therefore a direct next experiment.

## 10. Future research

The next study should introduce controlled source-level mutants at the requirements extractor, foundation planner, capability resolver, conformance layer and target generator. The objective is to determine whether the assurance system can detect naturally propagated regressions against the stochastic noise floor established in Study 1B.

A second direction is provider/model drift. Because CanonicalSemanticContext is held fixed before the stochastic boundary, future experiments can compare DeepSeek with other models, prompt versions or provider revisions without confounding changes in requirements interpretation.

A third direction is strategy-aware assurance. Cross-strategy experiments need typed equivalence envelopes that distinguish expected artifact diversity from adverse semantic or runtime effects. This includes normalised outcome classes and metrics that compare executable behavior rather than raw file-count differences alone.

## 11. Portfolio significance

SSM now demonstrates a complete research workflow around AI-assisted software generation: compiler and intermediate-representation design, deterministic semantic interpretation, constrained LLM synthesis, semantic conformance, independent evaluation, reproducible benchmark design, repeated experiments, statistical comparison and stage-level attribution.

The strongest research contribution is the architecture and methodology for asking **where stochastic variation enters, whether it crosses a semantic boundary, and whether downstream behavior changes**. Study 1 provides a controlled reference and an empirical online noise floor; Study 2 can test whether that assurance remains reliable under real compiler and provider evolution.
