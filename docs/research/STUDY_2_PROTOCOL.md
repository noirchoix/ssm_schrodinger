# Study 2 Protocol — Source-Level Evolution and Provider/Model/Scaffold Drift

## Working title

**Source-Level Regression Detection and Drift Attribution in a Canonically Constrained AI-Assisted Software Compiler**

## Status

Pre-registered design draft for execution after Study 1 evidence freeze. Study 1 artifacts and SSM-Bench v2 remain immutable during Study 2.

## 1. Motivation

Study 1 established two reference regimes for SSM V2.6 dev.2:

1. **Study 1A — deterministic reference and controlled evidence interventions.** The unchanged system produced identical paired observations, while known requirements-, SML-, and generated-tree interventions were detected and attributed to their injected stages.
2. **Study 1B — stochastic online synthesis noise floor.** The deterministic semantic front-end remained locked across 300 matched observations while online SML, SIR, and generated-tree identities varied. Final semantic conformance was 94.5% of provider-invoked observations, runtime-contract pass rate was 94.71% among accepted applications, and independent semantic-oracle means were unchanged relative to the offline reference.

Study 2 moves from synthetic evidence-record interventions to **actual source-level changes** and from a single fixed online condition to **provider/model/scaffold drift**. The central problem is to determine whether the assurance layer can separate natural stochastic variation from causally introduced compiler or synthesis changes.

## 2. Frozen reference state

Study 2 MUST use the frozen Study 1 reference without modifying it.

- Compiler/runtime: `2.6.0.dev2`
- Benchmark: SSM-Bench v2
- Benchmark digest: `5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7`
- Study 1B provider baseline: `deepseek`
- Study 1B model baseline: `deepseek-chat`
- Temperature: `0.0`
- Study 1B settings digest: `f6a6ef82e4cacde1c966224a61a8657adff7b84923c536ef209e96bab5f2f8a7`
- Replicates per case: `10`
- Cases: `30`
- Primary statistical unit: **benchmark case**, not individual replicate.

The 10 within-case replicates estimate stochastic variation. Inferential comparisons aggregate to case-level summaries or use case-clustered resampling to avoid pseudo-replication.

## 3. Research questions

### RQ2.1 — Source-level sensitivity
Can the evolution-assurance layer detect behavioral regressions caused by real compiler source changes rather than evidence-record interventions?

### RQ2.2 — Causal attribution
Can the system correctly identify the earliest causally affected compiler stage when a source mutation is introduced at a known boundary?

### RQ2.3 — Robustness under stochastic synthesis
Does regression detection remain reliable when the compiler mutation is evaluated beneath a probabilistic SML synthesis boundary whose natural variability was measured in Study 1B?

### RQ2.4 — Drift discrimination
Can the assurance layer distinguish provider/model/scaffold drift that changes representation or cost but preserves measured semantics from drift that materially changes semantic fidelity or runtime behavior?

### RQ2.5 — Strategy-aware verdict semantics
Can a strategy-aware comparison contract avoid false `REGRESSION` labels for expected structural diversity while remaining sensitive to semantic and runtime degradation?

## 4. Hypotheses

- **H2.1 Sensitivity:** source mutants that alter protected semantics or runtime behavior will produce a statistically detectable adverse effect relative to the frozen Study 1 reference.
- **H2.2 Attribution:** for deterministic upstream mutants, the first changed deterministic stage will equal the mutation's declared injection stage. For downstream mutants evaluated by replay, the first noise-qualified changed stage will equal the injected stage or the first deterministic descendant it directly affects.
- **H2.3 Noise separation:** natural Study 1B variation in raw SML/SIR/tree hashes will not by itself trigger semantic-regression classification under a strategy-aware contract.
- **H2.4 Repair robustness:** semantic-conformance repair will reduce the adverse effect of synthesis-side drift when the drift remains representable inside the canonical semantic envelope.
- **H2.5 Canonical upper bound:** source changes that degrade the deterministic canonical context will propagate into constrained online synthesis and cannot be repaired by the LLM without violating semantic authority.

## 5. Experimental structure

Study 2 is divided into two linked experiments.

### Study 2A — Actual source-level compiler mutants

#### 2A.1 Deterministic mutant calibration
Each mutant is implemented as a minimal, reviewable source diff on a separate Git branch/worktree from the frozen Study 1 commit. No runtime feature flags are permitted in the formal mutant implementation.

Each mutant first runs the 30-case benchmark once to confirm that:

- the mutation compiles;
- the intended stage is actually affected;
- unrelated infrastructure remains operational;
- the mutation does not accidentally change the benchmark, evaluator, or harness.

The calibration result is evidence only. It cannot be used to change the oracle, benchmark, statistical thresholds, or mutant definition after formal execution begins.

#### 2A.2 Formal deterministic mutant arm
For upstream semantic mutants, run the same 30 cases × 10 replicates through deterministic rendering. Because this lane is deterministic, repeated observations primarily confirm stability and provide a directly paired comparison with Study 1A.

#### 2A.3 Formal online mutant arm
For selected mutants, run the same 30 cases × 10 online replicates with the Study 1B provider settings locked. This tests whether source-level changes remain detectable under the observed synthesis noise floor.

### Study 2B — Provider/model/scaffold drift

The compiler and CanonicalSemanticContext remain frozen. Only the declared drift dimension changes.

Each drift condition is independently locked by a content-addressed configuration record containing provider, model, prompt/scaffold version, temperature, JSON mode, retry policy, token limit, timeout, date/time window, and any provider-reported model revision.

Conditions are evaluated against the original Study 1B baseline and against a same-day control rerun where feasible.

## 6. Predeclared source mutants

The initial mutant set is deliberately small and stage-separated. Each mutation must be implemented generically from semantic structure rather than hard-coded benchmark case IDs.

| ID | Source boundary | Mutation operator | Expected earliest affected stage | Protected outcome expected to degrade |
|---|---|---|---|---|
| `M-RQ-01` | Requirements extraction | Drop the first extracted explicit `business_rule` requirement when one exists | `requirements` | requirement/oracle semantic coverage |
| `M-FN-01` | Foundation planning | Remove the first planned relationship when one exists | `foundation` | foundation recall and dependent behavior |
| `M-AR-01` | Architecture resolution | Replace the selected architecture pattern with an incompatible supported alternative for qualifying cases | `architecture` | architecture conformance / generated structure |
| `M-CP-01` | Capability composition | Remove `workflow_approval` when a workflow requirement exists | `capabilities` | capability recall / workflow behavior |
| `M-SCV-01` | Semantic conformance | Suppress one missing-required-report diagnostic class | `semantic_conformance` | final semantic fidelity / runtime or report obligations |
| `M-TG-01` | Target generation | Omit the first generated application route module or route registration for qualifying apps | `generated_tree` | compile/runtime contract success |

A mutant that does not affect a case is recorded as **not applicable**, not as a successful non-regression observation.

## 7. Isolation strategy for stochastic stages

Raw first-hash mismatch is not sufficient beneath the online stochastic boundary because Study 1B showed expected variation in SML, SIR, and generated-tree identities.

Study 2 therefore uses two causal isolation modes.

### Mode A — Upstream deterministic attribution
For mutants at `requirements`, `foundation`, `architecture`, `capabilities`, `negotiation`, or canonical-context construction, any exact mismatch before SML is outside the Study 1B stochastic noise floor and is therefore decisive evidence of an upstream change.

### Mode B — Recorded-SML replay for downstream compiler mutants
For mutations at or after semantic conformance, accepted SML artifacts from the frozen Study 1B run are replayed through both:

- the frozen baseline compiler; and
- the source-mutant compiler.

The **same candidate SML bytes** are used on both sides. This removes provider sampling as a confound and permits direct causal attribution to conformance, SIR transformation, target generation, or quality gates.

Online end-to-end runs are then used as a secondary ecological-validity test, not as the sole source of causal attribution.

## 8. Provider/model/scaffold drift conditions

The exact commercial provider/model identifiers MUST be locked immediately before execution because available model names and provider revisions are temporally unstable. The design requires the following condition classes:

| Condition | Compiler | Canonical context | Provider/model | Scaffold | Purpose |
|---|---|---|---|---|---|
| `D-CONTROL` | frozen | frozen | Study 1B baseline | baseline | same-condition temporal control |
| `D-MODEL` | frozen | frozen | declared alternate model | baseline | model drift |
| `D-PROVIDER` | frozen | frozen | declared alternate provider/model | baseline | provider drift |
| `D-SCAFFOLD-MINUS` | frozen | frozen | Study 1B baseline | reduced representation envelope | scaffold weakening |
| `D-SCAFFOLD-REFORMAT` | frozen | frozen | Study 1B baseline | semantically equivalent reorganized prompt | benign scaffold variation |

The benchmark, canonical context, verifier, compiler, runtime contracts, and oracle remain unchanged in Study 2B.

## 9. Primary endpoints

### Semantic fidelity
- `oracle_requirement_recall`
- `oracle_foundation_recall`
- `oracle_capability_recall`
- `oracle_semantic_score`

### Conformance and repair
- first-candidate conformance rate
- final conformance rate
- repair probability
- repair rounds
- semantic diagnostic family distribution

### Executability and behavior
- normalized generation outcome: `GENERATED`, `BLOCKED`, `FAILED`
- compile success
- runtime-contract pass
- runtime failure family

### Evolution attribution
- exact deterministic upstream stage lock
- expected vs observed first deterministic changed stage
- noise-qualified changed stage for downstream conditions
- attribution distance in stage order

### Efficiency / operational secondary endpoints
- model calls
- input/output/total tokens
- latency
- cost when provider-reported and measured; otherwise explicitly unmeasured

## 10. Noise-floor comparison

The Study 1B baseline establishes the following observed reference values:

- upstream stage lock: `100%`
- provider-invoked observations: `200/300`
- first-candidate conformance: `171/200 = 85.5%`
- final conformance / acceptance: `189/200 = 94.5%`
- runtime-contract pass among accepted: `179/189 = 94.71%`
- normalized offline↔online outcome agreement: `299/300 = 99.67%`
- cases with repeated SML variance: `20/20` provider-invoked cases
- cases with repeated SIR variance: `19/19` accepted-generating cases
- cases with repeated generated-tree variance: `19/19` accepted-generating cases
- independent semantic-oracle mean effects: `0` for all four primary semantic metrics

Study 2 does **not** treat raw SML/SIR/tree hash variance as regression because those dimensions are already known to vary naturally in the online regime.

## 11. Statistical analysis plan

### Unit of inference
The primary inferential unit is the **benchmark case (n=30)**. Ten replicates estimate each case's stochastic outcome distribution.

### Case-level aggregation
For each case and condition, calculate:

- mean semantic score;
- final-conformance proportion;
- runtime-pass proportion;
- generation-success proportion;
- mean repair rounds;
- mean token and latency measures;
- stage-variance descriptors.

### Paired inference
- Binary paired endpoints: exact McNemar test on case-level derived binary classifications where appropriate.
- Continuous/bounded paired endpoints: paired permutation or Wilcoxon signed-rank test across case-level summaries; exact sign test retained as a conservative fallback with heavy ties.
- Effect sizes: paired mean/median difference plus cluster bootstrap 95% confidence interval by resampling benchmark cases.
- Multiple comparisons: Holm correction within each predeclared endpoint family.

Replicate-level analyses may be reported descriptively but MUST NOT be treated as 300 independent experimental units.

### Regression decision
A condition is a semantic/runtime regression only when a protected endpoint changes beyond its predeclared equivalence/noise envelope and the effect remains after case-clustered analysis. Structural artifact changes alone are not adverse in cross-strategy comparisons.

## 12. Strategy-aware equivalence contract

Study 2 introduces an explicit cross-strategy/drift contract to address the methodological issue discovered in Study 1B.

Protected metrics:

- requirement recall must not decrease materially;
- foundation recall must not decrease materially;
- capability recall must not decrease materially;
- composite semantic score must not decrease materially;
- runtime-contract pass rate must remain inside a predeclared tolerance relative to the Study 1B case-level noise distribution;
- deterministic upstream stages must remain exact for provider/model/scaffold drift conditions.

Permitted variation:

- candidate SML fingerprint;
- SIR fingerprint when semantics remain equivalent;
- generated-tree fingerprint and non-behavioral evidence/provenance files;
- token count and latency unless efficiency is the endpoint under test.

## 13. Qualification and stop rules

Every new mutant or drift condition receives a 30×1 qualification before formal 30×10 execution.

Qualification fails on:

- infrastructure error;
- benchmark digest mismatch;
- evaluator/oracle modification;
- unexpected provider invocation before a deterministic fail-closed boundary;
- canonical-context mismatch for Study 2B drift conditions;
- mutation not affecting its intended stage on any applicable case;
- inability to reproduce the frozen baseline control.

Qualification thresholds are engineering gates and are not altered after seeing formal results.

Formal execution is never stopped early because an experimental effect looks strong or weak. It may stop only for infrastructure failure, credential failure, provider outage, evidence corruption, or predeclared safety/resource limits. Interrupted runs resume into the same content-addressed output directory.

## 14. Required evidence record per observation

Each observation must record:

- benchmark case ID and replicate ID;
- source/benchmark digest;
- baseline or mutant/drift condition ID;
- Git commit SHA of the exact source state;
- mutation patch SHA-256 or drift configuration SHA-256;
- environment identity;
- provider/model/scaffold identity when applicable;
- all stage fingerprints;
- semantic-conformance attempts and diagnostics;
- independent oracle result;
- independent runtime-contract result;
- generated-app evidence bundle;
- measured latency/token/cost fields;
- content-addressed `GenerationRunRecord`.

## 15. Analysis outputs

Study 2 must produce:

1. `study2_experiment_manifest.json`
2. `study2_mutant_registry.json`
3. `study2_drift_registry.json`
4. qualification summaries per condition
5. formal case-level results table
6. case-clustered statistical report
7. attribution confusion matrix
8. source-mutant sensitivity / false-negative table
9. drift-equivalence table
10. figures comparing each condition to the frozen Study 1B noise floor
11. immutable evidence manifest and SHA-256 sums

## 16. Threats to validity

- Thirty cases limit external validity; Study 2 estimates behavior on SSM-Bench v2, not all software requirements.
- The current runtime contracts are bounded black-box probes rather than exhaustive behavioral proofs.
- Source mutants are controlled faults and may not represent the full distribution of natural compiler defects.
- Provider behavior may change without a visible model-name change.
- Model/provider comparisons can confound training differences, serving infrastructure, and undocumented provider revisions.
- Existing canonicalization defects remain part of the frozen baseline and must not be repaired mid-study.

## 17. Execution order

```text
Study 1 freeze
    ↓
source/tag lock + evidence checksums
    ↓
Study 2A mutant implementation in isolated worktrees
    ↓
30×1 qualification per mutant
    ↓
deterministic/replay formal mutant experiments
    ↓
selected 30×10 online mutant experiments
    ↓
Study 2B provider/model/scaffold conditions locked
    ↓
30×1 qualification per drift condition
    ↓
30×10 formal drift experiments
    ↓
case-clustered comparison against Study 1B noise floor
    ↓
combined research report
```

## 18. Primary interpretation target

Study 2 is designed to answer a stricter question than Study 1:

> **Can SSM distinguish real compiler or synthesis drift from the stochastic variability of an unchanged online generator, while preserving causal stage attribution and independent semantic/runtime evidence?**
