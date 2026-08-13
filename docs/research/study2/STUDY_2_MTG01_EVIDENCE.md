# Study 2 — M-TG-01 Evidence Record

## Mutant

- ID: M-TG-01
- Intervention class: REGRESSION
- Target component: `PythonFastAPITarget._main`
- Mutation: omit the first deterministic domain router registration from generated `app/main.py` while preserving route module generation.
- Qualified source commit: `9ceeccbc479672ad8bd17f7473511b08c44e7a25`
- Expected and observed first causal stage: `generated_tree`

## Benchmark and replay corpus

- SSM-Bench v2 case count: 30
- Benchmark digest: `5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7`
- Replay selection rule: `first ACCEPTED Study1B replicate per benchmark case`
- Recorded accepted SML cases replayed: 19
- Affected cases: 19
- Natural negative-control cases: 0

All 19 accepted replay cases contained at least one deterministic domain router registration and were therefore affected by M-TG-01.

The reported `negative_control_lock` is not treated as substantive evidence because the natural negative-control population is empty.

## Provenance

- Provenance valid: `true`
- Branch: `study2/m-tg-01`
- Git clean: `true`
- Target module SHA-256: `7e5a0e2521abd4974bbfd508744085a2eae847fcab11bf7115668ccd1bb86422`
- Provenance SHA-256: `cf096d54876f0959b967f2b6808ed852e73af1151e6285ea6f5ca7402140a085`

## Causal replay result

- Cases compared: 19
- Affected cases: 19
- Causal input lock: `true`
- Affected effect lock: `true`
- First causal stage: `generated_tree`
- Qualified: `true`

For every affected replay case, the experiment preserved the recorded SML, compiler SML hash, SIR hash, resolved-IR hash, and generated route-module path set while removing exactly one application router registration.

The generated file count remained unchanged while the generated-tree fingerprint changed.

## Runtime-sensitive evidence

The frozen regression suite exposed an application-level consequence of the target mutation.

The generated application retained the route module but no longer registered the first domain router in `app/main.py`. A runtime test expecting:

`POST /leave-requests -> HTTP 201`

instead observed:

`POST /leave-requests -> HTTP 404 Not Found`

This is treated as mutation-sensitive downstream behavioral evidence rather than an infrastructure failure.

## Interpretation

M-TG-01 establishes a deterministic downstream regression with stochastic generation completely removed as a confound.

The exact same recorded accepted SML corpus produced the same SIR and resolved IR, but a target-generator source mutation changed application registration at the generated-tree stage.

The result therefore demonstrates that semantic correctness at SML/SIR level does not guarantee correctness of the generated application: deterministic target-generation behavior requires independent assurance.

## Artifact SHA-256

- baseline replay: `cf440d3019de7bd1b217ed889997fd1e9fef1ef86928ae3d23b97eaf2c66bad4`
- provenance: `e0a3ead1f7c993cbd047792d3a75f1ae913528136ca630480dd91fa684f3d63f`
- mutant replay: `2bdd7373e14dbb8517f1a6b025147d3c63d6eb4af0a43feae5a66dfdae7ab4d0`
- replay comparison: `1f301c2ffd7f43f1340484cd04f645f61bd968cc53ad24dd399a232114b73a02`
- runtime regression evidence: `142f8e8e1fa10f0d5b5eb7de381a72325d6153a3b4489f74c8e106571c8f39e9`
