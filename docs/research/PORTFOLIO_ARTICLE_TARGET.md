# Portfolio Research Article Target

## Working title

**Specification-Conditioned Evolution Assurance for AI-Assisted Software Generation: Design and Controlled Evaluation of the SSM Platform**

## Status label for portfolio

**Independent research and systems-engineering study — working technical report; not peer reviewed.**

## Abstract

AI-assisted software generation is often evaluated primarily at the level of final code quality, leaving the intermediate semantic decisions that connect natural-language requirements to executable systems comparatively opaque. This project presents SSM, an experimental software-generation platform designed around a deterministic semantic authority boundary. Natural-language intent is transformed through RequirementsIR, application-foundation planning, architecture resolution, capability composition and negotiation into a CanonicalSemanticContext. Offline synthesis renders SML deterministically, while online synthesis is constrained by the same canonical context; candidate SML must pass a SemanticConformanceVerifier before entering the deterministic compiler and target generator. The platform records content-addressed stage identities, evaluation evidence and paired release observations so that software evolution can be treated as a measurable experimental process rather than a sequence of unstructured model outputs.

A frozen 30-case benchmark, SSM-Bench v2, was constructed with evaluator-separated semantic oracles and independent runtime contracts. A 30×1 qualification pass completed without harness failure and exposed several limitations in the current deterministic requirements front-end, including lexical domain-trigger collisions, incomplete preservation of custom rule semantics, negation-sensitive tenancy errors and a public-auth representation mismatch. The formal offline study then executed 300 baseline and 300 unchanged-control observations. All paired statuses, measured metrics and stage fingerprints were identical, and the evolution assay returned `NO_MATERIAL_CHANGE`. Three controlled regression interventions were subsequently classified as `REGRESSION` and attributed to their preregistered first changed stages (`requirements`, `sml`, and `generated_tree`). A declared non-semantic generated-tree change was instead classified as `INTENDED_EVOLUTION` while protected semantic metrics remained unchanged. These results demonstrate the feasibility of a scientific-method-inspired assurance layer for reproducible software-generator evolution, while also identifying clear limitations and future experiments involving source-level mutants, provider drift, larger held-out benchmarks and multi-annotator semantic ground truth.

## 1. Introduction

Large language models can produce useful source code, but source generation alone does not solve a deeper engineering problem: how do we know what changed when the generator, model, prompt, compiler, dependency environment or target architecture evolves? A final application may still compile while silently losing a requirement, changing an authorization assumption, weakening a business rule or producing a different architecture. Conversely, a generated tree may change substantially while preserving all protected semantics.

SSM was developed as a general-purpose application-generation compiler rather than a fixed application template. Its central design objective is to move probabilistic assistance away from final semantic authority. Raw intent is first transformed into typed intermediate representations. The product foundation, architecture and capability envelope are resolved deterministically. These artifacts are then collapsed into a CanonicalSemanticContext. An online language model may propose SML inside that envelope, but it cannot independently redefine the product semantics: the proposal must pass semantic conformance before the compiler accepts it.

This architecture created a second research question beyond code generation itself. Once intermediate semantics become explicit and content-addressable, generator evolution can be studied experimentally. The system can record stage fingerprints, compare paired baseline and candidate runs, distinguish stochastic or immaterial change from regression, require explicit change-intent contracts for accepted trade-offs, and identify the first stage at which two executions diverge.

The resulting research direction is **specification-conditioned evolution assurance**: treating an AI-assisted software generator as an observable experimental system whose changes can be measured against stable semantic obligations.

## 2. System architecture

The current SSM pipeline is:

```text
raw intent / input.md
        ↓
RequirementsIR
        ↓
AppFoundationPlan
        ↓
ArchitectureIR
        ↓
Capability composition
        ↓
Capability negotiation
        ↓
CanonicalSemanticContext
        ↓
   ┌──────────────┬───────────────┐
   │ offline      │ online        │
   ↓              ↓               │
deterministic   constrained LLM   │
SML renderer    candidate SML     │
   │              ↓               │
   │      SemanticConformanceVerifier
   └──────────────┬───────────────┘
                  ↓
             accepted SML
                  ↓
              SSMCompiler
                  ↓
                  SIR
                  ↓
       deterministic target generation
                  ↓
          generated application
                  ↓
         quality + evidence gates
```

This boundary is important because it changes the role of the model. The model is a probabilistic semantic synthesizer, not the sole interpreter of user intent. Tenancy, persistence, capabilities, entities, workflows and protected constraints are established upstream and remain independently verifiable.

The research layer records stage identities for requirements, foundation, architecture, capabilities, negotiation, canonical context, SML, semantic conformance, SIR, generated tree and quality evidence. This makes it possible to ask not simply whether two generated applications differ, but **where their observable semantics first diverge**.

## 3. SSM-Bench v2

To evaluate the complete chain, I constructed SSM-Bench v2 as 30 end-to-end case packs rather than thirty minimal prompts. Inputs include structured READMEs, semi-structured PRDs, stakeholder notes, narrative requests, bullet notes, contradictory requirements, ambiguous requirements and unsupported feature requests.

Each case is deliberately split into four files. Only `input.md` is presented to the compiler. The semantic oracle, runtime contract and metadata are evaluator-only. This design reduces evaluation circularity: the system does not get to see the answer key it is later judged against.

The corpus exercises every RequirementsIR category and covers persistence, authentication, tenancy, audit, RBAC, workflows, local and contextual rules, integrations, contract-only capabilities, non-functional requirements, reports, ambiguity, contradiction and unsupported requests.

The benchmark was frozen after a qualification run, but freezing did not require the compiler to achieve a perfect score. That decision is central to the research design. A benchmark that is edited until the current implementation passes every case is a demonstration set, not a useful evolution benchmark.

## 4. Qualification findings

All 30 qualification cases completed without evaluator failure. RequirementsIR obligation recall was 1.0 on the explicitly labelled obligations, capability-obligation recall was also 1.0, and planned ambiguity, contradiction and unsupported-feature detections were all observed. Foundation-obligation recall was lower at 0.887, which exposed the most useful current limitations.

Seven cases intended to be generatable were instead rejected, while all four intentional fail-closed cases were correctly rejected. Of the nineteen cases that produced applications, eighteen passed the independent runtime probes.

Several failures reveal important properties of deterministic natural-language parsing. Substring-based domain triggers can misclassify ordinary language; expense requirements that mention employees can be pulled into the HR entity branch; explicit custom rules can be captured in RequirementsIR without being promoted into the executable foundation; and negated statements about tenancy can still activate positive keyword extraction. A public/no-auth case also revealed a representational mismatch between the canonical auth value and deterministic SML rendering.

These results are not hidden defects in the report. They define measurable future work. A subsequent compiler release can be compared against the exact same frozen cases to determine whether semantic fidelity improves without destabilising other slices.

## 5. Controlled evolution experiment

The formal offline experiment used 30 cases with ten replicate identifiers per case, producing 300 baseline observations and 300 unchanged-control observations. The pair key was `(benchmark_case_id, replicate_id)`.

The primary metrics were compile success, generated-file count, independent requirement recall and composite semantic-oracle score. The assurance layer uses paired exact sign tests with a four-state verdict: `NO_MATERIAL_CHANGE`, `INTENDED_EVOLUTION`, `REGRESSION` or `INCONCLUSIVE`. Slices with insufficient paired observations remain inconclusive rather than being declared stable.

The baseline and no-change control were exactly stable across all 300 pairs: status, measured metrics and stage fingerprints all matched. The assay returned `NO_MATERIAL_CHANGE` and no first-changed stage.

Three controlled interventions were then introduced with known ground truth. A requirements-boundary degradation reduced requirement fidelity and was classified as `REGRESSION`, with the first changed stage identified as `requirements`. An SML rule degradation reduced compile success and semantic score and was attributed to `sml`. A generated-tree degradation was also classified as `REGRESSION` and attributed to `generated_tree`.

Finally, an approved change-intent experiment added one non-semantic evidence artifact to generated applications while protecting compile success and semantic metrics. The file-count change was statistically material, but it remained inside the declared envelope; the system therefore returned `INTENDED_EVOLUTION` rather than regression.

## 6. What the experiment demonstrates

The strongest result is methodological rather than product promotional. The study shows that an AI-assisted software generator can be instrumented so that releases are compared through typed semantic stages and paired evidence rather than only through final source diffs or anecdotal examples.

The unchanged control demonstrates specificity under the deterministic study condition. The regression controls show that the assay can react to known degradations. The intended-evolution condition shows why statistical significance alone is not enough: some real changes are expected and acceptable, but they should be declared before evaluation and constrained by protected metrics and explicit trade-off envelopes. First-stage attribution gives the result operational meaning by identifying where the divergence first entered the pipeline.

At the same time, benchmark qualification prevents the research layer from becoming self-congratulatory. The same measurement apparatus that validates evolution assurance also identifies weaknesses in the compiler's current semantic interpretation.

## 7. Limitations

This is not yet a publication-ready claim of general reliability. The controlled perturbations in Study 1 are deterministic evidence-record intervention controls with known stage ground truth. They validate the statistical and attribution machinery, but a stronger study should compile actual source-mutant releases and test whether the same results hold when faults propagate naturally through the implementation.

The formal repeated dataset uses the deterministic/offline synthesis strategy. The online DeepSeek path has separately passed a live dev.2 release gate in which a deliberately nonconforming first proposal was rejected at semantic conformance and repaired before compilation, but provider stochasticity is not included in the present statistical experiment.

The benchmark contains 30 cases, not thousands. Its semantic oracles were authored without a second independent annotator. Before publication, I would add held-out cases, independent annotation and agreement measures, additional application domains, richer long-form requirements documents and controlled source-level mutation operators.

## 8. Future research directions

The immediate next study should replace record-level intervention controls with source-level compiler mutants located at the requirements, foundation, capability, SML and target-generation boundaries. The key question is whether the assay can retain low false-positive behaviour while detecting naturally propagated semantic regressions.

A second direction is provider/model drift. Because online synthesis now occurs after CanonicalSemanticContext, repeated provider runs can hold the semantic authority constant while measuring variance introduced specifically at candidate SML synthesis. This creates a clean experiment for comparing models, prompt versions and provider updates without conflating them with requirements interpretation.

A third direction is sequential production monitoring. Offline paired release studies can establish a noise floor; later work can test anytime-valid or sequential methods for detecting drift without repeatedly inflating false-positive rates.

Finally, the benchmark itself should evolve through new **versions**, never by silently changing the frozen v2 corpus. A larger held-out benchmark, adversarial negation cases, long PRDs, multi-file specifications and multi-annotator semantic oracles would make it possible to study requirement interpretation as a research problem in its own right.

## 9. Portfolio significance

For a research portfolio, SSM demonstrates more than code generation. The project combines compiler and intermediate-representation design, deterministic generation, constrained LLM integration, typed semantic contracts, provenance, reproducibility, benchmarking, statistical paired analysis and experimental falsifiability.

The main future-research question is therefore not simply “Can an LLM generate an application?” It is: **How can an AI-assisted software-generation system evolve while preserving an explicit semantic contract, and how can regressions be detected, classified and attributed with reproducible evidence?**

That question is suitable for continued Master's-level research and can expand into a doctoral programme if the methodology is validated on source-level mutants, larger independently annotated benchmarks and real provider/environment drift.
