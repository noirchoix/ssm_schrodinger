# Handoff Prompt v1.1

You are taking over development of Semantic Software Markup Compiler v1.1.

The project is a compiler-style neuro-symbolic software synthesis system. It must not be treated as a normal LLM code generator.

Core architecture:

```text
Natural-language request → PydanticAI agents → requirements model → documentation/source registry RAG → SML → parser → SIR → symbolic logic decision layer → latent resolver → deterministic IR → compiler backend → generated source → static analysis/tests → semantic repair
```

The most important principles are:

1. AI understands intent; the compiler emits code.
2. SML is the source of truth; generated source is a build artifact.
3. Symbolic logic is a hard decision layer, not documentation.
4. Candidate implementations must pass admissibility checks before scoring.
5. Classical implication rules should derive required artifacts and reject contradictions.
6. The MVP must remain small: SML parser, SIR, logic layer, resolver, FastAPI target, golden tests.
7. Do not let an LLM directly write final generated source in the deterministic compiler path.

Start by implementing:

```text
compiler/frontend/parser.py
compiler/frontend/sml_ast.py
compiler/semantic/analyzer.py
compiler/semantic/fact_extractor.py
compiler/logic/facts.py
compiler/logic/rules.py
compiler/logic/engine.py
compiler/logic/proof.py
compiler/resolver/admissibility.py
compiler/backends/python_fastapi/target.py
cli/main.py
tests/golden/
```

MVP logic must support:

- facts;
- Horn-style implication rules;
- invalid facts;
- required facts;
- missing required artifact errors;
- deterministic proof traces;
- candidate rejection before scoring.

First golden examples:

1. Todo API compiles successfully.
2. Product API with missing `ProductCreate` fails with a semantic error.
3. Broad exception handler candidate is rejected under `ForbidBroadCatch` policy.
4. PostgreSQL target derives `DATABASE_URL` requirement.
5. Auth-required route derives token verifier/security dependency.
6. Re-running compile produces identical output and identical proof trace.
