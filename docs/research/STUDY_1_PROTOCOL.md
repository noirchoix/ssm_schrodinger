# SSM Research Study 1 — Frozen Baseline and Controlled Evolution Experiment

**Protocol status:** frozen for the formal offline run after benchmark qualification.
**Research instrument:** SSM `2.6.0.dev2`, unified CanonicalSemanticContext / SemanticConformanceVerifier architecture.
**Benchmark:** SSM-Bench v2, 30 evaluator-separated end-to-end case packs.
**Primary mode:** deterministic canonical/offline synthesis.

## 1. Research objective

Study 1 evaluates whether the SSM evolution-assurance layer can distinguish an unchanged system from controlled degradations and an explicitly authorised evolution while localising the first changed semantic stage. The study also records the semantic fidelity of the frozen research instrument against independent case oracles.

This is an engineering research study of the assurance method, not a claim that SSM-Bench v2 exhaustively represents software requirements or that one provider/model generalises to all AI-assisted development.

## 2. Hypotheses

- **H1 — No-change specificity.** A baseline/control rerun using the identical instrument, benchmark, environment identity, and analysis configuration will produce `NO_MATERIAL_CHANGE`, with no first-changed stage.
- **H2 — Regression sensitivity.** Controlled degradations will produce `REGRESSION` when they materially reduce protected measured outcomes.
- **H3 — Attribution.** Controlled changes introduced at the requirements, SML, and generated-tree boundaries will be attributed to those respective first-changed stages.
- **H4 — Intended evolution discrimination.** A declared generated-tree change that adds one non-semantic evidence artifact, while preserving protected metrics, will produce `INTENDED_EVOLUTION` under an approved ChangeIntentContract.
- **H5 — Baseline fidelity is descriptive.** Independent semantic-oracle scores and qualification mismatches are reported as current instrument limitations; they are not repaired by changing benchmark labels after observation.

## 3. Experimental unit and pairing

The experimental unit is `(benchmark_case_id, replicate_id)`. Each repeated arm contains:

`30 cases × 10 replicate IDs = 300 paired observations`.

Baseline and no-change control use identical case and replicate identifiers. Candidate perturbation arms are derived from the same paired observations, preserving the pair key.

## 4. Primary measured metrics

- `compile_success`
- `generated_file_count`
- `oracle_requirement_recall`
- `oracle_semantic_score`

Secondary descriptive metrics include `requirements_coverage`, `capability_honesty`, `oracle_foundation_recall`, `oracle_capability_recall`, and `semantic_variance_score`.

All values are measured-or-absent. No synthetic value may be labelled as an observed compiler metric.

## 5. Statistical procedure

The existing evolution assay is used without post-hoc threshold changes:

- paired exact two-sided sign test;
- `alpha = 0.05`;
- minimum overall matched pairs = 30;
- four-state decision: `NO_MATERIAL_CHANGE`, `INTENDED_EVOLUTION`, `REGRESSION`, `INCONCLUSIVE`;
- slice analysis by domain pack, database, tenancy, workflow, rule complexity, and source style;
- first-changed-stage attribution using ordered stage fingerprints.

Effect is reported as mean paired candidate-minus-baseline difference. P-values are not interpreted without effect direction and intervention context.

## 6. Conditions

### Baseline

Thirty cases, ten independent repeated executions of the frozen deterministic pipeline.

### No-change control

The same instrument and benchmark are rerun with the same replicate IDs. This estimates the false-positive behaviour of the assay under a deliberately unchanged candidate.

### Controlled regression A — `requirements_drop`

For JWT-labelled cases, the intervention deterministically alters the requirements-stage identity and propagates the changed stage identity downstream while reducing independent requirement-recall evidence. Expected first changed stage: `requirements`.

### Controlled regression B — `sml_rule_drop`

For cases labelled with executable rule complexity, the intervention changes the SML boundary and downstream identities, marks compilation/acceptance as failed for the intervention record, and reduces the semantic-oracle score. Expected first changed stage: `sml`.

### Controlled regression C — `generated_tree_drop`

For cases that produced a generated tree, the intervention changes generated-tree and quality-gate identities and records failed compilation/quality outcome. Expected first changed stage: `generated_tree`.

### Intended evolution — `intended_evolution`

For cases with generated output, one non-semantic generated evidence artifact is introduced. Protected metrics are `compile_success`, `oracle_requirement_recall`, and `oracle_semantic_score`. The approved envelope permits `generated_file_count` to increase by at most one. Expected first changed stage: `generated_tree`; expected verdict: `INTENDED_EVOLUTION`.

## 7. Important limitation of the perturbation campaign

The formal controlled perturbations in Study 1 are deterministic **evidence-record intervention controls** applied to paired run records after the complete baseline execution. They are designed to validate statistical decision logic and first-stage attribution against known ground truth. They are not equivalent to compiling four separate mutated source releases.

Actual source-code mutants, provider/model drift, sequential monitoring, and online stochastic synthesis are reserved for Study 2. The live DeepSeek release gate for dev.2 provides separate engineering evidence that the online path crosses CanonicalSemanticContext and can be rejected/repaired at semantic conformance, but that release-gate run is not included in the Study 1 statistical dataset.

## 8. Qualification and freeze policy

A 30×1 qualification pass is run before formal repeated observations. Benchmark freezing depends on evaluator/harness validity, not on perfect compiler performance. Known semantic misses are preserved as baseline findings.

After the protocol, benchmark digest, and experiment manifest are frozen, the formal repeated run must not modify source cases, oracles, runtime contracts, metrics, alpha, pair keys, or change-intent envelopes.

## 9. Claim boundary

A successful Study 1 supports the claim that the implemented SSM research apparatus can produce reproducible paired evidence, maintain a low false-positive result in an unchanged control, identify deliberately injected regressions, distinguish an authorised trade-off, and localise the first changed stage under the specified intervention model. It does not establish universal software correctness or generalise to untested providers, languages, or production drift.
