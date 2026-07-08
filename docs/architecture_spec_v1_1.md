# Semantic Software Markup & Deterministic AI Compiler  
## Architecture Specification v1.0

**Document status:** Draft v1.0  
**Intended audience:** AI development agent, human software architect, compiler engineer, open-source contributor, technical founder  
**Primary purpose:** Transfer the full project context and technical architecture to another chatbot or development team without losing the original intent.  
**Project codename:** SSM / SML Compiler  
**Core thesis:** AI should understand software intent; deterministic compilers should generate final code.

---

# Table of Contents

1. Executive Summary  
2. Origin of the Idea  
3. Problem Definition  
4. Core Design Philosophy  
5. Non-Goals  
6. Terminology  
7. End-to-End System Overview  
8. Entropy Reduction Model  
9. Software Markup Language (SML)  
10. Formal SML Grammar Draft  
11. Semantic Intermediate Representation (SIR)  
12. Latent Resolution Engine  
13. Compiler Architecture  
14. Agent Architecture Using PydanticAI  
15. RAG and Documentation Intelligence Layer  
16. Target Language Strategy  
17. Python Backend Target  
18. TypeScript / Node.js Integration  
19. Frontend Target Packs  
20. Validation System  
21. Static Analysis and Repair Loop  
22. Deterministic Regeneration and Diff Stability  
23. Repository Architecture  
24. Runtime Services and APIs  
25. CLI Specification  
26. Pydantic Data Models  
27. Algorithms  
28. Security, Sandboxing, and Supply Chain Controls  
29. Observability and Provenance  
30. Testing Strategy  
31. Evaluation Benchmarks  
32. MVP Scope  
33. Development Roadmap  
34. Open-Source Governance  
35. Risks and Mitigations  
36. Example End-to-End Flow  
37. Handoff Prompt for Another AI Developer  
38. Appendices  
39. References  

---

# 1. Executive Summary

This project defines a new software synthesis architecture designed to make AI-generated code more stable, reproducible, auditable, and maintainable.

The system introduces a human-readable **Software Markup Language (SML)** that sits between natural-language requirements and executable source code. SML is inspired by Markdown and markup languages, but it is not a document format. It is a semantic specification format for software systems.

The core idea is:

```text
Natural-language request
    ↓
AI intent understanding
    ↓
Structured requirements
    ↓
Software Markup Language
    ↓
Semantic Intermediate Representation
    ↓
Latent Resolution Engine
    ↓
Deterministic compiler
    ↓
Target source code
    ↓
Validation, tests, repair
```

The AI is responsible for interpreting intent, researching documentation, planning architecture, and filling a structured semantic representation. The compiler is responsible for code emission. This separation is deliberate. It prevents the language model from regenerating arbitrary source code from scratch every time a prompt changes.

The project addresses a major weakness in current AI coding workflows: prompt instability. Equivalent prompts often produce substantially different architecture, imports, abstractions, and code style. This causes code drift, bloated implementation, unnecessary try/except blocks, hallucinated imports, and poor maintainability.

The proposed solution is to reduce entropy progressively:

```text
Unbounded natural language
    ↓
bounded requirements model
    ↓
SML document
    ↓
semantic graph
    ↓
latent candidate pools
    ↓
resolved deterministic IR
    ↓
source code
```

The system does not attempt to build a new runtime language. It piggybacks on existing ecosystems such as Python, TypeScript, Node.js, FastAPI, React, Pydantic, PydanticAI, AST tooling, linters, formatters, test frameworks, and package managers.

The intended MVP should compile a constrained SML subset into a small production-grade Python FastAPI backend and, optionally, a React or Svelte frontend. The long-term vision is a generalized semantic compiler for AI-assisted software generation.

---

# 2. Origin of the Idea

The project began from an observation about AI-generated code:

Experienced developers often distrust AI-generated code not because AI cannot produce working code, but because AI-generated code is structurally unstable. A model can produce a working implementation quickly, but small prompt changes can mutate the architecture, regenerate unrelated sections, introduce redundant abstraction, or change coding patterns.

Common symptoms include:

- Excessive defensive coding.
- Broad `try/except` or `try/catch` blocks with no meaningful error handling.
- Hallucinated imports.
- Reimplementation of standard library behavior.
- Unnecessary helper functions.
- Architecture drift between generations.
- Inconsistent naming.
- Over-engineered edge-case handling.
- Bloated code produced because the model externalizes implementation reasoning into source code.

The insight was that AI code generation currently resembles asking a model to think through implementation from scratch on every request. The remedy is not only better prompting. The remedy is a compiler architecture.

The proposed architecture introduces a semantic layer between prompt and code. This layer behaves like a stable, versionable, structured specification that can be validated, diffed, resolved, and compiled deterministically.

The analogy is:

```text
Markdown : HTML
SML      : source code
```

Markdown succeeded because it gave humans a simpler authoring format that compiled into HTML. SML should give humans and AI systems a simpler semantic authoring format that compiles into implementation code.

A second analogy is:

```text
Source code → compiler IR → machine code
Natural language → semantic IR → source code
```

The project effectively proposes an "AI compiler IR" for software systems.

---

# 3. Problem Definition

## 3.1 Primary Problem

Current AI-assisted programming tools often generate source code directly from natural language. This creates instability because the natural-language prompt is too unconstrained and the output space is too large.

A prompt such as:

```text
Build a secure login endpoint in FastAPI.
```

can lead to multiple valid but inconsistent implementations:

- OAuth2 password flow.
- Custom JWT flow.
- Session-cookie flow.
- Dependency-injected auth service.
- Single-file implementation.
- Layered service/repository architecture.
- SQLAlchemy model.
- Raw SQL model.
- Pydantic v1-style schemas.
- Pydantic v2-style schemas.
- Different file layouts.
- Different error policies.

All of those may be defensible, but direct generation does not guarantee consistency.

## 3.2 Secondary Problems

### Prompt Drift

Equivalent prompts produce non-equivalent implementations.

### Code Drift

Regenerating one feature changes unrelated code.

### Import Hallucination

The model emits packages, symbols, or methods that do not exist.

### Bloat

The model creates wrappers, validators, handlers, and abstractions that are not justified by the specification.

### Weak Incrementality

The model often rewrites a whole file instead of making a minimal semantic change.

### Low Auditability

It is difficult to trace why a specific line of generated code exists.

### Poor Version Control Semantics

Generated source diffs are noisy. The meaningful design-level change is buried inside implementation churn.

### Weak Reuse of Official Documentation

The model may rely on stale or mixed knowledge unless a documentation retrieval layer constrains it.

## 3.3 Target Outcome

The system must make AI-assisted code generation:

- Stable.
- Deterministic after semantic resolution.
- Auditable.
- Reproducible.
- Validatable.
- Incrementally regenerable.
- Less bloated.
- Less prone to hallucinated imports.
- Friendly to Git diffs.
- Friendly to human review.

---

# 4. Core Design Philosophy

## 4.1 AI Understands Intent; Compiler Emits Code

The AI should not be the final source-code writer wherever deterministic compilation is possible.

The AI should produce:

- Requirements.
- Architecture decisions.
- SML.
- Candidate choices.
- Rationale.
- Documentation mappings.

The compiler should produce:

- Files.
- Imports.
- Functions.
- Classes.
- Routes.
- Tests.
- Configuration.
- Project layout.

## 4.2 SML Is the Source of Truth

Generated code is a build artifact. SML is the canonical project specification.

When a user changes a requirement, the system should update SML first, not mutate source directly.

## 4.3 Progressive Constraint

The pipeline progressively narrows possible outcomes:

```text
Natural language: infinite possibilities
Requirement model: constrained possibilities
SML: grammar-bound possibilities
SIR: typed graph possibilities
Latent candidates: bounded implementation choices
Resolved IR: one selected implementation
Codegen: deterministic output
```

## 4.4 Piggyback on Existing Languages

The project must not create a new runtime language. It should use mature target ecosystems.

The compiler should emit normal code in existing languages such as:

- Python.
- TypeScript.
- JavaScript.
- Rust in later phases.

The system should use existing tools:

- PydanticAI for AI orchestration.
- Pydantic for schema validation.
- Python `ast` for Python AST handling.
- TypeScript compiler API or AST tools for TypeScript.
- Node.js tooling for CLI/package workflows.
- Linters, formatters, test runners, and type checkers.

## 4.5 Determinism After Resolution

Before latent choices are resolved, the system may use probabilities, embeddings, candidate scoring, and semantic retrieval.

After resolution, code generation must be deterministic.

The same SML, same dependency versions, same compiler version, and same resolution policy must produce the same output.

## 4.6 Human-Readable, Machine-Strict

SML must be readable enough for a human to review and edit, but strict enough to parse and validate.

It should not become loose pseudocode.

## 4.7 Versionable Specification

SML and SIR should support stable diffs. A design change should appear as a small semantic change, not a full source rewrite.

---

# 5. Non-Goals

The project is not:

- A new general-purpose programming language.
- A replacement for Python, TypeScript, JavaScript, Rust, or C++.
- A new runtime VM.
- A pure prompt-engineering framework.
- A code-generation template engine only.
- A no-code tool.
- A visual UML tool.
- A one-shot app generator.
- A replacement for experienced developers.

The project should avoid:

- Hidden magical generation.
- Unbounded agent autonomy.
- Overly broad MVP targets.
- "Generate any app" marketing before the constrained compiler is stable.
- Treating source code as the primary source of truth.
- Designing a grammar so vague that it becomes pseudocode.

---

# 6. Terminology

## Natural-Language Intent

The user's unstructured request, e.g.:

```text
Build an inventory management system with JWT auth and an admin dashboard.
```

## Requirements Model

A structured Pydantic object representing clarified requirements.

## SML

Software Markup Language. A human-readable semantic markup format for software architecture and behavior.

## SIR

Semantic Intermediate Representation. A typed graph produced from SML.

## Latent Node

A semantic node whose final implementation choice has not yet been resolved.

## Candidate Pool

A bounded set of possible implementations for a latent node.

## Collapse

The act of selecting one candidate from a candidate pool using deterministic constraints, scores, policies, and tie-breaking.

## Deterministic IR

The fully resolved intermediate representation from which code can be generated without model creativity.

## Target Pack

A backend implementation module that knows how to compile resolved IR into a specific stack, such as FastAPI or React.

## Provenance

Metadata explaining where a decision came from: prompt, SML line, retrieved documentation, user preference, compiler default, or validation rule.

## Golden Test

A test that verifies stable compiler output for a known SML input.

---

# 7. End-to-End System Overview

## 7.1 High-Level Pipeline

```mermaid
flowchart TD
    A[User Request] --> B[Intent Agent]
    B --> C[Requirements Model]
    C --> D[Research / RAG Agent]
    D --> E[Implementation Knowledge Pack]
    C --> F[Architecture Agent]
    E --> F
    F --> G[SML Document]
    G --> H[SML Parser]
    H --> I[Semantic Intermediate Representation]
    I --> J[Latent Resolution Engine]
    J --> K[Resolved IR]
    K --> L[Compiler Backend]
    L --> M[Generated Source Tree]
    M --> N[Formatter / Linter / Type Checker]
    N --> O[Test Runner]
    O --> P[Repair Agent if needed]
    P --> G
```

## 7.2 Major Subsystems

1. **AI Orchestration Layer**
   - Uses PydanticAI.
   - Produces structured outputs.
   - Coordinates intent, research, architecture, repair, and explanation agents.

2. **Documentation Intelligence Layer**
   - Retrieves official framework documentation.
   - Builds package knowledge packs.
   - Stores documentation snippets with provenance.

3. **SML Frontend**
   - Lexes and parses SML.
   - Produces parse tree and SML AST.
   - Validates syntax.

4. **Semantic Analyzer**
   - Converts SML AST into SIR.
   - Resolves references.
   - Enforces semantic rules.

5. **Latent Resolution Engine**
   - Represents bounded ambiguity.
   - Scores candidates.
   - Applies constraints.
   - Collapses latent nodes into deterministic choices.

6. **Compiler Backend**
   - Emits source files.
   - Emits tests.
   - Emits configuration.
   - Uses target packs.

7. **Validation and Repair System**
   - Runs static analysis.
   - Runs tests.
   - Maps failures back to SML/SIR nodes.
   - Repairs semantic representation instead of blindly editing source.

8. **CLI / API / Developer Tooling**
   - Allows local compilation.
   - Supports inspection, diffing, validation, benchmarking, and packaging.

---

# 8. Entropy Reduction Model

The project can be understood as entropy management.

Natural language has extremely high entropy. It contains many valid interpretations. Direct code generation asks the model to select from an unbounded space.

SML reduces entropy by forcing the model to express intent in typed sections.

SIR reduces entropy further by converting markup into a structured semantic graph.

The Latent Resolution Engine keeps ambiguity only where ambiguity is legitimate. Each unresolved choice is represented as a bounded candidate set.

The compiler eliminates entropy by emitting deterministic source code.

## 8.1 Entropy Stages

| Stage | Entropy Level | Example |
|---|---:|---|
| Natural language | Very high | "Build login" |
| Requirements model | High but structured | Auth required, JWT preferred |
| SML | Medium | `#Auth strategy: jwt` |
| SIR | Low-medium | `AuthNode(strategy=jwt)` |
| Latent candidates | Low | password hashing library candidates |
| Resolved IR | Near zero | selected `passlib[bcrypt]` |
| Codegen | Zero | deterministic file output |

## 8.2 Important Principle

The system should never pretend ambiguity does not exist. It should represent ambiguity explicitly and collapse it only when sufficient constraints exist.

---

# 9. Software Markup Language (SML)

## 9.1 Purpose

SML is the stable, human-readable specification layer for software systems.

It describes:

- Project metadata.
- Stack choices.
- Modules.
- Data models.
- APIs.
- Services.
- UI components.
- State.
- Errors.
- Policies.
- Constraints.
- Tests.
- Deployment.
- Dependencies.

It does not describe every low-level implementation line.

## 9.2 File Extensions

Recommended supported extensions:

```text
.sml.md
.sml
.ssm
```

MVP recommendation:

```text
project.sml.md
```

This preserves Markdown readability while signaling compiler semantics.

## 9.3 Design Requirements

SML must be:

- Human-readable.
- Line-addressable.
- Parseable.
- Strictly structured.
- Versionable.
- Diff-friendly.
- Extensible.
- Compatible with AI generation.
- Compatible with human editing.
- Mappable to typed Pydantic models.
- Mappable to deterministic compiler IR.

## 9.4 Basic SML Example

```sml
#Project
name: Inventory System
description: Track products, suppliers, stock movements, and admin users.
version: 0.1.0

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT
frontend: React
package_manager: uv

#Module Inventory
purpose: Manage products and stock quantities.

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required
  quantity: int default=0
  created_at: datetime auto_now_add

#Route ListProducts
method: GET
path: /products
auth: required
returns: Product[]

#Route CreateProduct
method: POST
path: /products
auth: admin
body: ProductCreate
returns: Product

#Policy Errors
not_found: 404
validation_error: 422
unauthorized: 401

#Test
case: create product
expect:
  status: 201
  response_contains: sku
```

## 9.5 SML Section Model

Every top-level section begins with a heading directive:

```sml
#Project
#Stack
#Module <Name>
#DataModel <Name>
#Route <Name>
#Service <Name>
#Component <Name>
#State <Name>
#Event <Name>
#Policy <Name>
#Constraint <Name>
#Test <Name>
#Deploy <Name>
```

Sections contain key-value fields, nested lists, and optional block directives.

## 9.6 Comments

```sml
// single-line comment
```

Markdown comments may also be allowed in `.sml.md` mode:

```html
<!-- comment -->
```

Compiler comments should be preserved in source maps but ignored semantically.

## 9.7 Namespaces

Names should resolve within namespaces:

```sml
#Namespace auth

#Service TokenIssuer
...
```

Fully qualified name:

```text
auth.TokenIssuer
```

## 9.8 Imports in SML

Imports are semantic, not necessarily source-level imports.

```sml
#Import
package: fastapi
symbols:
  - FastAPI
  - Depends
usage: backend.routes
resolution: compiler
```

A source import should not be hardcoded unless required.

Preferred:

```sml
#Capability
name: dependency_injection
provider: FastAPI
```

The compiler decides exact imports.

## 9.9 Constraints

Constraints narrow implementation choices.

```sml
#Constraint BackendStyle
architecture: layered
max_file_size_lines: 350
avoid:
  - broad_exception_handlers
  - unused_abstractions
  - handwritten_json_parsing
```

## 9.10 Policies

Policies define cross-cutting behavior.

```sml
#Policy ErrorHandling
default_validation_error: 422
unknown_error: propagate
broad_catch: forbidden
log_unhandled: true
```

## 9.11 Profiles

Profiles allow environment-specific behavior.

```sml
#Profile development
database_url: sqlite:///dev.db
debug: true

#Profile production
database_url: env:DATABASE_URL
debug: false
```

## 9.12 Includes

```sml
@include ./modules/auth.sml.md
@include ./modules/inventory.sml.md
```

Includes must be deterministic. Circular includes are forbidden.

## 9.13 Compiler Directives

```sml
@compiler version >=0.1.0
@target python.fastapi
@strict true
```

Directives control the compiler, not the generated application.

---

# 10. Formal SML Grammar Draft

The initial grammar should be implemented with a parser library such as Lark or equivalent.

## 10.1 Informal Syntax

SML is line-oriented, section-oriented, and indentation-sensitive for nested blocks.

## 10.2 EBNF-Style Draft

```ebnf
document        ::= directive* section+

directive       ::= "@" IDENT directive_args? NEWLINE
directive_args  ::= TEXT

section         ::= heading NEWLINE section_body?

heading         ::= "#" section_type section_name?
section_type    ::= IDENT
section_name    ::= TEXT

section_body    ::= body_line*
body_line       ::= key_value
                  | list_item
                  | nested_block
                  | comment
                  | blank

key_value       ::= IDENT ":" value NEWLINE
value           ::= scalar
                  | inline_list
                  | reference
                  | typed_value

scalar          ::= STRING | NUMBER | BOOLEAN | IDENT | TEXT
inline_list     ::= "[" value_list? "]"
value_list      ::= value ("," value)*

list_item       ::= INDENT "- " value NEWLINE

nested_block    ::= IDENT ":" NEWLINE INDENT body_line+ DEDENT

reference       ::= "$" IDENT ("." IDENT)*
typed_value     ::= IDENT "(" value_list? ")"

comment         ::= "//" TEXT NEWLINE
blank           ::= NEWLINE
```

## 10.3 Lark-Style Grammar Sketch

```lark
start: directive* section+

directive: "@" NAME /[^\n]*/ NEWLINE

section: heading NEWLINE body?
heading: "#" NAME section_name?
section_name: /[^\n]+/

body: body_line+
body_line: key_value
         | list_item
         | comment
         | NEWLINE

key_value: NAME ":" value? NEWLINE
list_item: INDENT "- " value NEWLINE
comment: "//" /[^\n]*/ NEWLINE

?value: inline_list
      | typed_value
      | reference
      | scalar

inline_list: "[" [value ("," value)*] "]"
typed_value: NAME "(" [value ("," value)*] ")"
reference: "$" NAME ("." NAME)*

scalar: ESCAPED_STRING
      | SIGNED_NUMBER
      | "true" -> true
      | "false" -> false
      | /[^\n#@]+/

%import common.CNAME -> NAME
%import common.ESCAPED_STRING
%import common.SIGNED_NUMBER
%import common.NEWLINE
%ignore /[ \t]+/
```

## 10.4 Parser Output

The parser should produce an SML AST:

```python
SMLDocument
  directives: list[Directive]
  sections: list[Section]
```

```python
Section
  type: str
  name: str | None
  fields: dict[str, Value]
  line_range: SourceRange
```

## 10.5 Strict Mode

Strict mode must reject:

- Unknown section types unless explicitly allowed by plugin.
- Duplicate IDs.
- Unresolved references.
- Invalid enum values.
- Ambiguous indentation.
- Mixed tabs/spaces.
- Compiler directives after sections.
- Cyclic includes.
- Reserved names used as custom symbols.

---

# 11. Semantic Intermediate Representation (SIR)

## 11.1 Purpose

SIR is the typed graph representation produced from SML. It is the compiler's true internal model.

SML is optimized for humans and AI agents. SIR is optimized for validation and compilation.

## 11.2 SIR Graph

SIR should be represented as a directed labeled graph:

```text
ProjectNode
  ├── StackNode
  ├── ModuleNode
  │     ├── DataModelNode
  │     ├── RouteNode
  │     └── ServiceNode
  ├── PolicyNode
  ├── ConstraintNode
  └── TestNode
```

## 11.3 Node Requirements

Every SIR node must have:

- Stable ID.
- Type.
- Name.
- Source range.
- Attributes.
- Dependencies.
- Provenance.
- Validation status.
- Optional latent fields.

Example:

```json
{
  "id": "route.ListProducts",
  "type": "RouteNode",
  "name": "ListProducts",
  "source_range": {"file": "project.sml.md", "start": 28, "end": 33},
  "attributes": {
    "method": "GET",
    "path": "/products",
    "auth": "required"
  },
  "dependencies": ["model.Product"],
  "provenance": ["user_requirement:inventory_crud"],
  "latent": {}
}
```

## 11.4 Node Taxonomy

### ProjectNode

Represents the entire project.

### StackNode

Represents selected frameworks and target packs.

### ModuleNode

Represents a bounded domain area.

### DataModelNode

Represents persistent or transport data structures.

### FieldNode

Represents a model field.

### RouteNode

Represents an API endpoint.

### ServiceNode

Represents business logic.

### RepositoryNode

Represents data access.

### ComponentNode

Represents frontend UI components.

### StateNode

Represents frontend or backend state.

### EventNode

Represents events, commands, or domain transitions.

### PolicyNode

Represents cross-cutting rules.

### ConstraintNode

Represents compiler restrictions.

### TestNode

Represents expected behavior.

### DeploymentNode

Represents infrastructure and environment.

## 11.5 Graph Invariants

The semantic graph must satisfy:

1. Every node ID is unique.
2. Every reference resolves to exactly one node.
3. Every route has method and path.
4. Every route response type resolves or is primitive.
5. Every model field has type.
6. Every service dependency is declared.
7. Every policy is known to the active target pack.
8. Every unresolved latent node has a bounded candidate pool.
9. Every resolved candidate has provenance.
10. The graph can be topologically sorted for codegen.

---

# 12. Latent Resolution Engine

## 12.1 Purpose

The Latent Resolution Engine is the most original part of the architecture.

It represents implementation ambiguity explicitly as bounded candidate pools, then collapses them into deterministic choices using constraints, documentation, dependency context, and tie-breaking rules.

## 12.2 Concept

A latent node is a semantic slot whose final implementation has not been selected.

Example:

```text
Import form for React state usage
```

Possible candidates:

```text
import React from "react"
import * as React from "react"
import { useState } from "react"
import React, { useState } from "react"
```

The system should not ask the model to freewrite the import. It should create a candidate pool and resolve based on:

- Required symbols.
- Framework version.
- Existing project style.
- Target pack rules.
- Documentation evidence.
- Linter constraints.
- Compiler policy.

## 12.3 Latent Node Data Structure

```python
class LatentChoice:
    id: str
    node_id: str
    dimension: str
    candidates: list[Candidate]
    constraints: list[ConstraintRef]
    selected: str | None
    confidence: float | None
    resolution_trace: list[ResolutionStep]
```

```python
class Candidate:
    id: str
    label: str
    payload: dict
    prior_weight: float
    score: float | None
    evidence: list[EvidenceRef]
    valid: bool | None
    rejection_reason: str | None
```

## 12.4 Candidate Pool Examples

### Import Style

```json
{
  "dimension": "python_import_style",
  "candidates": [
    {"id": "import_module", "payload": "import fastapi"},
    {"id": "from_import_symbol", "payload": "from fastapi import FastAPI"},
    {"id": "from_import_many", "payload": "from fastapi import FastAPI, Depends"}
  ]
}
```

### API Layering

```json
{
  "dimension": "backend_architecture",
  "candidates": [
    {"id": "single_file"},
    {"id": "router_service_repository"},
    {"id": "clean_architecture"}
  ]
}
```

### Error Handling

```json
{
  "dimension": "error_policy",
  "candidates": [
    {"id": "raise_http_exception"},
    {"id": "custom_domain_exception_mapper"},
    {"id": "broad_try_except"}
  ]
}
```

## 12.5 Resolution Inputs

Resolution should use:

- SIR graph constraints.
- SML policy sections.
- Retrieved documentation.
- Target pack defaults.
- Existing project style.
- Static analysis requirements.
- User preferences.
- Compiler version.
- Package versions.

## 12.6 Resolution Algorithm

```text
For each latent choice:
    1. Load candidate pool.
    2. Remove candidates violating hard constraints.
    3. Score remaining candidates using:
       - target pack preference
       - documentation match
       - dependency compatibility
       - project style consistency
       - simplicity score
       - testability score
    4. Apply confidence threshold.
    5. Apply deterministic tie-breaker.
    6. Record selected candidate.
    7. Record resolution trace.
```

## 12.7 Hard Constraints

Hard constraints eliminate candidates before scoring.

Examples:

- Candidate requires package not allowed by dependency policy.
- Candidate uses deprecated framework API.
- Candidate violates SML policy.
- Candidate cannot satisfy required symbol.
- Candidate conflicts with target language version.
- Candidate causes circular dependency.

## 12.8 Soft Scoring

Soft scoring ranks candidates.

Suggested scoring function:

```text
score =
  0.30 * documentation_match
+ 0.20 * target_pack_preference
+ 0.15 * project_style_consistency
+ 0.15 * simplicity
+ 0.10 * testability
+ 0.05 * maintainability
+ 0.05 * prior_weight
```

Weights must be configurable.

## 12.9 Deterministic Tie-Breaking

If two candidates score equally:

1. Prefer explicit user instruction.
2. Prefer SML constraint.
3. Prefer target pack default.
4. Prefer existing project style.
5. Prefer lower complexity.
6. Prefer lexicographically stable candidate ID.

Never choose randomly in deterministic mode.

## 12.10 Confidence Threshold

If no candidate reaches a minimum threshold, the system should:

- Return a validation error.
- Ask the agent to refine SML.
- Request user clarification only if absolutely necessary.
- Never silently invent a candidate outside the pool.

## 12.11 Provenance

Every resolution must record why it happened.

Example:

```json
{
  "choice": "auth.jwt_library",
  "selected": "python_jose",
  "because": [
    "SML specified JWT auth",
    "FastAPI target pack supports python-jose",
    "Dependency policy allows python-jose",
    "Candidate has official usage examples in knowledge pack"
  ]
}
```

---

# 13. Compiler Architecture

## 13.1 Compiler Stages

```text
Input SML
  ↓
Include expansion
  ↓
Lexing
  ↓
Parsing
  ↓
SML AST
  ↓
Semantic analysis
  ↓
SIR graph
  ↓
Validation
  ↓
Latent resolution
  ↓
Resolved IR
  ↓
Optimization passes
  ↓
Target backend codegen
  ↓
Source tree
  ↓
Formatting
  ↓
Static analysis
  ↓
Tests
  ↓
Build manifest
```

## 13.2 Compiler Frontend

Responsible for:

- Reading SML files.
- Expanding includes.
- Lexing.
- Parsing.
- Producing SML AST.
- Reporting syntax errors.
- Preserving source locations.

## 13.3 Semantic Analyzer

Responsible for:

- Section type validation.
- Field validation.
- Reference resolution.
- Type checking.
- Dependency graph construction.
- Policy interpretation.
- Constraint collection.
- Latent node creation.

## 13.4 Resolution Pass

Responsible for:

- Candidate pool creation.
- Candidate filtering.
- Candidate scoring.
- Candidate collapse.
- Provenance recording.

## 13.5 Optimization Passes

Possible IR optimization passes:

- Remove unused services.
- Merge duplicate DTOs.
- Normalize route prefixes.
- Normalize imports.
- Split oversized files.
- Eliminate unreachable tests.
- Deduplicate validation schemas.
- Apply naming conventions.

Optimization must not change semantics.

## 13.6 Backend Codegen

Responsible for:

- File tree generation.
- Source AST generation.
- Import generation.
- Function/class generation.
- Config generation.
- Test generation.
- README generation.
- Dependency manifest generation.

## 13.7 Build Manifest

Every compile should produce:

```json
{
  "compiler_version": "0.1.0",
  "sml_hash": "...",
  "sir_hash": "...",
  "resolved_ir_hash": "...",
  "target_pack": "python.fastapi",
  "generated_files": [],
  "resolution_trace": [],
  "validation_results": [],
  "timestamp": "..."
}
```

This enables reproducibility and debugging.

---

# 14. Agent Architecture Using PydanticAI

## 14.1 Why PydanticAI

PydanticAI fits the project because the architecture requires structured outputs, typed validation, retry policies, tool usage, and potentially graph-based workflows.

The system should use PydanticAI to orchestrate AI agents, but should not let agents bypass SML or compiler validation.

## 14.2 Agent Responsibilities

### Intent Agent

Input:

```text
Natural-language user request
```

Output:

```python
ProjectRequirements
```

Responsibilities:

- Extract project type.
- Extract features.
- Extract constraints.
- Identify ambiguities.
- Avoid making hidden implementation decisions.

### Research Agent

Input:

```python
ProjectRequirements
StackHints
```

Output:

```python
ImplementationKnowledgePack
```

Responsibilities:

- Retrieve relevant official documentation.
- Identify recommended patterns.
- Identify deprecated APIs.
- Identify package version constraints.
- Provide evidence references.

### Architecture Agent

Input:

```python
ProjectRequirements
ImplementationKnowledgePack
```

Output:

```python
ArchitecturePlan
```

Responsibilities:

- Choose module boundaries.
- Choose high-level architecture.
- Identify required data models.
- Identify services, routes, components, policies, and tests.

### SML Generator Agent

Input:

```python
ArchitecturePlan
```

Output:

```python
SMLDocumentDraft
```

Responsibilities:

- Emit SML.
- Avoid emitting source code.
- Preserve user intent.
- Mark uncertainty as latent or unresolved.

### Resolution Agent

Input:

```python
SIRGraph
LatentChoices
KnowledgePack
```

Output:

```python
ResolutionPlan
```

Responsibilities:

- Assist candidate scoring.
- Provide evidence for candidate choices.
- Respect deterministic collapse rules.
- Never invent unregistered candidates without flagging.

### Compiler Agent

This should be minimal. Ideally, compilation is deterministic code, not model generation.

Agent role:

- Explain compiler errors.
- Suggest SML edits.
- Assist with target pack creation.

### Repair Agent

Input:

```python
ValidationFailure
SourceMap
SIRGraph
```

Output:

```python
SMLPatch
```

Responsibilities:

- Map build/test failures back to SML or IR.
- Suggest semantic patches.
- Avoid blind source mutation.
- Preserve minimal diffs.

## 14.3 Agent Workflow Graph

```mermaid
flowchart LR
    U[User] --> IA[Intent Agent]
    IA --> RQ[Requirements Model]
    RQ --> RA[Research Agent]
    RQ --> AA[Architecture Agent]
    RA --> AA
    AA --> SG[SML Generator]
    SG --> CP[Compiler Pipeline]
    CP --> VR[Validation Results]
    VR -->|pass| Done[Generated Project]
    VR -->|fail| Repair[Repair Agent]
    Repair --> SG
```

## 14.4 Agent Contract Principle

Every agent must return a Pydantic model, not freeform text, except where explicitly generating SML text.

Even SML output should be wrapped:

```python
class SMLDocumentDraft(BaseModel):
    text: str
    assumptions: list[str]
    unresolved_questions: list[str]
    provenance: list[EvidenceRef]
```

## 14.5 Retry Policy

Agent retries should be used only for structured output failures or validation failures.

Retries must not produce uncontrolled architectural drift.

---

# 15. RAG and Documentation Intelligence Layer

## 15.1 Purpose

The RAG layer constrains implementation decisions using current documentation and local project conventions.

It should prevent:

- Stale package usage.
- Hallucinated imports.
- Deprecated APIs.
- Wrong initialization patterns.
- Incorrect config options.

## 15.2 Document Sources

Priority order:

1. Official framework documentation.
2. Official package documentation.
3. Source repository README.
4. Type stubs / generated docs.
5. Local project conventions.
6. Trusted internal style guide.
7. Community examples only when official docs are insufficient.

## 15.3 Knowledge Pack

The Research Agent should produce a knowledge pack:

```python
ImplementationKnowledgePack:
    target_stack: list[str]
    docs: list[DocSnippet]
    package_versions: list[PackageVersion]
    recommended_patterns: list[Pattern]
    deprecated_patterns: list[Pattern]
    examples: list[CodeExample]
    constraints: list[Constraint]
```

## 15.4 Retrieval Strategy

Use hybrid retrieval:

- Keyword search for package symbols.
- Vector search for semantic documentation.
- Version-aware filtering.
- Target-pack-specific queries.
- Local codebase retrieval when modifying existing projects.

## 15.5 Provenance Requirements

Every documentation-derived decision should cite:

- Source title.
- URL or local file.
- Version/date if available.
- Retrieved text hash.
- Retrieval query.
- Associated SIR node.

## 15.6 Caching

Knowledge packs should be cached by:

```text
package name
package version
target pack
retrieval date
doc source hash
```

## 15.7 Dependency Registry

The project should maintain an internal registry:

```yaml
packages:
  fastapi:
    supported_targets: [python.fastapi]
    docs_url: https://fastapi.tiangolo.com/
    import_symbols:
      - FastAPI
      - APIRouter
      - Depends
      - HTTPException
  pydantic:
    supported_targets: [python]
    import_symbols:
      - BaseModel
      - Field
```

---

# 16. Target Language Strategy

## 16.1 Piggybacking Principle

The system should compile into mature languages rather than executing SML directly.

SML is a specification format, not a runtime.

## 16.2 MVP Targets

Recommended MVP targets:

```text
python.fastapi
python.pydantic
python.pytest
```

Optional frontend target:

```text
typescript.react
```

## 16.3 Later Targets

Potential target packs:

```text
typescript.node.express
typescript.nextjs
typescript.react
typescript.svelte
python.django
python.flask
rust.axum
go.gin
```

## 16.4 Target Pack Interface

Every target pack must implement:

```python
class TargetPack:
    id: str
    supported_nodes: set[str]
    default_policies: dict
    candidate_providers: list[CandidateProvider]
    validators: list[Validator]
    codegen_passes: list[CodegenPass]
    formatters: list[Formatter]
    test_generators: list[TestGenerator]
```

## 16.5 Target Pack Responsibilities

- Provide candidate pools.
- Translate resolved IR nodes into AST/source.
- Enforce target-specific constraints.
- Generate dependency manifests.
- Generate tests.
- Provide lint/type-check commands.
- Provide examples and golden tests.

---

# 17. Python Backend Target

## 17.1 MVP Backend Stack

Recommended MVP stack:

```text
Python 3.11+
FastAPI
Pydantic v2
SQLAlchemy or SQLModel
Alembic
pytest
ruff
mypy or pyright
uv or pip-tools
```

The initial version can simplify persistence by supporting either:

- In-memory repository.
- SQLite.
- PostgreSQL.

## 17.2 Generated File Layout

```text
generated_app/
  pyproject.toml
  README.md
  .env.example
  app/
    __init__.py
    main.py
    core/
      config.py
      errors.py
      security.py
    api/
      __init__.py
      routes/
        __init__.py
        inventory.py
    models/
      __init__.py
      product.py
    schemas/
      __init__.py
      product.py
    services/
      __init__.py
      inventory_service.py
    repositories/
      __init__.py
      product_repository.py
    db/
      __init__.py
      session.py
      base.py
  tests/
    test_inventory.py
```

## 17.3 Python AST Emission Strategy

The compiler should prefer AST construction for complex Python files and text templates only for simple configuration files.

Python code generation approaches:

1. Build Python `ast` nodes.
2. Unparse with `ast.unparse`.
3. Format with `ruff format` or Black.
4. Run static checks.

Fallback:

- Use structured templates for boilerplate files.
- Never allow arbitrary LLM-written source in deterministic codegen mode.

## 17.4 Error Handling Policy

Broad exception handlers are forbidden by default.

Allowed:

```python
raise HTTPException(status_code=404, detail="Product not found")
```

Allowed when explicitly configured:

```python
try:
    ...
except SpecificKnownError as exc:
    ...
```

Forbidden by default:

```python
try:
    ...
except Exception:
    ...
```

## 17.5 Import Generation

Imports should be generated from symbol usage and target pack rules.

Do not let the LLM write imports directly.

Import generation algorithm:

```text
1. Collect required symbols from resolved IR.
2. Map symbols to package import paths via registry.
3. Group standard-library imports.
4. Group third-party imports.
5. Group local imports.
6. Sort deterministically.
7. Emit only used imports.
8. Run linter to confirm no unused imports.
```

---

# 18. TypeScript / Node.js Integration

## 18.1 Role of Node.js

Node.js can serve several roles:

- CLI distribution layer.
- TypeScript frontend target.
- Developer tooling.
- Language server integration.
- Web IDE integration.
- Parser frontend if a TypeScript parser implementation is preferred.

The project should not depend on Node.js for Python codegen unless the selected implementation team prefers a TypeScript compiler core.

## 18.2 Recommended Node Package Layout

```text
packages/
  cli/
    package.json
    src/
      index.ts
      commands/
        compile.ts
        validate.ts
        inspect.ts
  sml-parser/
    src/
      lexer.ts
      parser.ts
      ast.ts
  vscode-extension/
    package.json
    src/
      extension.ts
```

## 18.3 ESM Strategy

Modern Node.js tooling should prefer ESM for new TypeScript packages unless project constraints require CommonJS.

Example `package.json`:

```json
{
  "type": "module",
  "bin": {
    "smlc": "./dist/index.js"
  },
  "scripts": {
    "build": "tsc",
    "test": "vitest",
    "lint": "eslint ."
  }
}
```

## 18.4 CLI Commands

```bash
smlc init
smlc validate project.sml.md
smlc compile project.sml.md --target python.fastapi --out ./generated
smlc inspect project.sml.md --graph
smlc explain route.ListProducts
smlc benchmark ./examples
```

## 18.5 TypeScript Target Pack

A TypeScript target pack should support:

- React components.
- API clients.
- Node.js server routes.
- Type-safe DTOs.
- Zod schemas or TypeScript interfaces.
- ESLint/Prettier formatting.

---

# 19. Frontend Target Packs

## 19.1 Purpose

Frontend target packs compile SML UI components into frontend code.

Initial frontend targets may include:

```text
typescript.react
typescript.svelte
```

## 19.2 Component SML Example

```sml
#Component ProductList
framework: React
props:
  products: Product[]
state:
  search: string
actions:
  - filter_products
renders:
  - table
  - empty_state
  - loading_state
data_source: GET /products
```

## 19.3 Generated React Structure

```text
src/
  components/
    ProductList.tsx
  api/
    products.ts
  types/
    product.ts
  pages/
    ProductsPage.tsx
```

## 19.4 Frontend Import Resolution Example

Latent import choice:

```json
{
  "dimension": "react_import_style",
  "required_symbols": ["useState", "useEffect"],
  "candidates": [
    "import React from 'react'",
    "import * as React from 'react'",
    "import { useState, useEffect } from 'react'",
    "import React, { useState, useEffect } from 'react'"
  ]
}
```

Resolution should depend on:

- JSX transform settings.
- React version.
- ESLint rules.
- Existing project style.
- Target pack default.

---

# 20. Validation System

Validation occurs at multiple layers.

## 20.1 Syntax Validation

Ensures SML is parseable.

## 20.2 Schema Validation

Ensures parsed sections conform to expected Pydantic models.

## 20.3 Semantic Validation

Ensures references, types, and dependencies are valid.

## 20.4 Constraint Validation

Ensures policies and constraints are enforceable.

## 20.5 Resolution Validation

Ensures every latent node is collapsed or explicitly deferred.

## 20.6 Codegen Validation

Ensures generated files can be produced without missing symbols.

## 20.7 Static Validation

Runs linters, formatters, and type checkers.

## 20.8 Behavioral Validation

Runs generated tests.

## 20.9 Validation Error Format

```json
{
  "code": "UNRESOLVED_REFERENCE",
  "message": "Route CreateProduct references ProductCreate, but no schema exists.",
  "severity": "error",
  "source_range": {
    "file": "project.sml.md",
    "start": 42,
    "end": 42
  },
  "node_id": "route.CreateProduct",
  "suggested_fix": "Define #DataModel ProductCreate or change body type."
}
```

---

# 21. Static Analysis and Repair Loop

## 21.1 Principle

Repair should happen at the semantic layer whenever possible.

Wrong:

```text
Generated code fails → AI edits source directly.
```

Correct:

```text
Generated code fails → map failure to IR/SML → patch SML or target pack → regenerate.
```

## 21.2 Repair Flow

```text
Compile
  ↓
Run static checks
  ↓
Capture failure
  ↓
Map to generated file and source map
  ↓
Map to IR node
  ↓
Determine if issue is:
     - SML issue
     - target pack bug
     - dependency issue
     - compiler bug
  ↓
Patch correct layer
  ↓
Regenerate
```

## 21.3 Source Maps

Every generated source region should map back to:

- SML section.
- SIR node.
- Resolution choice.
- Target pack generator.

Example:

```json
{
  "generated_file": "app/api/routes/inventory.py",
  "generated_lines": [12, 24],
  "sir_node": "route.ListProducts",
  "sml_source": "project.sml.md:28-33",
  "generator": "python.fastapi.route_generator"
}
```

## 21.4 Repair Agent Output

```python
class SemanticPatch(BaseModel):
    target: Literal["sml", "sir", "target_pack", "dependency"]
    patch: str
    rationale: str
    expected_effect: str
```

---

# 22. Deterministic Regeneration and Diff Stability

## 22.1 Requirement

Given identical inputs, compiler version, target pack version, dependency registry, and resolution policy, output must be identical.

## 22.2 Determinism Inputs

- SML text.
- Include files.
- Compiler version.
- Target pack version.
- Dependency lock.
- Resolution policy.
- Knowledge pack hash.
- Environment profile.

## 22.3 Diff Stability Rules

- Stable file ordering.
- Stable import ordering.
- Stable class/function ordering.
- Stable naming.
- Stable formatting.
- Stable generated comments.
- Stable IDs.
- Stable tie-breakers.

## 22.4 Incremental Regeneration

When a section changes, only affected files should regenerate where possible.

Example:

Changing `Product.quantity` should affect:

- Product model.
- Product schema.
- Tests referencing Product.
- Possibly database migration.

It should not rewrite:

- Auth module.
- Unrelated routes.
- Project README unless schema summary changes.

---

# 23. Repository Architecture

## 23.1 Recommended Monorepo

```text
semantic-software-markup/
  README.md
  LICENSE
  CONTRIBUTING.md
  ROADMAP.md
  pyproject.toml
  package.json
  docs/
    architecture-spec.md
    language-reference.md
    compiler-reference.md
    agent-reference.md
  examples/
    todo-api/
      project.sml.md
      expected/
    inventory-system/
      project.sml.md
      expected/
  sml/
    grammar/
      sml.lark
    examples/
    schemas/
  compiler/
    __init__.py
    frontend/
      lexer.py
      parser.py
      sml_ast.py
    semantic/
      analyzer.py
      graph.py
      validators.py
    resolver/
      latent.py
      candidates.py
      scoring.py
      collapse.py
    ir/
      nodes.py
      resolved.py
      optimizer.py
    backends/
      python_fastapi/
        target.py
        generators/
        validators/
      typescript_react/
        target.py
        generators/
    codegen/
      python_ast.py
      text_templates.py
      source_map.py
    validation/
      errors.py
      runner.py
      static_analysis.py
  agents/
    __init__.py
    intent_agent.py
    research_agent.py
    architecture_agent.py
    sml_agent.py
    repair_agent.py
    schemas.py
  rag/
    ingestion.py
    retriever.py
    knowledge_pack.py
    registry.py
  cli/
    main.py
    commands/
      init.py
      validate.py
      compile.py
      inspect.py
      benchmark.py
  tests/
    unit/
    integration/
    golden/
  packages/
    cli-node/
    vscode-extension/
```

## 23.2 Module Boundaries

### `sml/`

Language-level grammar and examples.

### `compiler/frontend/`

Parsing and AST creation.

### `compiler/semantic/`

Semantic graph and validation.

### `compiler/resolver/`

Latent resolution engine.

### `compiler/backends/`

Target packs.

### `agents/`

PydanticAI orchestration.

### `rag/`

Documentation ingestion and retrieval.

### `cli/`

Developer interface.

### `tests/golden/`

Stable output tests.

---

# 24. Runtime Services and APIs

## 24.1 Local CLI First

The MVP should start as a local CLI.

## 24.2 Optional API Server

Later, expose a service:

```http
POST /v1/intent
POST /v1/sml/generate
POST /v1/sml/validate
POST /v1/compile
POST /v1/inspect
POST /v1/repair
```

## 24.3 Compile API

Request:

```json
{
  "sml": "...",
  "target": "python.fastapi",
  "mode": "deterministic",
  "profile": "development"
}
```

Response:

```json
{
  "success": true,
  "files": [
    {
      "path": "app/main.py",
      "content": "..."
    }
  ],
  "manifest": {},
  "validation": {}
}
```

## 24.4 Inspect API

Returns:

- SML AST.
- SIR graph.
- Latent choices.
- Resolution trace.
- Generated file map.

---

# 25. CLI Specification

## 25.1 `smlc init`

Creates starter project.

```bash
smlc init inventory-system
```

Output:

```text
inventory-system/
  project.sml.md
  sml.lock
```

## 25.2 `smlc validate`

```bash
smlc validate project.sml.md
```

Checks syntax, schema, semantics, and constraints.

## 25.3 `smlc compile`

```bash
smlc compile project.sml.md --target python.fastapi --out ./generated
```

Compiles SML into source tree.

## 25.4 `smlc inspect`

```bash
smlc inspect project.sml.md --sir
smlc inspect project.sml.md --latent
smlc inspect project.sml.md --source-map
```

## 25.5 `smlc explain`

```bash
smlc explain route.CreateProduct
```

Explains why generated code exists.

## 25.6 `smlc benchmark`

```bash
smlc benchmark ./examples
```

Runs deterministic benchmark suite.

---

# 26. Pydantic Data Models

The following models are conceptual and should be refined during implementation.

## 26.1 Source Range

```python
from pydantic import BaseModel, Field
from typing import Literal, Any

class SourceRange(BaseModel):
    file: str
    start_line: int
    end_line: int
    start_col: int | None = None
    end_col: int | None = None
```

## 26.2 SML Document

```python
class Directive(BaseModel):
    name: str
    args: str | None = None
    source_range: SourceRange

class SMLSection(BaseModel):
    section_type: str
    name: str | None = None
    fields: dict[str, Any]
    source_range: SourceRange

class SMLDocument(BaseModel):
    directives: list[Directive]
    sections: list[SMLSection]
```

## 26.3 Requirements

```python
class FeatureRequirement(BaseModel):
    name: str
    description: str
    priority: Literal["must", "should", "could"] = "must"

class ProjectRequirements(BaseModel):
    project_name: str
    description: str
    domain: str | None = None
    features: list[FeatureRequirement]
    stack_hints: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
```

## 26.4 SIR Node

```python
class EvidenceRef(BaseModel):
    source_type: Literal["user", "sml", "docs", "compiler_default", "target_pack"]
    source_id: str
    summary: str

class SIRNode(BaseModel):
    id: str
    node_type: str
    name: str
    attributes: dict[str, Any]
    dependencies: list[str] = Field(default_factory=list)
    source_range: SourceRange | None = None
    provenance: list[EvidenceRef] = Field(default_factory=list)
```

## 26.5 Latent Choice

```python
class Candidate(BaseModel):
    id: str
    label: str
    payload: dict[str, Any]
    prior_weight: float = 0.0
    score: float | None = None
    valid: bool | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    rejection_reason: str | None = None

class LatentChoice(BaseModel):
    id: str
    node_id: str
    dimension: str
    candidates: list[Candidate]
    selected_candidate_id: str | None = None
    confidence: float | None = None
    resolution_trace: list[str] = Field(default_factory=list)
```

## 26.6 Compile Result

```python
class GeneratedFile(BaseModel):
    path: str
    content: str
    source_map: dict[str, Any] = Field(default_factory=dict)

class CompileResult(BaseModel):
    success: bool
    files: list[GeneratedFile]
    manifest: dict[str, Any]
    errors: list[dict[str, Any]] = Field(default_factory=list)
```

---

# 27. Algorithms

## 27.1 Intent Extraction Algorithm

```text
Input: user prompt

1. Normalize prompt.
2. Extract project type.
3. Extract explicit features.
4. Extract explicit constraints.
5. Extract stack preferences.
6. Identify missing but necessary requirements.
7. Produce ProjectRequirements.
8. Validate with Pydantic.
9. If validation fails, retry structured output.
10. Do not choose implementation details unless explicitly requested.
```

## 27.2 SML Generation Algorithm

```text
Input: ProjectRequirements, ArchitecturePlan

1. Create #Project section.
2. Create #Stack section from explicit or default stack.
3. Create one #Module per domain boundary.
4. Create #DataModel sections.
5. Create #Route sections.
6. Create #Service sections.
7. Create #Policy sections.
8. Create #Constraint sections.
9. Create #Test sections.
10. Mark unresolved choices as latent.
11. Return SMLDocumentDraft.
```

## 27.3 Semantic Analysis Algorithm

```text
Input: SML AST

1. Validate section types.
2. Validate section field schemas.
3. Assign stable node IDs.
4. Build symbol table.
5. Resolve references.
6. Build dependency graph.
7. Detect cycles.
8. Infer missing derived nodes.
9. Create latent choices for unresolved implementation dimensions.
10. Return SIR graph.
```

## 27.4 Latent Resolution Algorithm

```text
Input: SIR graph, knowledge pack, target pack

1. For each target pack, register candidate providers.
2. For each SIR node, discover latent dimensions.
3. Generate candidate pool.
4. Apply hard constraints.
5. Score candidates.
6. Select winner with deterministic tie-breaker.
7. Record resolution trace.
8. Update node with resolved implementation details.
9. Validate all latent choices are resolved or deferred.
10. Return resolved IR.
```

## 27.5 Codegen Algorithm

```text
Input: resolved IR, target pack

1. Topologically sort graph.
2. Plan output file tree.
3. Generate source AST or templates for each file.
4. Generate imports from symbol usage.
5. Generate tests from TestNodes.
6. Generate dependency manifest.
7. Generate README and .env.example.
8. Format output.
9. Write source map.
10. Return generated file set.
```

## 27.6 Repair Algorithm

```text
Input: validation failure

1. Parse error message.
2. Locate generated file and line.
3. Use source map to find SIR node.
4. Determine fault layer:
   a. SML defect
   b. Resolution defect
   c. Target pack defect
   d. Dependency defect
   e. Environment defect
5. Generate minimal semantic patch.
6. Recompile.
7. Confirm error resolved.
8. Preserve unrelated output.
```

---

# 28. Security, Sandboxing, and Supply Chain Controls

## 28.1 Threat Model

The system may ingest user prompts, documentation, local code, package metadata, and generated code. Risks include:

- Prompt injection from documentation.
- Malicious package recommendations.
- Secret leakage.
- Unsafe generated code.
- Insecure dependency versions.
- Arbitrary command execution during validation.
- Supply-chain compromise.
- Over-permissive generated APIs.

## 28.2 Controls

### Documentation Sanitization

Retrieved documentation should be treated as data, not instructions.

### Tool Allowlist

Agents can only call registered tools.

### Dependency Policy

The compiler should enforce approved packages.

```yaml
dependency_policy:
  allow:
    - fastapi
    - pydantic
    - sqlalchemy
  deny:
    - unknown-package
  require_version_pin: true
```

### Secret Handling

SML must not store secrets directly.

Allowed:

```sml
database_url: env:DATABASE_URL
```

Forbidden:

```sml
database_url: postgresql://user:password@host/db
```

### Sandbox Execution

Generated code should be tested in a sandboxed environment.

### No Arbitrary Shell

Agents should not execute arbitrary shell commands. The validation runner should execute a fixed set of allowed commands.

---

# 29. Observability and Provenance

## 29.1 Event Log

Every compile run should produce structured events:

```json
{
  "event": "latent_choice_resolved",
  "node_id": "route.ListProducts",
  "choice_id": "python_import_style",
  "selected": "from_import_symbol",
  "timestamp": "..."
}
```

## 29.2 Provenance Graph

The system should be able to answer:

- Why does this file exist?
- Why does this import exist?
- Why was this package selected?
- Which SML line generated this route?
- Which documentation snippet supported this decision?
- Which agent produced this section?
- Which validation rule rejected an alternative candidate?

## 29.3 Explainability Command

```bash
smlc explain app/api/routes/inventory.py:12
```

Expected output:

```text
Generated from route.ListProducts
SML source: project.sml.md:28-33
Target pack: python.fastapi
Import selected because FastAPI route generator required APIRouter.
```

---

# 30. Testing Strategy

## 30.1 Unit Tests

- SML lexer.
- SML parser.
- AST model validation.
- Semantic analyzer.
- Reference resolver.
- Candidate pool generation.
- Candidate scoring.
- Tie-breakers.
- Import generator.

## 30.2 Golden Tests

Golden tests compare generated output against expected files.

Example:

```text
examples/todo-api/project.sml.md
examples/todo-api/expected/app/main.py
```

Test:

```text
compile project.sml.md
compare generated output to expected output
```

## 30.3 Property Tests

Potential properties:

- Deterministic compile output.
- No duplicate node IDs.
- No unresolved references after validation.
- Import generation emits no unused imports.
- Equivalent SML formatting produces same SIR.

## 30.4 Integration Tests

- Compile Todo API.
- Compile Inventory API.
- Compile Auth API.
- Compile React component.
- Run generated app tests.

## 30.5 Regression Tests

Every discovered hallucination, drift, or invalid output should become a regression fixture.

---

# 31. Evaluation Benchmarks

## 31.1 Prompt Equivalence Benchmark

Feed equivalent prompts:

```text
Build a todo API.
Create a FastAPI todo backend.
Make an API for todo items using Python.
```

Expected:

- Similar or identical SML.
- Same architecture.
- Stable codegen.

## 31.2 Code Drift Benchmark

Modify one requirement and measure affected files.

Metric:

```text
changed_files / total_files
```

Lower is better when the requirement change is local.

## 31.3 Bloat Index

Measure:

- Lines of code per semantic node.
- Number of helper functions per feature.
- Exception handler count.
- Unused abstractions.
- Cyclomatic complexity.

## 31.4 Hallucinated Import Rate

Run generated code through import validation.

Metric:

```text
missing_imports / total_imports
```

## 31.5 Build Pass Rate

```text
successful_builds / total_benchmark_cases
```

## 31.6 Test Pass Rate

```text
passing_generated_tests / total_generated_tests
```

## 31.7 Determinism Score

Compile same SML N times.

```text
identical_outputs / N
```

Expected target:

```text
100%
```

## 31.8 Direct LLM Baseline

Compare against direct LLM code generation.

Metrics:

- Build pass rate.
- Drift.
- Bloat.
- Import errors.
- Diff stability.
- Human review score.

---

# 32. MVP Scope

## 32.1 MVP Objective

Build a working compiler that converts constrained SML into a small FastAPI backend.

## 32.2 MVP Features

MVP should support:

- `#Project`
- `#Stack`
- `#Module`
- `#DataModel`
- `#Route`
- `#Policy`
- `#Test`
- Basic parser.
- Pydantic validation.
- SIR graph.
- Basic latent resolution for imports and architecture style.
- Python FastAPI target.
- Deterministic codegen.
- Generated pytest tests.
- CLI commands:
  - `validate`
  - `compile`
  - `inspect`
- Golden tests.

## 32.3 MVP Exclusions

Do not include in MVP:

- Full frontend generation.
- Complex auth beyond simple placeholder/JWT scaffold.
- Multi-language backends.
- Visual IDE.
- Cloud service.
- Full repair agent autonomy.
- Production deployment automation.

## 32.4 MVP Acceptance Criteria

The MVP is successful when:

1. A user writes `project.sml.md`.
2. `smlc validate` passes.
3. `smlc compile` generates a FastAPI project.
4. Generated project installs successfully.
5. Tests pass.
6. Re-running compile produces identical output.
7. Equivalent prompts produce stable SML after normalization.
8. No hallucinated imports occur in benchmark examples.

---

# 33. Development Roadmap

## Phase 0: Specification

Deliverables:

- Architecture spec.
- SML language draft.
- SIR schema draft.
- Compiler pipeline design.
- MVP target definition.

## Phase 1: Parser Prototype

Deliverables:

- Grammar.
- Parser.
- SML AST.
- Syntax error reporting.
- Example SML files.

## Phase 2: Semantic Analyzer

Deliverables:

- Pydantic schemas.
- Symbol table.
- Reference resolver.
- SIR graph builder.
- Semantic validation errors.

## Phase 3: Basic Compiler

Deliverables:

- Python FastAPI target pack.
- File generator.
- Import generator.
- Source map.
- Deterministic output.

## Phase 4: Latent Resolution Engine

Deliverables:

- Candidate model.
- Candidate providers.
- Constraint filtering.
- Scoring.
- Deterministic tie-breaking.
- Resolution trace.

## Phase 5: Validation Toolchain

Deliverables:

- Formatter runner.
- Linter runner.
- Type checker runner.
- Test runner.
- Validation report.

## Phase 6: PydanticAI Agent Layer

Deliverables:

- Intent Agent.
- Research Agent.
- Architecture Agent.
- SML Generator Agent.
- Repair Agent prototype.
- Structured output schemas.

## Phase 7: RAG Layer

Deliverables:

- Documentation ingestion.
- Vector index.
- Knowledge pack schema.
- Package registry.
- Provenance references.

## Phase 8: Benchmarks

Deliverables:

- Prompt equivalence benchmark.
- Golden output tests.
- Code drift benchmark.
- Build pass benchmark.
- Direct LLM baseline comparison.

## Phase 9: Frontend Target

Deliverables:

- React or Svelte target pack.
- Component SML.
- API client generation.
- Frontend test generation.

## Phase 10: Open-Source Release

Deliverables:

- Public repository.
- Documentation site.
- Examples.
- Contribution guide.
- Roadmap.
- Issue templates.

---

# 34. Open-Source Governance

## 34.1 License

Recommended:

- Apache-2.0 for permissive commercial use with patent protection.
- MIT if simplicity is preferred.

## 34.2 Contribution Model

Require:

- Design proposals for grammar changes.
- Golden tests for codegen changes.
- Benchmark updates for compiler changes.
- No target pack changes without validation fixtures.

## 34.3 RFC Process

Major changes should use RFCs:

```text
rfcs/
  0001-sml-section-model.md
  0002-latent-resolution-engine.md
  0003-python-fastapi-target.md
```

## 34.4 Versioning

Use semantic versioning:

```text
SML language version
Compiler version
Target pack version
Knowledge pack version
```

Breaking changes to SML grammar require major version increment.

---

# 35. Risks and Mitigations

## Risk 1: SML Becomes Too Vague

Mitigation:

- Strict grammar.
- Pydantic schemas.
- Mandatory validation.
- Golden tests.

## Risk 2: SML Becomes Too Verbose

Mitigation:

- Sensible defaults.
- Includes.
- Profiles.
- Macros later.
- AI-assisted SML generation.

## Risk 3: Compiler Complexity Grows Too Fast

Mitigation:

- Start with one target pack.
- Restrict MVP.
- Avoid full language runtime.
- Add capabilities incrementally.

## Risk 4: Agents Reintroduce Drift

Mitigation:

- Agents output structured models.
- Agents cannot bypass compiler.
- Semantic patches only.
- Deterministic codegen.

## Risk 5: RAG Uses Stale Docs

Mitigation:

- Versioned knowledge packs.
- Official docs priority.
- Package lock integration.
- Retrieval timestamp and doc hash.

## Risk 6: Codegen Templates Become Fragile

Mitigation:

- Prefer AST for language constructs.
- Use templates only for static files.
- Use linters and formatters.
- Add regression tests.

## Risk 7: Open-Source Contributors Add Inconsistent Target Packs

Mitigation:

- Target pack interface.
- Required golden tests.
- Required benchmark metrics.
- RFC process.

---

# 36. Example End-to-End Flow

## 36.1 User Request

```text
Build a simple inventory API with products, suppliers, JWT auth, and PostgreSQL.
```

## 36.2 Requirements Model

```json
{
  "project_name": "Inventory API",
  "features": [
    {"name": "Products CRUD", "priority": "must"},
    {"name": "Suppliers CRUD", "priority": "must"},
    {"name": "JWT Auth", "priority": "must"},
    {"name": "PostgreSQL persistence", "priority": "must"}
  ],
  "stack_hints": {
    "backend": "FastAPI",
    "database": "PostgreSQL"
  }
}
```

## 36.3 SML

```sml
#Project
name: Inventory API
description: API for products, suppliers, and stock management.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#Module Products
purpose: Manage product records.

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#Route ListProducts
method: GET
path: /products
auth: required
returns: Product[]

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Policy ErrorHandling
not_found: 404
validation_error: 422
broad_catch: forbidden
```

## 36.4 Latent Choices

```json
[
  {
    "dimension": "backend_architecture",
    "candidates": ["single_file", "router_service_repository"]
  },
  {
    "dimension": "uuid_strategy",
    "candidates": ["python_uuid", "database_uuid"]
  },
  {
    "dimension": "auth_library",
    "candidates": ["python_jose", "pyjwt"]
  }
]
```

## 36.5 Resolved IR

```json
{
  "backend_architecture": "router_service_repository",
  "uuid_strategy": "python_uuid",
  "auth_library": "python_jose"
}
```

## 36.6 Generated Output

```text
app/main.py
app/api/routes/products.py
app/models/product.py
app/schemas/product.py
app/services/product_service.py
app/repositories/product_repository.py
tests/test_products.py
pyproject.toml
README.md
```

---

# 37. Handoff Prompt for Another AI Developer

Use the following prompt to transfer context to another AI system:

```text
You are taking over development of an open-source compiler-style project called Semantic Software Markup / SML Compiler.

The project goal is to solve instability in AI-generated code by separating intent understanding from deterministic code generation.

Do not treat this as a normal prompt-to-code generator. The architecture is:

Natural-language request → PydanticAI agents → structured requirements → documentation RAG → Software Markup Language → SML parser → Semantic Intermediate Representation → Latent Resolution Engine → deterministic IR → target compiler backend → generated code → static analysis/tests → semantic repair.

The most important design principle is: AI understands intent; the compiler emits code. Generated source code is a build artifact. SML is the source of truth.

The project does not create a new runtime language. It piggybacks on mature ecosystems such as Python, TypeScript/Node.js, PydanticAI, Pydantic, Python AST, parser libraries, linters, formatters, and test runners.

The Software Markup Language is a human-readable markup format inspired by Markdown, but stricter. It describes software architecture, modules, data models, routes, services, components, policies, constraints, tests, and deployment.

The Latent Resolution Engine represents unresolved implementation choices as bounded candidate pools. For example, import strategy, auth library, architecture style, or error policy may initially have multiple candidates. The engine filters candidates using hard constraints, scores them using documentation and project context, then collapses them deterministically with tie-breakers. Random generation is forbidden after resolution.

The MVP should compile a constrained SML file into a FastAPI backend with Pydantic models and pytest tests. It should support #Project, #Stack, #Module, #DataModel, #Route, #Policy, and #Test. It should include a parser, Pydantic schemas, SIR graph builder, candidate resolver, Python FastAPI target pack, deterministic codegen, CLI commands, and golden tests.

Your implementation priorities are:
1. Define the grammar and parser.
2. Define Pydantic models for SML AST and SIR.
3. Build semantic validation and reference resolution.
4. Build a minimal latent resolution engine.
5. Build the Python FastAPI target pack.
6. Add deterministic golden tests.
7. Add PydanticAI agents only after the deterministic compiler path works.

Never bypass the compiler by asking the LLM to directly write final source code. If generated code fails, map the failure back to SML/SIR/source maps and patch the semantic layer or target pack.
```

---

# 38. Appendices

## Appendix A: SML Design Checklist

A new SML feature must answer:

- What semantic concept does it represent?
- Which SIR node does it map to?
- Which target packs can compile it?
- What validation rules apply?
- What latent choices can it introduce?
- How is it versioned?
- How does it appear in diffs?
- What golden tests cover it?

## Appendix B: Target Pack Checklist

A target pack must provide:

- ID.
- Supported SIR nodes.
- Default policies.
- Candidate providers.
- Codegen passes.
- Import rules.
- Dependency manifest rules.
- Formatter commands.
- Static analysis commands.
- Test generator.
- Golden fixtures.

## Appendix C: Anti-Bloat Rules

Default compiler policies:

```yaml
anti_bloat:
  broad_exception_handlers: forbidden
  unused_helpers: forbidden
  duplicate_validation: forbidden
  unnecessary_wrapper_classes: discouraged
  handwritten_standard_library_equivalents: forbidden
  max_function_lines: 60
  max_file_lines: 350
```

## Appendix D: Example `sml.lock`

```json
{
  "sml_version": "0.1.0",
  "compiler_version": "0.1.0",
  "target_packs": {
    "python.fastapi": "0.1.0"
  },
  "knowledge_packs": {
    "fastapi": "sha256:...",
    "pydantic": "sha256:..."
  },
  "resolution_policy": "deterministic-default-v1"
}
```

## Appendix E: Example Validation Error

```text
ERROR SML104: Unresolved reference ProductCreate
File: project.sml.md
Line: 34

Route CreateProduct declares:
  body: ProductCreate

But no DataModel, Schema, or DTO named ProductCreate exists.

Suggested fixes:
  1. Add #DataModel ProductCreate
  2. Change body to Product
  3. Enable compiler option derive_create_schema: true
```

## Appendix F: Example SML Patch

```diff
 #DataModel Product
 fields:
   id: uuid primary
   name: string required max=120
   sku: string unique required
   quantity: int default=0

+#DataModel ProductCreate
+fields:
+  name: string required max=120
+  sku: string unique required
+  quantity: int default=0
```

---

# 39. References

The implementation should continue to use current official documentation as the source of truth. The following references were used to ground this architecture draft:

1. PydanticAI documentation: structured outputs, agents, tools, retries, and graph workflows.
2. Pydantic documentation: models, validation, and JSON Schema generation.
3. Python official documentation: `ast` module for abstract syntax trees.
4. Node.js official documentation: ECMAScript modules and CommonJS modules.
5. TypeScript official documentation: module system behavior for Node.js modes.
6. FastAPI official documentation: OpenAPI, Pydantic integration, and API framework patterns.
7. Lark documentation: grammar-based parsing in Python.

---

# 40. Immediate Implementation Task List

The next development agent should start with these exact tasks:

## Task 1: Create Repository Skeleton

Create:

```text
semantic-software-markup/
  compiler/
  sml/
  agents/
  rag/
  cli/
  examples/
  tests/
```

## Task 2: Implement Initial Grammar

Create:

```text
sml/grammar/sml.lark
```

Support:

- directives
- sections
- key-value fields
- nested lists
- comments
- source ranges

## Task 3: Implement Parser

Create:

```text
compiler/frontend/parser.py
```

Output:

```python
SMLDocument
```

## Task 4: Implement Pydantic Schemas

Create:

```text
compiler/frontend/sml_ast.py
compiler/ir/nodes.py
```

## Task 5: Implement Semantic Analyzer

Create:

```text
compiler/semantic/analyzer.py
```

It must:

- create node IDs
- build symbol table
- resolve references
- build SIR graph
- emit validation errors

## Task 6: Implement Minimal Target Pack

Create:

```text
compiler/backends/python_fastapi/
```

Support:

- FastAPI app
- Pydantic schemas
- in-memory repository
- CRUD routes
- pytest tests

## Task 7: Implement CLI

Create:

```text
cli/main.py
```

Commands:

```bash
smlc validate
smlc compile
smlc inspect
```

## Task 8: Add Golden Test

Create:

```text
examples/todo-api/project.sml.md
tests/golden/test_todo_api.py
```

Assert deterministic output.

## Task 9: Add Latent Resolution MVP

Support these dimensions:

```text
backend_architecture
python_import_style
error_handling_policy
id_strategy
```

## Task 10: Add Agent Layer After Compiler Core

Only after deterministic compile works, add:

```text
agents/intent_agent.py
agents/sml_agent.py
agents/repair_agent.py
```

The agent layer must generate or patch SML, not final source code.

---

# 41. Final Architectural Summary

This project should be built as a compiler system, not as a chatbot wrapper.

The durable intellectual contribution is the combination of:

1. A human-readable Software Markup Language.
2. A typed Semantic Intermediate Representation.
3. A Latent Resolution Engine for bounded ambiguity.
4. Deterministic target-pack code generation.
5. PydanticAI-based structured agent orchestration.
6. Documentation-grounded RAG with provenance.
7. Validation and repair at the semantic layer.

The first prototype should be narrow, deterministic, and testable. The long-term system can become a generalized infrastructure layer for AI-assisted software engineering.


---

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


---

# Symbolic Logic Decision Layer Specification

**Document:** Logic Decision Layer Specification  
**Version:** v1.1  
**Role:** This document defines how classical logic, implication rules, satisfiability checks, and proof traces are integrated into the SML Compiler architecture.

---

## 1. Purpose

The project can be understood as entropy management, but entropy management alone is insufficient. Natural language ambiguity must eventually be converted into formal claims. Classical logic and mathematical implication should be integrated as decision layers because implication schemes can eliminate ambiguity where prompts and embeddings cannot.

The Symbolic Logic Decision Layer sits between SIR construction and candidate resolution.

```text
SML → SIR → Logic Facts + Rules → Admissible Candidate Set → Resolver → Codegen
```

The layer answers one question before generation:

> Is this design candidate logically admissible under the current facts, rules, constraints, assumptions, and policies?

If no, the candidate is rejected before scoring.

---

## 2. Design principle

The compiler uses two kinds of decision mechanisms:

### Hard decisions

Hard decisions are governed by symbolic logic, type checks, invariants, policy constraints, package compatibility, and satisfiability.

A hard decision can reject a candidate.

### Soft decisions

Soft decisions are governed by ranking, probability, style preference, documentation similarity, simplicity, maintainability, and target-pack defaults.

A soft decision can choose among valid candidates, but cannot rescue an invalid candidate.

```text
Candidate pool
  ↓
Hard symbolic filtering
  ↓
Admissible candidates only
  ↓
Soft scoring
  ↓
Deterministic tie-break
```

---

## 3. Formal model

### 3.1 Facts

A fact is an atomic proposition about the project.

```text
Project(InventoryAPI)
Target(PythonFastAPI)
Database(PostgreSQL)
Route(ListProducts)
Method(ListProducts, GET)
Path(ListProducts, "/products")
AuthRequired(ListProducts)
Model(Product)
Field(Product, sku)
Unique(Product, sku)
```

### 3.2 Rules

Rules are implications.

```text
AuthRequired(r) ∧ Target(PythonFastAPI) → Requires(Service(TokenVerifier))
Database(PostgreSQL) → Requires(EnvVar(DATABASE_URL))
Field(m, f) ∧ Unique(m, f) → Requires(DatabaseUniqueConstraint(m, f))
Route(r) ∧ Body(r, t) → Requires(Schema(t))
```

### 3.3 Constraints

Constraints forbid invalid combinations.

```text
BroadCatch(Exception) ∧ Policy(ForbidBroadCatch) → Invalid(BroadCatch(Exception))
Target(PythonFastAPI) ∧ PydanticVersion(v1) ∧ Policy(PydanticV2Only) → Invalid(PydanticVersion(v1))
CircularDependency(a, b) → Invalid(Dependency(a, b))
```

### 3.4 Assumptions

Assumptions are temporary facts introduced by the compiler or agent.

```text
Assume(DefaultArchitecture, RouterServiceRepository)
Assume(DefaultIDStrategy, UUID)
```

Assumptions must be recorded in provenance and can be overridden by explicit SML.

### 3.5 Candidate admissibility

A candidate is admissible only if the fact set remains satisfiable when the candidate is added.

```text
Admissible(c) ⇔ S ∧ R ∧ A ∧ C(c) ⊭ ⊥
```

Where:

- `S` = SIR fact set
- `R` = rule set
- `A` = assumptions
- `C(c)` = candidate-specific facts
- `⊥` = contradiction / invalid state

---

## 4. Reasoning modes

The MVP can implement a small custom implication engine. Later versions can support specialized engines.

| Reasoning Mode | Use | Possible Tooling |
|---|---|---|
| Horn clauses | dependency closure and required artifacts | custom engine, Datalog |
| SAT | discrete compatibility and feature flags | PySAT |
| SMT | versions, numeric ranges, resource constraints | Z3 |
| Datalog | derived facts and traceable dependency logic | pyDatalog, Soufflé-style backend |
| Type/refinement checks | schema and model constraints | Pydantic + custom validators |
| Prolog-like queries | explainability and proof search | custom or optional logic backend |

MVP should not require all engines. MVP should implement enough Horn-rule logic to reject inconsistent candidate choices.

---

## 5. Open-world and closed-world policy

Natural-language interpretation begins in an open-world mode: absence of evidence does not mean false.

Compilation strict mode uses closed-world enforcement for required facts: any required fact not present or derivable is an error.

```text
Intent ingestion: open world
SML validation: partially open
SIR logic validation: closed for required compiler facts
Codegen: closed world
```

This prevents the system from silently inventing missing requirements.

---

## 6. SML additions

### 6.1 Rule section

```sml
#Rule AuthRequiresVerifier
when:
  - AuthRequired($route)
  - Target(PythonFastAPI)
then:
  - Requires(Service(TokenVerifier))
severity: error
```

### 6.2 Invariant section

```sml
#Invariant NoBroadExceptionHandlers
forbid:
  - BroadCatch(Exception)
unless:
  - ExplicitPolicy(AllowBroadCatch)
severity: error
```

### 6.3 Assumption section

```sml
#Assumption DefaultArchitecture
fact: Architecture(RouterServiceRepository)
source: compiler_default
can_override: true
```

### 6.4 Decision section

```sml
#Decision BackendArchitecture
candidates:
  - SingleFile
  - RouterServiceRepository
constraints:
  - NoCircularDependencies
  - MaxFileLines(350)
select: deterministic
```

---

## 7. Logic facts generated from SIR

The semantic analyzer must translate SIR nodes into facts.

Example SML:

```sml
#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product
```

Generated facts:

```text
Route(CreateProduct)
Method(CreateProduct, POST)
Path(CreateProduct, "/products")
AuthRequired(CreateProduct)
Body(CreateProduct, ProductCreate)
Returns(CreateProduct, Product)
Requires(Schema(ProductCreate))
Requires(Schema(Product))
```

If `ProductCreate` cannot be resolved or derived, validation fails.

---

## 8. Proof object schema

Every hard decision should emit a proof or explanation object.

```json
{
  "decision_id": "route.CreateProduct.body_schema",
  "claim": "Requires(Schema(ProductCreate))",
  "status": "proved",
  "support": [
    "Route(CreateProduct)",
    "Body(CreateProduct, ProductCreate)",
    "Rule: RouteBodyRequiresSchema"
  ],
  "source": "project.sml.md:42-48"
}
```

A rejected candidate should explain the contradiction.

```json
{
  "candidate": "BroadCatchExceptionHandler",
  "status": "rejected",
  "because": [
    "Policy(ForbidBroadCatch)",
    "Candidate introduces BroadCatch(Exception)",
    "Rule: BroadCatchForbidden"
  ]
}
```

---

## 9. Integration with latent resolution

Before v1.1, latent resolution selected among candidates using constraints and scoring. In v1.1, it must call the logic layer first.

```python
for choice in latent_choices:
    candidates = candidate_provider(choice)
    admissible = []
    for c in candidates:
        proof = logic_engine.check_admissibility(sir_facts, rules, assumptions, c)
        if proof.status == "admissible":
            admissible.append((c, proof))
        else:
            trace.reject(c, proof)

    if not admissible:
        raise NoAdmissibleCandidate(choice)

    selected = scorer.rank(admissible)
    selected = deterministic_tie_break(selected)
```

---

## 10. MVP logic engine

MVP should implement:

- fact storage;
- rule storage;
- forward-chaining implication;
- invalid-state detection;
- missing-required-fact detection;
- proof traces;
- deterministic rule ordering;
- JSON export of facts and proofs.

MVP does not need full first-order theorem proving.

---

## 11. Example hard rules for FastAPI MVP

```text
Route(r) ∧ Method(r, POST) ∧ Body(r, s) → Requires(Schema(s))
Route(r) ∧ Returns(r, s) → Requires(Schema(s))
AuthRequired(r) → Requires(Dependency(CurrentUser))
Target(PythonFastAPI) ∧ Requires(Dependency(CurrentUser)) → Requires(Module(app.core.security))
Database(PostgreSQL) → Requires(Dependency(SQLAlchemy))
Database(PostgreSQL) → Requires(EnvVar(DATABASE_URL))
Unique(model, field) → Requires(DatabaseConstraint(unique(model, field)))
Policy(ForbidBroadCatch) ∧ Candidate(BroadCatchException) → Invalid(Candidate)
```

---

## 12. Testing requirements

The logic layer must include tests for:

- valid derivation;
- missing schema rejection;
- broad exception rejection;
- dependency closure;
- circular dependency rejection;
- deterministic proof ordering;
- candidate admissibility;
- contradiction reporting.

---

## 13. Architectural impact

The logic layer makes the project more than a prompt normalizer. It turns the compiler into a neuro-symbolic software synthesis system:

- LLMs produce structured semantic intent.
- Symbolic logic eliminates impossible choices.
- The resolver chooses among admissible candidates.
- The compiler generates deterministic source code.
- Proof traces explain decisions.
