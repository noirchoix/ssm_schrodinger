# Architecture Specification Addendum v1.1: Registry-Enriched Symbolic Logic Integration

**Base document:** Semantic Software Markup & Deterministic AI Compiler Architecture Specification v1.0  
**Addendum version:** v1.1  
**Date:** 2026-06-29

---

## 1. Change summary

This addendum adds three major updates to the v1.0 architecture:

1. **Classical symbolic logic decision layers** are now first-class compiler passes.
2. **A source registry** is added to ground architecture decisions in software architecture, systems engineering, compiler construction, neuro-symbolic AI, and LaTeX source-architecture references.
3. **README strategy** is split into two documents: one preserving the original project intent and another synthesizing necessary and sufficient registry-derived design principles.

---

## 2. Revised thesis

Version 1.0 described the project as entropy management: reducing ambiguity from natural language into deterministic code.

Version 1.1 keeps that thesis but strengthens it:

> Entropy is reduced by structured representation; ambiguity is eliminated by symbolic admissibility checks wherever the system can express the decision as facts, implications, invariants, or satisfiability constraints.

The revised pipeline is:

```text
Natural language
  ↓
Structured requirements
  ↓
SML
  ↓
SIR
  ↓
Logic facts and implication rules
  ↓
Admissible candidate set
  ↓
Latent resolution
  ↓
Resolved IR
  ↓
Deterministic codegen
```

---

## 3. Why symbolic logic belongs in the core

LLM outputs are probabilistic. Compiler outputs must be reproducible. The bridge between those domains is not only grammar. It is logic.

The system should use symbolic logic to answer questions such as:

- Does this candidate violate an explicit policy?
- Does this route require a schema that does not exist?
- Does this package choice conflict with the selected framework version?
- Does this architecture introduce a circular dependency?
- Does this generated import correspond to a required symbol?
- Does every stakeholder concern have at least one design view?
- Does every required design constraint have an implementation or an explicit deferral?

---

## 4. New compiler pass order

```text
1. Include expansion
2. Lexing
3. Parsing
4. SML AST validation
5. Semantic analysis
6. SIR graph construction
7. Fact extraction
8. Symbolic implication closure
9. Invariant and consistency checking
10. Candidate pool generation
11. Candidate admissibility filtering
12. Candidate scoring
13. Deterministic collapse
14. Resolved IR validation
15. Code generation
16. Formatting
17. Static analysis
18. Tests
19. Proof/provenance packaging
```

---

## 5. New repository modules

```text
compiler/
  logic/
    facts.py
    rules.py
    engine.py
    constraints.py
    proof.py
    export.py
  semantic/
    fact_extractor.py
  resolver/
    admissibility.py
registry/
  source_registry.yaml
  source_registry.md
docs/
  logic_decision_layer_spec.md
```

---

## 6. Registry-derived design updates

### 6.1 Neuro-symbolic AI

The project should explicitly adopt a hybrid design: neural interpretation for flexible understanding, symbolic rules for formal constraints and explainable decision traces.

### 6.2 SPRING design-generation pattern

SPRING demonstrates a useful pattern: a neural model proposes candidates, then symbolic reasoning filters choices that violate explicit constraints. SML Compiler should apply the same architecture to software generation: candidate implementations are proposed, but only logically admissible candidates survive.

### 6.3 IEEE 1016 / architecture description discipline

SML should support stakeholders, concerns, viewpoints, views, design rationale, consistency, and completeness. These concepts should not be optional documentation fluff. They are how the system knows what the design is supposed to satisfy.

### 6.4 Systems engineering

The compiler should treat requirements, architecture, implementation, integration, verification, validation, risk, configuration, interface, and technical data management as lifecycle entities.

### 6.5 Compiler construction

The project should preserve classic compiler phase separation. Every phase should own one concern and pass a structured artifact to the next phase.

### 6.6 Little-language implementation

SML should remain small and extensible. Implement features through parser/schema/semantic modules, not prompt conventions.

### 6.7 Python internals

The Python backend should be AST-aware. Grammar, parser, AST, and code generation boundaries should remain explicit.

### 6.8 LaTeX source architecture

LaTeX suggests four useful patterns:

- source and documentation should be co-designed;
- public authoring syntax should be separated from implementation machinery;
- hooks/templates should provide safe extension points;
- tests, issue templates, release manifests, and compatibility policy are part of long-lived language infrastructure.

---

## 7. SML grammar extensions

Add top-level sections:

```text
#Stakeholder
#Concern
#Viewpoint
#View
#Rule
#Invariant
#Assumption
#Decision
#ProofRequirement
#Risk
#Interface
#ConfigurationItem
```

MVP should implement only:

```text
#Rule
#Invariant
#Assumption
#Decision
```

The others can be parsed as structured sections but not fully enforced until later releases.

---

## 8. Updated MVP acceptance criteria

The MVP is not complete until it can reject invalid codegen candidates through symbolic logic.

Minimum examples:

1. A route references a missing body schema → compiler fails with a specific SML error.
2. A policy forbids broad exception handlers → broad exception candidate is rejected.
3. PostgreSQL is selected → `DATABASE_URL` environment requirement is derived.
4. Auth is required → security dependency is derived.
5. Same SML compiles twice → identical output and identical proof trace.

---

## 9. Updated evaluation metrics

Add these metrics to the v1.0 benchmark suite:

| Metric | Meaning |
|---|---|
| Candidate rejection precision | Invalid candidates rejected correctly |
| Candidate rejection recall | All known invalid candidates rejected |
| Proof completeness | Generated decisions have supporting facts/rules |
| Unsat diagnostic quality | Contradictions are explained at SML/SIR level |
| Derived requirement coverage | Required artifacts derived from rules are generated |
| Logic determinism | Same facts/rules produce same closure and proof order |

---

## 10. Updated handoff instruction

Future development agents must not bypass the symbolic layer. Any candidate resolver must call admissibility checks before scoring. Any generated source element must be explainable by SML source, SIR node, rule, candidate, target-pack default, or explicit compiler assumption.
