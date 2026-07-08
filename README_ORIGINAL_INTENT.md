# README_ORIGINAL_INTENT

This README preserves the original project bias and founding goals before incorporation of the external source registry. It should remain as the philosophical anchor for the project.

---

## Original problem

AI-generated code is fast, but it is unstable. Small prompt changes can alter architecture, imports, error handling, file layout, naming, dependencies, and implementation style. This is why many senior engineers distrust AI code: not because it can never work, but because it often lacks reproducibility, discipline, and architectural restraint.

The project begins from the observation that direct prompt-to-code generation lets the model reason through implementation from scratch each time. That causes code bloat, broad exception handlers, unnecessary helper functions, invented imports, redundant abstractions, and architecture drift.

---

## Original core idea

Create a stable intermediate layer between natural-language prompting and executable source code.

```text
Natural language
  ↓
AI reasoning and documentation retrieval
  ↓
Software Markup Language
  ↓
Semantic IR
  ↓
Bounded latent choices
  ↓
Deterministic compiler
  ↓
Clean source code
```

The AI should understand intent. The compiler should generate code.

---

## Original design instinct

The system should behave more like Markdown for software than like a new programming language.

Markdown did not replace HTML. It gave humans a simpler, stable authoring format that compiled into HTML. SML should not replace Python or TypeScript. It should give humans and AI agents a stable authoring format that compiles into ordinary software projects.

---

## Original anti-bloat commitment

The generated code should avoid:

- hallucinated imports;
- broad `try/except` or `catch` blocks;
- unnecessary wrappers;
- reinvention of standard library behavior;
- excessive function definitions;
- architecture mutation across regenerations;
- untraceable implementation decisions.

---

## Original innovation

The original innovation is not simply “AI generates a DSL.”

The innovation is:

> use AI to produce a stable semantic specification, represent unresolved implementation choices as bounded possibility sets, resolve them with constraints, and compile deterministically.

---

## Original intended audience

This project is especially useful for:

- new programmers and vibe coders who need stable output;
- AI coding workflows that need reproducibility;
- teams that want AI speed without losing architecture discipline;
- open-source contributors interested in compiler-style AI systems.

Experienced engineers may still prefer writing code manually, but the system gives them an auditable specification and deterministic regeneration layer when they want automation.
