# SSM Research Study 1 — Results Report

## Executive result

Study 1 successfully executed the frozen offline research protocol over SSM-Bench v2. The benchmark contains 30 evaluator-separated cases and all 30 completed qualification without evaluator/harness failure. The formal repeated dataset contains 300 baseline observations and 300 no-change control observations, with controlled paired intervention arms derived from the same baseline records.

The principal assurance result is clean: the unchanged control produced `NO_MATERIAL_CHANGE`; all three preregistered regression controls produced `REGRESSION`; the approved non-semantic change produced `INTENDED_EVOLUTION`; and first-changed-stage attribution identified `requirements`, `sml`, and `generated_tree` exactly where the corresponding controls were injected.

The same study also identified important limitations in the current natural-language semantic front-end. These are retained as findings rather than removed from the benchmark.

## 1. Benchmark qualification

SSM-Bench v2 validated structurally with 30 cases and coverage of every RequirementsIR category. Its frozen corpus digest is:

`5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7`

Qualification results:

| Measure | Result |
|---|---:|
| Benchmark cases | 30 |
| Harness/instrumentation failures | **0** |
| Harness qualification | **PASS** |
| Expected outcome matches | **23 / 30 (76.7%)** |
| Intended generatable cases that generated | **19 / 26 (73.1%)** |
| Expected fail-closed cases correctly rejected | **4 / 4 (100%)** |
| Independent runtime probes passed | **18 / 19 generated applications (94.7%)** |
| Requirement-obligation recall | **1.000** |
| Foundation-obligation recall | **0.887** |
| Capability-obligation recall | **1.000** |
| Planned ambiguity detection | **1.000** |
| Planned contradiction detection | **1.000** |
| Planned unsupported-feature detection | **1.000** |
| Mean composite semantic-oracle score | **0.9812** |

The composite score should not be read as 98.1% end-to-end application correctness. It is the mean of six bounded oracle dimensions, several of which are binary and intentionally narrow. The more diagnostic measure is foundation-obligation recall (0.887) together with the seven unexpected fail-closed outcomes.

### 1.1 Current semantic-front-end limitations exposed by qualification

The benchmark exposed four classes of weakness:

1. **Substring-trigger collisions in deterministic domain inference.** Short substring checks can falsely activate the HR path. For example, ordinary words containing the characters `hr` can influence domain/entity selection. This caused some inventory/Todo inputs to collapse toward `Employee`/`LeaveRequest` semantics.
2. **Domain-precedence collisions.** Expense requests that mention employees can be classified into the HR entity branch before the expense branch, producing a rule/entity integrity conflict and fail-closed rejection.
3. **Public-auth representation mismatch.** The public Todo case reached CanonicalSemanticContext correctly but deterministic SML/conformance disagreed over the representation of no authentication (`None` versus null/omitted representation), causing a semantic-conformance rejection.
4. **Explicit custom rule preservation is incomplete.** RequirementsIR captured custom temporal, multi-field, and contextual rule declarations, but the deterministic foundation planner currently promotes only a bounded set of domain rules. Cases such as assignment-team matching, enrollment date order, maximum stock, leave date validation, and approval-limit context therefore score below full foundation fidelity even when the generated application remains structurally valid.

A fifth issue appeared in a negated tenancy statement: wording such as “no tenant isolation is required” can still activate a positive tenant keyword and collide with an explicit single-tenant constraint. This is a useful example of why negation-sensitive requirement parsing belongs in future work.

These failures are not removed from SSM-Bench v2. They form the baseline defect profile against which future compiler evolution can be measured.

## 2. Formal repeated baseline and no-change control

Each arm contains 30 cases × 10 replicates = 300 observations.

| Arm | Records | Conditional | Rejected | Mean oracle semantic score |
|---|---:|---:|---:|---:|
| Baseline | 300 | 190 | 110 | 0.9812037 |
| No-change control | 300 | 190 | 110 | 0.9812037 |

The 110 rejected observations consist of the same eleven cases repeated ten times: four intentional fail-closed benchmark cases plus seven current baseline limitations discovered during qualification.

For all 300 paired baseline/control observations:

- status was identical: **300 / 300**;
- measured metric maps were identical: **300 / 300**;
- stage-fingerprint maps were identical: **300 / 300**.

The assay therefore returned:

`NO_MATERIAL_CHANGE`

with `first_changed_stage = null`.

All four primary paired metrics had effect 0 and exact-test p-value 1.0.

## 3. Controlled regression results

### 3.1 Requirements-stage degradation

The `requirements_drop` control altered the requirements boundary for JWT-labelled cases and reduced independent requirement-recall evidence.

Result: **REGRESSION**
First changed stage: **requirements**

| Metric | Baseline mean | Candidate mean | Mean paired effect | Exact p |
|---|---:|---:|---:|---:|
| Oracle requirement recall | 1.0000 | 0.7667 | -0.2333 | 1.03×10^-84 |
| Oracle semantic score | 0.9812 | 0.8879 | -0.0933 | 1.03×10^-84 |

### 3.2 SML-stage rule degradation

The `sml_rule_drop` control targets cases labelled with executable rule complexity.

Result: **REGRESSION**
First changed stage: **sml**

| Metric | Baseline mean | Candidate mean | Mean paired effect | Exact p |
|---|---:|---:|---:|---:|
| Compile success | 0.6333 | 0.3000 | -0.3333 | 1.58×10^-30 |
| Oracle semantic score | 0.9812 | 0.8912 | -0.0900 | 1.31×10^-54 |

### 3.3 Generated-tree degradation

The `generated_tree_drop` control changes generated-tree/quality identities for cases that generated output and records the affected candidate as failed.

Result: **REGRESSION**
First changed stage: **generated_tree**

| Metric | Baseline mean | Candidate mean | Mean paired effect | Exact p |
|---|---:|---:|---:|---:|
| Compile success | 0.6333 | 0.0000 | -0.6333 | 1.27×10^-57 |

## 4. Declared intended evolution

The intended-evolution control adds one non-semantic evidence artifact to cases with generated output. The approved ChangeIntentContract protects compile success, requirement recall, and semantic score while allowing generated-file count to increase by at most one.

Result: **INTENDED_EVOLUTION**
First changed stage: **generated_tree**

| Metric | Baseline mean | Candidate mean | Mean paired effect | Exact p |
|---|---:|---:|---:|---:|
| Generated file count | 55.0333 | 55.6667 | +0.6333 | 1.27×10^-57 |
| Compile success | 0.6333 | 0.6333 | 0 | 1.0 |
| Oracle requirement recall | 1.0000 | 1.0000 | 0 | 1.0 |
| Oracle semantic score | 0.9812 | 0.9812 | 0 | 1.0 |

The significant file-count increase does not become a regression because it falls inside the approved envelope and all protected metrics remain unchanged.

## 5. Slice analysis

Slice analysis behaved conservatively. Slices with fewer than the configured 30 matched observations report `INCONCLUSIVE` rather than being silently treated as stable. In the unchanged control, no sufficiently powered slice reported a regression. The controlled perturbations produced regression verdicts across the relevant sufficiently populated domain, persistence, tenancy, workflow, rule-complexity, and source-style slices.

This supports the design principle that aggregate stability should not be allowed to conceal a regression concentrated inside a labelled capability slice.

## 6. Interpretation

Study 1 provides two different kinds of evidence.

First, it validates the **evolution-assurance apparatus** under controlled conditions: pairing, immutable stage identities, exact paired comparison, approved change envelopes, slice-aware verdicts, and first-changed-stage attribution all behaved as specified. The no-change arm did not produce a false regression, while known intervention controls were detected and localised.

Second, the independent case oracles exposed real weaknesses in the current deterministic natural-language front-end. This is scientifically useful. The benchmark is not acting as a demonstration set constructed only from examples the implementation already handles; it creates measurable pressure on requirement interpretation, negation, domain selection, rule promotion, and representation equivalence.

## 7. Threats to validity

The most important limitation is that the controlled regression campaign uses deterministic **evidence-record intervention controls** after complete baseline execution. This gives known ground truth for assay classification and attribution, but it is not identical to evaluating separately compiled source-mutant releases. Source-level mutation testing is therefore a direct Study 2 requirement.

The primary repeated study uses deterministic/offline synthesis. The online DeepSeek path has separate dev.2 release-gate evidence demonstrating canonical-context conditioning and semantic-conformance repair, but provider/model stochasticity is not part of the formal Study 1 dataset.

The 30-case benchmark is intentionally broad for the current implementation but remains small relative to general software requirements. Oracles were authored once, without independent inter-rater adjudication. A publication-grade extension should add multiple annotators, agreement measures, more domains, larger textual variation, and held-out cases.

Finally, p-values in the intervention arms are extremely small because the interventions affect many deterministically paired observations. They should be interpreted as confirmation that the assay reacts consistently to the specified controls, not as evidence of universal real-world effect magnitude.

## 8. Study 1 conclusion

Within the frozen Study 1 protocol, SSM's research layer correctly distinguished unchanged behaviour, controlled regression, and approved intended evolution, while localising the earliest changed stage. At the same time, SSM-Bench v2 identified concrete semantic-front-end limitations that become falsifiable targets for subsequent compiler releases.

The next research step is therefore not to make Study 1 look cleaner. It is to keep this benchmark frozen and test whether future compiler changes improve the measured baseline without creating regressions elsewhere.
