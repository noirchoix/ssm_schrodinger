# SSM Research Study 1 — Combined Results Report

## Study scope

This report combines **Study 1A (deterministic semantic pipeline and controlled evolution assurance)** with **Study 1B (canonical-context-constrained online SML synthesis using DeepSeek)** over the same frozen SSM-Bench v2 corpus.

The frozen benchmark contains 30 end-to-end case packs and retains corpus digest:

`5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7`

The central experimental design holds the deterministic semantic front-end constant and changes only the SML synthesis strategy:

```text
same input.md
    ↓
RequirementsIR
    ↓
FoundationPlan
    ↓
ArchitectureIR
    ↓
Capabilities
    ↓
Negotiation
    ↓
CanonicalSemanticContext
    ↓
    ├── Study 1A: deterministic SML renderer
    └── Study 1B: DeepSeek candidate SML + semantic conformance + bounded repair
    ↓
SSMCompiler → SIR → deterministic target generation
    ↓
independent semantic oracle + runtime contract
```

The combined study therefore separates variation in **semantic interpretation** from variation in **probabilistic specification synthesis**.

---

## 1. Study 1A — deterministic reference

Study 1A used 30 cases × 10 replicates, producing 300 baseline observations and 300 no-change control observations. The unchanged control was exactly stable across all pairs:

- status equality: 300/300;
- metric-map equality: 300/300;
- stage-fingerprint equality: 300/300;
- evolution verdict: `NO_MATERIAL_CHANGE`;
- first changed stage: `null`.

Controlled intervention arms behaved as intended:

| Condition | Verdict | First changed stage |
|---|---|---|
| No-change control | `NO_MATERIAL_CHANGE` | `null` |
| Requirements degradation | `REGRESSION` | `requirements` |
| SML rule degradation | `REGRESSION` | `sml` |
| Generated-tree degradation | `REGRESSION` | `generated_tree` |
| Approved evidence-file addition | `INTENDED_EVOLUTION` | `generated_tree` |

The strongest methodological result from Study 1A is that the assay distinguished unchanged behavior, declared intended evolution, and known regressions while localising the earliest affected stage under controlled ground truth.

Study 1A also preserved known benchmark failures instead of tuning them away. The deterministic semantic front-end showed limitations in substring domain triggers, domain precedence, negated tenancy parsing, custom rule promotion, and a public/no-auth representation mismatch. These remain part of the frozen baseline defect profile.

---

## 2. Study 1B — formal 30 × 10 online experiment

Study 1B reused the same 30 cases and the same deterministic upstream semantics. The formal arm contains:

- 30 cases;
- 10 replicates per case;
- 300 total online observations;
- 200 observations in which the provider was invoked;
- 100 observations correctly stopped before the provider by the deterministic semantic boundary.

The online condition was locked to:

```text
provider            deepseek
model               deepseek-chat
temperature         0.0
JSON mode           true
max output tokens   3000
max retries         2
timeout              60 s
settings SHA-256     f6a6ef82e4cacde1c966224a61a8657adff7b84923c536ef209e96bab5f2f8a7
```

### 2.1 Structural integrity of the experiment

The upstream stage lock held for every matched observation:

| Stage | Exact Study 1A ↔ Study 1B match rate |
|---|---:|
| RequirementsIR | 100% |
| FoundationPlan | 100% |
| ArchitectureIR | 100% |
| Capabilities | 100% |
| Negotiation | 100% |
| Normalised CanonicalSemanticContext | 100% |

`upstream_stage_lock = true` and `upstream_stage_mismatches = {}`.

This is the central architecture result: provider stochasticity did not alter the deterministic interpretation of the original requirement.

### 2.2 Online acceptance and repair

Among the 200 provider-invoked observations:

- first-candidate semantic conformance passed in **171/200 = 85.5%**;
- final conformance passed in **189/200 = 94.5%**;
- accepted online observations: **189/200 = 94.5%**;
- 29 observations initially failed semantic conformance;
- bounded repair recovered 18 of those 29 observations;
- 11 remained rejected after the allowed repair budget.

A 95% Wilson interval for the final acceptance proportion is approximately **90.4%–96.9%**.

The failures are strongly concentrated rather than diffuse:

- `SSMB2-003`: 10/10 rejected because of the pre-existing `None` versus `null` authentication representation mismatch (`SCV002`);
- `SSMB2-021`: 9/10 accepted; one replicate exhausted repair after repeatedly introducing a non-canonical business rule and/or omitting `LowStockSummary`;
- all other provider-invoked cases were accepted in all ten replicates.

Cases requiring recurrent semantic repair were:

- `SSMB2-010`: 8/10 first proposals missed the canonical `OperationalSummary` report; all were repaired successfully;
- `SSMB2-014`: 2/10 first proposals missed `LowStockSummary`; both were repaired successfully;
- `SSMB2-021`: 9/10 first proposals were non-conforming; eight were repaired and one exhausted the repair budget;
- `SSMB2-003`: all ten remained blocked by the systematic representation mismatch.

This provides direct repeated evidence that the semantic-conformance boundary is not merely passive validation: it corrected recurrent model deviations before compilation.

### 2.3 Runtime-contract performance

Of the 189 accepted generated applications, **179 passed the independent runtime contract**, for a measured runtime pass rate of:

`179 / 189 = 94.7089947%`

The ten runtime failures are all repetitions of `SSMB2-004`, whose canonical semantic front-end already exhibits the known Todo-to-HR misclassification seen in Study 1A. Thus the online synthesizer reproduced an inherited upstream semantic error rather than creating a new runtime failure class.

As a diagnostic, excluding this pre-existing case leaves 179/179 runtime passes among the other accepted applications. This exclusion is not used as the primary study metric; it simply identifies the concentration of the failure mode.

### 2.4 Semantic fidelity

Across all 300 matched Study 1A/Study 1B observations, the independent semantic-oracle metrics were unchanged:

| Metric | Study 1A mean | Study 1B mean | Paired effect |
|---|---:|---:|---:|
| Requirement recall | 1.0000 | 1.0000 | 0 |
| Foundation recall | 0.8872222 | 0.8872222 | 0 |
| Capability recall | 1.0000 | 1.0000 | 0 |
| Composite semantic score | 0.9812037 | 0.9812037 | 0 |

Every paired observation for these four metrics was equal; each exact paired sign test therefore returned p = 1.0.

This means Study 1B introduced substantial representational variability without measurable loss under the frozen independent semantic oracle.

### 2.5 Where stochasticity entered

First-changed-stage attribution examined all 300 matched pairs and localised every online/offline divergence that crossed the stochastic boundary to:

`first_changed_stage = sml`

with 200 changed pairs attributed to `sml`. The remaining 100 observations were stopped before provider synthesis.

Within the 20 provider-invoked benchmark cases, all 20 showed more than one candidate-SML fingerprint across the ten repeats. Across these cases the number of distinct SML fingerprints ranged from 2 to 8, with mean 4.55 and median 5.

Among the 19 cases that produced accepted applications, all 19 also showed SIR and generated-tree fingerprint variance across repeated online synthesis. Most had ten distinct SIR/tree identities across ten runs. This demonstrates strong artifact-level variability even at temperature 0.

However, artifact identity is not equivalent to semantic or behavioral identity. The independent semantic-oracle scores remained unchanged, and runtime failures were confined to the already-known upstream defect. The study therefore supports a distinction between **representation variance** and **measured semantic/runtime variance**.

---

## 3. Interpretation of the generic assay `REGRESSION` verdict

The raw Study 1B analysis file reports an overall strategy-assay verdict of:

`REGRESSION`

That label must **not** be interpreted as evidence that DeepSeek caused a semantic regression.

The generic evolution-assurance classifier was designed for comparing software releases under a change-intent contract. In the Study 1A ↔ Study 1B strategy comparison it detected a statistically significant change in `generated_file_count`:

- Study 1A mean: 55.0333;
- Study 1B mean: 55.1133;
- mean difference: +0.08 files;
- exact sign-test p ≈ 1.85×10^-24.

Because no strategy-specific ChangeIntentContract authorised that structural difference, the release classifier correctly followed its own rule and labelled the comparison `REGRESSION`.

For this experiment, however, a small change in generated-file count is not intrinsically adverse. The semantic metrics are identical and compile success differs by only one observation (0.6333 versus 0.6300; non-significant). The appropriate research interpretation is therefore:

> **statistically detectable structural divergence with preserved measured semantic fidelity**, not semantic regression.

This is itself a methodological finding: **release-evolution verdict semantics should not be reused unchanged for cross-strategy experiments.** Future analysis should add a strategy-comparison contract or a dedicated classifier that distinguishes adverse changes from expected structural differences between deterministic and probabilistic synthesis strategies.

---

## 4. Interpretation of the 36.7% status-match rate

The analysis reports:

`status_match_rate = 0.3666667`

This value is primarily a status-taxonomy mismatch, not evidence that 63.3% of applications behaved differently.

Study 1A uses `CONDITIONAL` for successfully generated baseline observations, whereas Study 1B uses `ACCEPTED`. The 110 pairs that were rejected in both arms therefore match textually, while successful observations usually compare `CONDITIONAL` with `ACCEPTED`. This produces approximately 110/300 = 36.7% exact string equality.

A future combined analyzer should compare a normalised outcome class such as `generated/blocked/failed` rather than raw arm-specific status labels.

---

## 5. Main combined findings

The combined experiment supports five evidence-backed conclusions.

1. **The deterministic semantic front-end was stable.** Requirements, foundation, architecture, capability composition, negotiation and the normalised canonical semantic context were locked across all 300 paired Study 1A/Study 1B observations.

2. **Stochasticity entered where designed.** First-changed-stage attribution localised online/offline divergence to SML synthesis rather than to upstream requirements interpretation.

3. **Surface and intermediate artifacts varied substantially.** Every provider-invoked case produced multiple SML forms across ten repeats, and every successfully generated case showed SIR/tree fingerprint variance.

4. **Measured semantic fidelity remained stable.** All paired independent semantic-oracle metrics were exactly unchanged across all 300 pairs.

5. **Semantic conformance materially constrained the model.** Recurrent missing reports and invented executable rules were rejected and usually repaired before compilation; 18 of 29 initially nonconforming observations were recovered, while the remaining failures were dominated by one known systematic representation defect.

The results support the research proposition that probabilistic SML synthesis can exhibit high representation variance while preserving a deterministic semantic authority and stable measured semantics, provided candidate specifications are constrained by explicit canonical context and semantic conformance.

---

## 6. Limits on the claim

The study does **not** establish universal behavioral equivalence. The runtime contracts are intentionally independent but bounded; unchanged oracle/runtime results cannot prove equivalence for behaviors that were not tested.

The benchmark contains only 30 cases and uses one provider/model condition. The oracles were not independently double-annotated. Temperature 0 did not eliminate output variance, but the study does not estimate how the distribution changes at other temperatures or under other providers/models.

The online run also inherits deterministic semantic-front-end defects. In particular, `SSMB2-004` demonstrates that a strong conformance boundary can faithfully preserve an incorrect upstream canonical interpretation. Canonicalization quality is therefore a causal upper bound on constrained synthesis quality.

Finally, the generic release-assay verdict is not a valid standalone strategy-quality label. The Study 1B result should be interpreted through the strategy-specific metrics and independent oracles, not by the raw `REGRESSION` string alone.

---

## 7. Research decision and next study

Study 1 is now complete as a two-part experiment:

- **Study 1A:** deterministic stability, controlled evolution classification and first-stage attribution;
- **Study 1B:** repeated provider variance under a fixed canonical semantic authority.

The next research milestone should be **Study 2 — source-level perturbation and provider/model drift**. It should preserve SSM-Bench v2 unchanged and introduce controlled source mutants at the requirements, foundation, capability, conformance and target-generation stages, followed by provider/model/scaffold comparisons. The objective is to test whether the assurance layer can distinguish naturally propagated regressions from the stochastic noise floor measured in Study 1B.

No Study 1 rerun is required for the present evidence bundle. The raw online evidence should now be frozen and checksummed before any compiler or analysis-code modification.
