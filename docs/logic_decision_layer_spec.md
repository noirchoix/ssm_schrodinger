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
