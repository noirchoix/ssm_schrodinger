# README_SOURCE_REGISTRY

This README extracts the necessary and sufficient principles from the provided source registry. It is not meant to replace the original project intent. It grounds implementation discipline using systems engineering, software architecture, compiler construction, neuro-symbolic AI, and LaTeX source-architecture references.

---

## Source families used

The uploaded registry contains these source families:

1. **Neuro-symbolic AI and symbolic reasoning**
   - Neuro-Symbolic Generative AI for Explainable Reasoning.
   - SPRING / symbolic reasoning in neural generative design.

2. **Systems engineering and lifecycle discipline**
   - Systems Engineering Guidebook.
   - Systems Engineering Fundamentals.
   - Systems Engineering Principles and Practice.

3. **Software design and architecture**
   - IEEE 1016 Software Design Descriptions.
   - Software Architecture lecture material.
   - Software Design paper.

4. **Compiler construction and language implementation**
   - Compiler Construction, Niklaus Wirth.
   - CS 132 compiler construction lectures.
   - Compiling Little Languages in Python.
   - Python Compiler Internals.

5. **LaTeX source architecture**
   - LaTeX2e GitHub source archive.

---

## Necessary principles extracted

### 1. Neural generation must be constrained by symbolic logic

Neural systems are useful for perception, semantic interpretation, and flexible generation. Symbolic systems are useful for explicit rules, formal constraints, traceability, and admissibility checks. SML Compiler should therefore use LLMs for interpretation and planning, but symbolic logic for hard decision boundaries.

### 2. A specification must address stakeholder concerns

A software design description is not just a technical note. It exists to communicate design information to stakeholders. SML must therefore model stakeholders, concerns, viewpoints, views, rationale, and completeness/consistency criteria.

### 3. Architecture is the record of significant decisions

Architecture should not include every small implementation choice. It should capture decisions that are costly to change, structurally important, or globally constraining. SML should distinguish architectural decisions from detailed implementation choices.

### 4. Systems engineering must provide lifecycle control

Requirements, architecture, implementation, integration, verification, validation, transition, risk management, interface management, configuration management, and data management must appear as first-class project lifecycle concerns.

### 5. A compiler pipeline must remain phase-disciplined

The compiler path should preserve clear phases: scanning/lexing, parsing, semantic analysis, IR construction, logic validation, resolution, code generation, diagnostics, and testing.

### 6. Little languages should be extensible

SML is a little language. It should be small, structured, and extensible through well-defined compiler modules rather than vague prompt conventions.

### 7. Documentation and implementation should be co-designed

LaTeX’s source organization demonstrates a long-lived ecosystem where documentation, source, build tooling, release packaging, tests, issue templates, and compatibility concerns are integrated. SML Compiler should similarly treat documentation, examples, tests, and generated artifacts as part of the system design.

### 8. Formal design analysis should prevent ambiguity

Ambiguity should not merely be reduced statistically. Where possible, it should be eliminated by formal claims, implications, invariants, and consistency checks.

---

## Sufficient implementation criteria

A project implementation is sufficient for v1.1 when it can do all of the following:

1. Parse a constrained SML document into a typed AST.
2. Convert the AST into a Semantic Intermediate Representation.
3. Convert SIR nodes into formal design facts.
4. Apply implication rules and constraints to derive required facts.
5. Reject candidate implementations that make the fact set inconsistent.
6. Resolve remaining valid candidates deterministically.
7. Compile the resolved IR into a FastAPI project.
8. Generate tests and dependency files.
9. Produce source maps and proof/provenance traces.
10. Recompile identical SML into identical output.
11. Explain why each generated file, import, route, schema, and dependency exists.
12. Treat generated source as a build artifact, not the source of truth.

---

## What not to import from the registry

The registry should not make the MVP too broad. Do not import every systems-engineering ceremony, every architecture viewpoint, every compiler optimization, or all LaTeX machinery.

For MVP, import only what is necessary:

- a small SML grammar;
- a small but typed SIR;
- a minimal symbolic implication engine;
- a deterministic resolver;
- one target pack;
- golden tests;
- provenance;
- source registry discipline.

Everything else belongs in later releases.
