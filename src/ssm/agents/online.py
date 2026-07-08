from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ssm.agents.providers import (
    ChatMessage,
    LLMProvider,
    ProviderError,
    ProviderResponseError,
    assert_no_source_code,
    extract_json_object,
    make_generation_provider,
)
from ssm.agents.schemas import SMLDocumentDraft
from ssm.agents.settings import OnlineAgentSettings, SecretRedactor
from ssm.errors import SSMError
from ssm.pipeline import SSMCompiler


class OnlineAgentDisabledError(ProviderError):
    pass


class OnlineDraftValidationError(ProviderResponseError):
    pass


class OnlineAgentAuditLogger:
    """Append-only JSONL audit log for online agent calls.

    Prompts and responses are represented by hashes unless explicit prompt
    logging is enabled. API keys and known secrets are redacted before writing.
    """

    def __init__(self, settings: OnlineAgentSettings, redactor: SecretRedactor | None = None):
        self.settings = settings
        self.path = Path(settings.agent_audit_log) if settings.agent_audit_log else None
        self.redactor = redactor or SecretRedactor.from_env()

    def write(self, event: dict[str, Any]) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sanitized = self._sanitize(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sanitized, sort_keys=True, separators=(",", ":")) + "\n")

    def _sanitize(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(payload, default=str)
        redacted = self.redactor.redact(text)
        parsed = json.loads(redacted)
        if not self.settings.agent_log_prompts:
            parsed.pop("prompt", None)
            parsed.pop("response", None)
        return parsed if isinstance(parsed, dict) else {}


class OnlineDraftService:
    """Online prompt-to-SML service.

    Online models are allowed to draft SML only. The deterministic compiler still
    owns semantic validation, resolution, and final source generation.
    """

    def __init__(
        self,
        settings: OnlineAgentSettings,
        provider: LLMProvider | None = None,
        compiler: SSMCompiler | None = None,
        audit_logger: OnlineAgentAuditLogger | None = None,
    ):
        self.settings = settings
        self.provider = provider or make_generation_provider(settings)
        self.compiler = compiler or SSMCompiler()
        self.audit_logger = audit_logger or OnlineAgentAuditLogger(settings)

    @classmethod
    def from_env(cls, settings: OnlineAgentSettings | None = None) -> OnlineDraftService:
        resolved = settings or OnlineAgentSettings.from_env()
        return cls(resolved)

    def draft(self, prompt: str) -> SMLDocumentDraft:
        self._require_online_enabled()
        run_id = str(uuid.uuid4())
        last_error = ""
        for attempt in range(self.settings.llm_max_retries + 1):
            messages = self._messages(prompt, last_error=last_error)
            started = time.time()
            try:
                response = self.provider.generate(messages)
                draft = self._parse_and_validate(response.text)
                elapsed_ms = int((time.time() - started) * 1000)
                draft.provenance.append(f"online:{response.provider}:{response.model}:run:{run_id}")
                self.audit_logger.write(
                    {
                        "event": "online_draft_success",
                        "run_id": run_id,
                        "attempt": attempt + 1,
                        "provider": response.provider,
                        "model": response.model,
                        "usage": response.usage.model_dump(),
                        "elapsed_ms": elapsed_ms,
                        "prompt_sha256": _sha256(prompt),
                        "prompt": prompt,
                        "response_sha256": _sha256(response.text),
                        "response": response.text,
                    }
                )
                return draft
            except (ProviderResponseError, ValidationError, SSMError, ValueError) as exc:
                last_error = str(exc)
                self.audit_logger.write(
                    {
                        "event": "online_draft_retryable_validation_error",
                        "run_id": run_id,
                        "attempt": attempt + 1,
                        "provider": getattr(self.provider, "name", "unknown"),
                        "model": getattr(self.provider, "model", "unknown"),
                        "prompt_sha256": _sha256(prompt),
                        "error": last_error,
                    }
                )
                if attempt >= self.settings.llm_max_retries:
                    raise OnlineDraftValidationError(last_error) from exc
        raise OnlineDraftValidationError(last_error or "Online draft did not produce valid SML.")

    def _require_online_enabled(self) -> None:
        if self.settings.agent_mode != "online" or not self.settings.run_online_ai:
            raise OnlineAgentDisabledError(
                "Online AI is disabled. Set RUN_ONLINE_AI=1 and SSM_AGENT_MODE=online, "
                "or pass --agent-mode online."
            )

    def _parse_and_validate(self, text: str) -> SMLDocumentDraft:
        payload = extract_json_object(text)
        draft = SMLDocumentDraft.model_validate(payload)
        assert_no_source_code(draft.text)
        if not draft.text.strip().startswith("#Project"):
            raise OnlineDraftValidationError("SML draft must start with a #Project section.")
        # Compile, not just parse. This proves schema references, symbolic rules,
        # resolver decisions, and target-pack generation all accept the model output.
        self.compiler.compile_text(draft.text, source_file="<online-draft>")
        return draft

    def _messages(self, prompt: str, *, last_error: str) -> list[ChatMessage]:
        repair_instruction = ""
        if last_error:
            repair_instruction = (
                f"\nPrevious attempt failed compiler validation:\n{last_error}\nRepair the SML."
            )
        return [
            ChatMessage(role="system", content=_SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=(
                    "Draft SML for this request. Return only a JSON object matching the required "
                    f"schema.\n\nUSER REQUEST:\n{prompt}{repair_instruction}"
                ),
            ),
        ]


_SYSTEM_PROMPT = """You are the online SML drafting agent for a deterministic semantic app compiler.

Return a single JSON object only. Do not emit markdown fences. The JSON object must match:
{
  "text": "<SML markdown document>",
  "assumptions": ["..."],
  "unresolved_questions": ["..."],
  "provenance": ["online-llm"]
}

You may emit SML only. Do not emit Python, FastAPI, SQLAlchemy, Dockerfile, JavaScript, or shell code.
The deterministic compiler emits final source code later.

General app-foundation SML sections supported in this version:
#Project, #Stack, #Capability, #Tenant, #Audit, #Role, #DataModel, #Relationship,
#Workflow, #StateMachine, #BusinessRule, #Invariant, #Event, #Report, #Integration,
#Route, #Policy, #Constraint.

Core generation sections:
#Project
name: <project name>
description: <short description>

#Stack
backend: FastAPI
database: PostgreSQL | InMemory
auth: JWT

#DataModel <Name>
fields:
  id: uuid primary
  name: string required max=120
  status: string required max=40 default=draft

#DataModel <Name>Create
fields:
  name: string required max=120
  status: string required max=40 default=draft

#Route <Name>
method: GET | POST | PATCH | PUT | DELETE
path: /resources or /resources/{id}
auth: required
body: <SchemaName> | none
returns: <SchemaName> | <SchemaName>[]

Rules:
- Model app foundations across domains, not only inventory.
- Pick capability sections such as generic_crud, workflow_approval, inventory, hr, expense, crm, procurement, ticketing, or school when relevant.
- For create/update routes, define both Resource and ResourceCreate models.
- For CRUD requests, include list, create, get-by-id, patch/update, and delete routes.
- For workflow apps, include #Workflow with states, transitions, and actions.
- For relationship fields, prefer explicit <entity>_id uuid fields plus #Relationship metadata.
- For SaaS requests, include #Tenant enabled and #Audit enabled.
- For PostgreSQL requests, use database: PostgreSQL.
- For JWT/auth requests, use auth: JWT and auth: required on routes.
- Always include #Policy ErrorHandling and #Constraint Architecture.
- Keep names PascalCase for models and route names.
- Do not leave a route body or return schema undefined; use body: none when there is no body.
- If a requested integration is outside the compiler's scope, add it to assumptions/questions rather than inventing source code.
"""


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
