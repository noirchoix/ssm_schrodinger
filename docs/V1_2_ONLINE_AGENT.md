# V1.2 Online Agent Integration

V1.2 adds a gated online agent layer while preserving the deterministic compiler contract.

## Boundary

Online models may produce only SML drafts or semantic repair suggestions. They do not emit final Python, FastAPI, SQLAlchemy, Docker, or migration source code. The compiler still owns:

```text
SML -> SIR -> symbolic logic -> resolver -> deterministic target generation
```

## Generation providers

Supported generation providers:

- `openai` via an OpenAI-compatible chat-completions adapter.
- `deepseek` via the same OpenAI-compatible adapter.
- `gemini` via Gemini `generateContent` JSON responses.
- `mock` for deterministic CI and offline online-mode tests.

Required online gate:

```bash
export RUN_ONLINE_AI=1
export SSM_AGENT_MODE=online
export SSM_LLM_PROVIDER=deepseek # or gemini, openai, mock
export SSM_LLM_MODEL="<provider-model>"
export SSM_LLM_TEMPERATURE=0
export SSM_LLM_TIMEOUT_SECONDS=60
export SSM_LLM_MAX_RETRIES=2
export SSM_LLM_MAX_OUTPUT_TOKENS=3000
```

Provider API keys:

```bash
export OPENAI_API_KEY="..."      # provider=openai
export DEEPSEEK_API_KEY="..."    # provider=deepseek
export GEMINI_API_KEY="..."      # provider=gemini
```

`SSM_LLM_API_KEY` may be used as a provider-neutral override.

## Embeddings

Supported embedding providers:

- `gemini`
- `voyageai`
- `mock`

Example:

```bash
export SSM_EMBED_PROVIDER=voyageai
export VOYAGEAI_API_KEY="..."
export SSM_EMBED_MODEL="voyage-3-large"

python -m ssm.cli.main embed-text --text "SML source registry note" --out build/embed.json
```

Gemini embeddings use `GEMINI_API_KEY` or `GOOGLE_API_KEY`; VoyageAI embeddings use `VOYAGEAI_API_KEY`. `SSM_EMBED_API_KEY` may be used as a provider-neutral override.

## Online draft command

```bash
python -m ssm.cli.main draft \
  --agent-mode online \
  --prompt "Build a FastAPI inventory API with PostgreSQL, JWT auth, product CRUD, SKU uniqueness, pagination, OpenAPI contract tests, and Docker support." \
  --out build/online_inventory/project.sml.md

python -m ssm.cli.main validate build/online_inventory/project.sml.md
python -m ssm.cli.main compile build/online_inventory/project.sml.md --out build/online_inventory_api
```

## Acceptance gates

Online draft output is accepted only when:

1. The provider response is parseable JSON.
2. The JSON validates against `SMLDocumentDraft`.
3. The draft text is SML, not source code.
4. The SML compiles successfully through the deterministic compiler.
5. The generated app passes the existing generated-app gates.

Prompt and response bodies are hashed in the audit log by default. Full prompt/response logging is disabled unless `SSM_AGENT_LOG_PROMPTS=1` is explicitly set. API keys and known secrets are redacted.

## Offline online-mode CI

The mock provider exercises the online path without network access:

```bash
make online-mock-quality
```
