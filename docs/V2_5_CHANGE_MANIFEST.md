# V2.5 Change Manifest

## Release scope

This manifest records the repository changes used to implement V2.1–V2.5 while retaining the existing SML/SIR compiler as the deterministic source-generation authority.

- Implementation and validation files changed: **35**
- Added files: **24**
- Modified files: **11**
- Deleted files: **0**

The manifest itself is excluded from its own hash table to avoid a recursive self-hash.

## Added files

### `docs/V2_1_TO_V2_5_SCHRODINGER_ROADMAP_IMPLEMENTATION.md`

Architecture and implementation guide for the complete V2.1–V2.5 roadmap.

- SHA-256: `e6bf1b3370e16fb462c20387e7ed382fce0d2050f4156ba540e045b6ef16a50c`

### `docs/V2_5_LOCAL_VALIDATION.md`

Records framework, collapse-gate, generated-application, incremental, and variability validation results.

- SHA-256: `a7a471c5ddced3754de28163a888ae06c2c1e3694d01c19a3b4eaf5d8f585157`

### `examples/intent_inputs/hr_leave_readme.md`

Representative structured intent input used by the V2.5 end-to-end gate.

- SHA-256: `a8bccadfd66f08b413c80a90a9c133bc3a7b95ade479a71bd80da3fb45bdff35`

### `scripts/test_v25_e2e.sh`

Adds the end-to-end Schrödinger collapse, quality, type, compile, and evidence gate.

- SHA-256: `9b47348434663d9e16d3860efdb49e19ffe5ec0f2f239b30b7ca2c6bf8ef8a19`

### `src/ssm/architecture/__init__.py`

Exports constrained architecture-resolution contracts.

- SHA-256: `c547be7596930998fbc136db5521526c4a0f40ab885794325c3bda2988beec22`

### `src/ssm/architecture/resolver.py`

Implements deterministic architecture candidate evaluation, rejection proofs, use cases, transactions, events, failures, and NFR resolution.

- SHA-256: `49f772868cd3ec0eda1189dc83dd210c1c0302a6f767c47218ca37e70afb47a5`

### `src/ssm/architecture/schemas.py`

Defines typed ArchitecturePlan, candidate, proof, module, use-case, transaction, event, adapter, failure, and NFR records.

- SHA-256: `08a5042f274b293a4aa72883af498b7335505bf28f63c05032ff0b910bf248b5`

### `src/ssm/capabilities/__init__.py`

Exports capability composition types and services.

- SHA-256: `a40d2018dcd9e75be166a1753aacdba97b7c5ca12e51ecf9c4a5a4e09b9b8cb0`

### `src/ssm/capabilities/composer.py`

Resolves capability prerequisites, conflicts, support levels, guarantees, limitations, and composition issues.

- SHA-256: `515af156a799e8ed5e4a2bc4c7927e1a004036b37b9888dca8b46249fa352a9e`

### `src/ssm/capabilities/registry.py`

Defines the bounded production, scaffold, and contract-only capability-pack registry.

- SHA-256: `7b97dee4b5c097456fa346157b04d7074d77ae82504c12c9513e50bf3db3c54a`

### `src/ssm/capabilities/schemas.py`

Defines capability-pack protocol, selection, issue, and composition result schemas.

- SHA-256: `dbe62389a04ab46ac45e33158035190524a31a2223d54f31b185658ad765cdf9`

### `src/ssm/certification/__init__.py`

Exports variability and senior-grade certification services.

- SHA-256: `f6646bcbbf656c1061a234edb3ca10e2760237eeaa1355ebd65ab481726424ed`

### `src/ssm/certification/evaluator.py`

Runs repeated semantic-equivalence checks, coverage, architecture, capability-honesty, repair-boundary, and bounded-profile certification.

- SHA-256: `752716a6551279780e9fb8ccc55d830d605820c2a3cb17abe1077b79d94f53d8`

### `src/ssm/certification/schemas.py`

Defines certification checks, variability metrics, senior-grade metrics, and reports.

- SHA-256: `ef84198a1e580ab59ab132773ff5132ee3d49e41e4aa15f14f70568e75a146ec`

### `src/ssm/incremental/__init__.py`

Exports incremental compilation, dependency, failure-classification, and repair-routing services.

- SHA-256: `9ce21f2da636b2197478e199f10f02a207d02460ec5f42f878d61ba38430083b`

### `src/ssm/incremental/engine.py`

Builds semantic/artifact dependencies, performs content-addressed incremental emission, detects disk drift, classifies failures, and routes repairs by abstraction.

- SHA-256: `252d5465c8224600f94d4171784eba7b37c759642003cae138c679db638599cb`

### `src/ssm/incremental/schemas.py`

Defines dependency graphs, artifact diffs, failure classifications, and repair directives.

- SHA-256: `849cba311fc9d95d7340c1d4f34228967899964c916fa9c9c8ca8fb883e9b083`

### `src/ssm/product/__init__.py`

Exports the complete high-level Schrödinger product compiler.

- SHA-256: `ed911276075b48425b075395ebf653246507c3749d43a5a3b3bdfb500ae9c6fc`

### `src/ssm/product/compiler.py`

Orchestrates RequirementsIR, foundation, architecture, capability composition, SML, deterministic compilation, incremental emission, evidence, and certification.

- SHA-256: `8293c6ba56e9e64485711ba1df7818bf760cfdf500450db53d511354b2d6a020`

### `src/ssm/product/schemas.py`

Defines collapse-plan and product-build result contracts.

- SHA-256: `bbe150f691fd053f601ac4d3e06e39e86fd466dadae3027600598f375f825feb`

### `src/ssm/requirements/__init__.py`

Exports intent-to-requirements compiler contracts.

- SHA-256: `6a594d7b2ee1178deaa89d2cf4a1a0817ff5e614fc3748ceee3f3138a3c9074b`

### `src/ssm/requirements/extractor.py`

Implements conservative deterministic README/free-form extraction, explicit/inferred classification, contradiction detection, ambiguity and assumption registers, and unsupported-request visibility.

- SHA-256: `ca1ca52a69f7511f631b3b7d04d52ed98ca43384f763d2aa3a060414aabea96b`

### `src/ssm/requirements/schemas.py`

Defines RequirementsIR, requirement items, evidence, ambiguities, contradictions, assumptions, and semantic fingerprints.

- SHA-256: `3292d4d664923400a69a67a150258f285f68a6b7fd60a9ce60e85fd8348368cc`

### `tests/test_schrodinger_roadmap.py`

Adds roadmap regressions for deterministic requirements, blocking ambiguity, contradictions, architecture singularity, capability honesty, repair boundaries, incrementality, certification, and CLI behavior.

- SHA-256: `79c0fe9dd8d73ccca0bb5e821edb1114c7a21c78801d7fdbfabe7478d0b89d5c`

## Modified files

### `README.md`

Documents the V2.5 intent-collapse entry point, commands, bounded claims, and compatibility with the existing deterministic compiler.

- SHA-256: `a188f86085033b5e98f5222a55c188ae5f8c1d2af9734ce6f4968c1e887e26bf`

### `pyproject.toml`

Advances package metadata to 2.5.0.dev0 and updates the project description.

- SHA-256: `3054ca2161598d454141b3607856da7fae863bbf2317a0c643b81a0e25ce8365`

### `scripts/test_v15_e2e.sh`

Keeps the historical V1.5 gate compatible with the current 2.5.0.dev0 runtime.

- SHA-256: `c193731cf14b6e11520a98eb7ecfac006d322924d4701e63a06bd7b0ad5b6cff`

### `scripts/test_v20_e2e.sh`

Keeps the validated V2.0 product-platform gate compatible with the current runtime version.

- SHA-256: `254ab2ea801871068b35589a8c3d78574f0edf7f3bebbe05604a532b9d7bfe88`

### `src/ssm/__init__.py`

Exports the high-level product compiler and advances the runtime version.

- SHA-256: `9acd4b36f8427e8ef8af51f9eef000e359ca9c4d836cb2797e503023856c3ec0`

### `src/ssm/backends/python_fastapi/platform.py`

Updates generated platform and admin release metadata to the V2.5 development release.

- SHA-256: `61dce5c6e89546c311cc8c0909a022e3a13d4987227e3a9dc0032dad27eb43c5`

### `src/ssm/cli/main.py`

Adds requirements, collapse-plan, compile-intent, and certify-intent commands.

- SHA-256: `fa39ff6334a0e00c813025beed41d1b8f921465f23c083385297a16fd47189c2`

### `src/ssm/foundation/__init__.py`

Exports the new capability contract used by high-level foundation plans.

- SHA-256: `829b6ca6407fa5aa15056e497d5529ae13dd09c086e56e09f17d7f3f7f352e9d`

### `src/ssm/foundation/negotiator.py`

Negotiates composed capability support and makes partial or unsupported selections visible.

- SHA-256: `6a21f1d226dbe53046abe23b31473a83a454096db59f4e267b31368efcc86962`

### `src/ssm/foundation/renderer.py`

Renders architecture decisions and capability contracts into canonical SML and normalizes multiline scalar prose.

- SHA-256: `560963b33207d94878622cfdca4e451268469ad15ca5b999c958addb63125bf3`

### `src/ssm/foundation/schemas.py`

Extends AppFoundationPlan with capability contracts and exact requirement traceability.

- SHA-256: `0c203645e4c8a956faf57d84c23c4098c48e1959fd1c4b856c543a3de5cafe14`

## Architectural invariants retained

- Online models remain limited to high-level semantic drafting and do not become source-code authorities.
- The existing `SSMCompiler` remains the deterministic SML/SIR-to-artifact compiler.
- Unsupported, contradictory, ambiguous, inferred, and assumption-dependent requirements remain explicit.
- Capability contracts distinguish production implementations from scaffolds and contract-only support.
- Repair routing forbids semantic failures from being hidden by arbitrary generated-source edits.
- Certification is bounded to the declared supported profile and does not claim universal README-to-production coverage.

## Validation reference

See `docs/V2_5_LOCAL_VALIDATION.md` for the exact test, quality, generated-application, evidence, incremental, and variability results.
