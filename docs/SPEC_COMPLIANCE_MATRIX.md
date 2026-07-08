# V1 Spec Compliance Matrix

| Spec Requirement | V1 Implementation |
|---|---|
| Parse `.sml.md` files | `ssm.frontend.parser.SMLParser` |
| Build SIR from SML | `ssm.semantic.analyzer.SemanticAnalyzer` |
| Support `#Project`, `#Stack`, `#Module`, `#DataModel`, `#Route`, `#Policy`, `#Constraint`, `#Rule`, `#Invariant`, `#Test` | Parser and semantic analyzer accept all listed sections; compiler backend consumes core sections. |
| Horn-rule / implication engine | `ssm.logic.engine.LogicEngine` |
| Candidate admissibility before scoring | `ssm.resolver.engine.LatentResolver` |
| FastAPI target pack | `ssm.backends.python_fastapi.target.PythonFastAPITarget` |
| Deterministic output | Stable ordering, stable manifests, golden tests. |
| Proof/provenance traces | `proof_trace.json`, `sml.manifest.json`, source ranges in SIR nodes. |
| Agents generate/patch SML, not final code | `ssm.agents.*` expose SML-oriented outputs only. |
