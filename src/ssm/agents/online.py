from __future__ import annotations

import hashlib
import json
import re
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
        normalized_text = normalize_online_sml(draft.text)
        if normalized_text != draft.text:
            draft = draft.model_copy(update={"text": normalized_text})
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

Role syntax must be flat SML sections. Do not emit a YAML-style roles: list.

Valid role syntax:
#Role Manager
permissions: [approve_leave, reject_leave, view_leave_requests]

Invalid role syntax:
roles:
  - name: Manager
    permissions:
      - approve_leave


Relationship syntax must be flat SML sections. Do not emit YAML/list-style relationship objects.

Valid relationship syntax:
#Relationship EmployeeManager
source: Employee
target: Employee
cardinality: many-to-one
required: false

Invalid relationship syntax:
#Relationship EmployeeManager
- from: Employee.manager_id
  to: Employee.id
  type: many-to-one

Workflow syntax must use scalar transition lists. Do not emit mapping objects under transitions.

Valid workflow syntax:
#Workflow LeaveApproval
entity: LeaveRequest
states:
  - pending
  - approved
  - rejected
transitions:
  - pending -> approved
  - pending -> rejected
actions:
  - approve_leave
  - reject_leave

Invalid workflow syntax:
#Workflow LeaveApproval
transitions:
  - from: pending
    to: approved
    action: approve_leave

Rules:
- Model app foundations across domains, not only inventory.
- Pick capability sections such as generic_crud, workflow_approval, inventory, hr, expense, crm, procurement, ticketing, or school when relevant.
- For create/update routes, define both Resource and ResourceCreate models.
- For CRUD requests, include list, create, get-by-id, patch/update, and delete routes.
- For workflow apps, include #Workflow with states, transitions, and actions.
- For relationship fields, prefer explicit <entity>_id uuid fields plus #Relationship metadata.
- Relationship source and target values must be existing #DataModel names, not field paths.
- For manager approval, prefer Employee.manager_id with a self-relationship from Employee to Employee.
- For SaaS requests, include #Tenant enabled and #Audit enabled.
- For PostgreSQL requests, use database: PostgreSQL.
- For JWT/auth requests, use auth: JWT and auth: required on routes.
- Always include #Policy ErrorHandling and #Constraint Architecture.
- Keep names PascalCase for models and route names.
- Do not use YAML list blocks such as roles: followed by - name: entries.
- Do not use relationship list items such as - from: / to: under #Relationship.
- Do not use nested transition objects such as - from: / to: / action: under transitions.
- Use scalar transition strings such as pending -> approved.
- Use inline bracket lists for permissions and similar flat lists.
- Do not leave a route body or return schema undefined; use body: none when there is no body.
- If a requested integration is outside the compiler's scope, add it to assumptions/questions rather than inventing source code.
"""


_ROLE_NAME_RE = re.compile(r"^name\s*:\s*(?P<value>.+?)\s*$", re.IGNORECASE)
_PERMISSIONS_RE = re.compile(r"^permissions\s*:\s*(?P<value>.*)\s*$", re.IGNORECASE)
_SECTION_HEADING_RE = re.compile(r"^#(?P<type>[A-Za-z][A-Za-z0-9_]*)(?:\s+(?P<name>.*?))?\s*$")
_RELATIONSHIP_LIST_KV_RE = re.compile(
    r"^-\s*(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(?P<value>.*)\s*$"
)
_RELATIONSHIP_KV_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(?P<value>.*)\s*$")
_TRANSITION_LIST_KV_RE = re.compile(
    r"^-\s*(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(?P<value>.*)\s*$"
)
_TRANSITION_KV_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(?P<value>.*)\s*$")


def normalize_online_sml(text: str) -> str:
    """Normalize common live-LLM SML syntax drift before strict compilation.

    The SML grammar intentionally rejects YAML-style nested list blocks such as
    ``roles:`` followed by ``- name: Manager``. Live LLMs often emit that shape
    even after being instructed to use ``#Role`` sections. This function keeps
    the parser strict while converting that narrow, recoverable drift into the
    compiler-supported flat SML form.
    """

    normalized = _flatten_roles_collection(text)
    normalized = _flatten_role_permission_blocks(normalized)
    normalized = _flatten_relationship_list_blocks(normalized)
    normalized = _flatten_transition_object_blocks(normalized)
    return normalized


def _flatten_roles_collection(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    changed = False

    while index < len(lines):
        line = lines[index]
        if line.strip() != "roles:":
            output.append(line)
            index += 1
            continue

        base_indent = _indent_width(line)
        block: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.strip() and _indent_width(candidate) <= base_indent:
                break
            block.append(candidate)
            cursor += 1

        roles = _parse_roles_collection(block)
        if not roles:
            output.append(line)
            output.extend(block)
            index = cursor
            continue

        rendered = _render_role_sections(roles)
        if output and output[-1].strip():
            output.append("")
        output.extend(rendered)
        if cursor < len(lines) and lines[cursor].strip():
            output.append("")
        index = cursor
        changed = True

    if not changed:
        return text
    return "\n".join(output).rstrip() + "\n"


def _parse_roles_collection(block: list[str]) -> list[dict[str, list[str] | str]]:
    roles: list[dict[str, list[str] | str]] = []
    current: dict[str, list[str] | str] | None = None
    collecting_permissions = False

    for raw_line in block:
        stripped = raw_line.strip()
        if not stripped:
            continue

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            name_match = _ROLE_NAME_RE.match(item)
            if name_match:
                if current:
                    roles.append(current)
                current = {"name": _clean_scalar(name_match.group("value")), "permissions": []}
                collecting_permissions = False
                continue

            if collecting_permissions and current is not None:
                permissions_value = current.setdefault("permissions", [])
                if isinstance(permissions_value, list):
                    permissions_value.append(_clean_scalar(item))
                continue

            if current:
                roles.append(current)
            current = {"name": _clean_scalar(item), "permissions": []}
            collecting_permissions = False
            continue

        if current is None:
            continue

        name_match = _ROLE_NAME_RE.match(stripped)
        if name_match:
            current["name"] = _clean_scalar(name_match.group("value"))
            collecting_permissions = False
            continue

        permissions_match = _PERMISSIONS_RE.match(stripped)
        if permissions_match:
            current["permissions"] = _parse_inline_list(permissions_match.group("value"))
            collecting_permissions = not bool(permissions_match.group("value").strip())
            continue

        collecting_permissions = False

    if current:
        roles.append(current)

    return [role for role in roles if str(role.get("name", "")).strip()]


def _render_role_sections(roles: list[dict[str, list[str] | str]]) -> list[str]:
    rendered: list[str] = []
    for position, role in enumerate(roles):
        name = _clean_role_name(str(role.get("name", "")))
        permissions_value = role.get("permissions", [])
        permissions = permissions_value if isinstance(permissions_value, list) else []
        if position:
            rendered.append("")
        rendered.append(f"#Role {name}")
        rendered.append(f"permissions: [{', '.join(_clean_scalar(item) for item in permissions)}]")
    return rendered


def _flatten_role_permission_blocks(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    changed = False

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.lower() != "permissions:":
            output.append(line)
            index += 1
            continue

        base_indent = _indent_width(line)
        cursor = index + 1
        permissions: list[str] = []
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.strip() and _indent_width(candidate) <= base_indent:
                break
            candidate_stripped = candidate.strip()
            if candidate_stripped.startswith("- "):
                permissions.append(_clean_scalar(candidate_stripped[2:].strip()))
            elif candidate_stripped:
                break
            cursor += 1

        if not permissions:
            output.append(line)
            index += 1
            continue

        indent = line[: len(line) - len(line.lstrip())]
        output.append(f"{indent}permissions: [{', '.join(permissions)}]")
        index = cursor
        changed = True

    if not changed:
        return text
    return "\n".join(output).rstrip() + "\n"


def _flatten_relationship_list_blocks(text: str) -> str:
    """Flatten DeepSeek-style list objects inside #Relationship sections.

    The strict SML parser expects #Relationship bodies to contain direct
    key-value fields such as ``source: Employee`` and ``target: Manager``.
    Live LLMs often emit YAML-inspired list objects instead:

    #Relationship EmployeeManager
    - from: Employee.manager_id
      to: Employee.id
      type: many-to-one

    This normalizer converts that narrow, recoverable shape into the supported
    flat relationship syntax without loosening the parser.
    """

    lines = text.splitlines()
    output: list[str] = []
    index = 0
    changed = False

    while index < len(lines):
        line = lines[index]
        heading = _SECTION_HEADING_RE.match(line.strip())
        if not heading or heading.group("type").lower() != "relationship":
            output.append(line)
            index += 1
            continue

        output.append(line)
        cursor = index + 1
        body: list[str] = []
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.strip().startswith("#"):
                break
            body.append(candidate)
            cursor += 1

        normalized_body, body_changed = _normalize_relationship_body(body)
        output.extend(normalized_body)
        if (
            body_changed
            and cursor < len(lines)
            and lines[cursor].strip().startswith("#")
            and output
            and output[-1].strip()
        ):
            output.append("")
        changed = changed or body_changed
        index = cursor

    if not changed:
        return text
    return "\n".join(output).rstrip() + "\n"


def _normalize_relationship_body(body: list[str]) -> tuple[list[str], bool]:
    if not any(line.strip().startswith("- ") for line in body):
        return body, False

    fields: dict[str, str] = {}
    passthrough: list[str] = []
    changed = False
    collecting_relationship_item = False

    for raw_line in body:
        stripped = raw_line.strip()
        if not stripped:
            passthrough.append(raw_line)
            continue

        list_match = _RELATIONSHIP_LIST_KV_RE.match(stripped)
        if list_match:
            key = _normalize_relationship_key(list_match.group("key"))
            value = _normalize_relationship_value(key, list_match.group("value"))
            fields[key] = value
            collecting_relationship_item = True
            changed = True
            continue

        nested_match = _RELATIONSHIP_KV_RE.match(stripped)
        if collecting_relationship_item and nested_match and _indent_width(raw_line) > 0:
            key = _normalize_relationship_key(nested_match.group("key"))
            value = _normalize_relationship_value(key, nested_match.group("value"))
            fields[key] = value
            changed = True
            continue

        collecting_relationship_item = False
        passthrough.append(raw_line)

    if not changed:
        return body, False

    rendered: list[str] = []
    seen_keys: set[str] = set()
    for raw_line in passthrough:
        stripped = raw_line.strip()
        existing_match = _RELATIONSHIP_KV_RE.match(stripped)
        if existing_match and _indent_width(raw_line) == 0:
            key = _normalize_relationship_key(existing_match.group("key"))
            seen_keys.add(key)
            if key in fields:
                rendered.append(f"{key}: {fields[key]}")
            else:
                rendered.append(raw_line)
            continue
        rendered.append(raw_line)

    if rendered and rendered[-1].strip():
        rendered.append("")

    for key in ("source", "target", "cardinality", "required"):
        if key in fields and key not in seen_keys:
            rendered.append(f"{key}: {fields[key]}")

    if "cardinality" not in fields and "cardinality" not in seen_keys:
        rendered.append("cardinality: many-to-one")

    return _trim_excess_blank_lines(rendered), True


def _normalize_relationship_key(key: str) -> str:
    lowered = key.strip().lower().replace("-", "_")
    aliases = {
        "from": "source",
        "source": "source",
        "source_model": "source",
        "to": "target",
        "target": "target",
        "target_model": "target",
        "type": "cardinality",
        "kind": "cardinality",
        "relation": "cardinality",
        "relationship": "cardinality",
        "cardinality": "cardinality",
        "required": "required",
        "optional": "required",
    }
    return aliases.get(lowered, lowered)


def _normalize_relationship_value(key: str, value: str) -> str:
    cleaned = _clean_scalar(value)
    if key in {"source", "target"}:
        return _model_name_from_reference(cleaned)
    if key == "cardinality":
        return _normalize_cardinality(cleaned)
    if key == "required":
        return _normalize_bool_value(cleaned)
    return cleaned


def _model_name_from_reference(value: str) -> str:
    cleaned = _clean_scalar(value)
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[0]
    return _clean_scalar(cleaned)


def _normalize_cardinality(value: str) -> str:
    cleaned = _clean_scalar(value).lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "one-to-one": "one-to-one",
        "one-to-many": "one-to-many",
        "many-to-one": "many-to-one",
        "many-to-many": "many-to-many",
        "belongs-to": "many-to-one",
        "has-many": "one-to-many",
    }
    return aliases.get(cleaned, cleaned or "many-to-one")


def _normalize_bool_value(value: str) -> str:
    cleaned = _clean_scalar(value).strip().lower()
    if cleaned in {"false", "no", "optional", "0"}:
        return "false"
    if cleaned in {"true", "yes", "required", "1"}:
        return "true"
    return cleaned or "true"


def _trim_excess_blank_lines(lines: list[str]) -> list[str]:
    trimmed: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        trimmed.append(line)
        previous_blank = is_blank
    while trimmed and not trimmed[0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return trimmed


def _flatten_transition_object_blocks(text: str) -> str:
    """Flatten mapping-style transition objects into parser-supported scalars.

    The parser supports transition lists as scalar strings:

    transitions:
      - pending -> approved

    Live LLMs often emit YAML-style mapping objects instead:

    transitions:
      - from: pending
        to: approved
        action: approve_leave

    This normalizer changes only that recoverable shape and leaves ordinary
    scalar transition lists untouched.
    """

    lines = text.splitlines()
    output: list[str] = []
    index = 0
    changed = False

    while index < len(lines):
        line = lines[index]
        if line.strip().lower() != "transitions:":
            output.append(line)
            index += 1
            continue

        base_indent = _indent_width(line)
        cursor = index + 1
        block: list[str] = []
        while cursor < len(lines):
            candidate = lines[cursor]
            if candidate.strip() and _indent_width(candidate) <= base_indent:
                break
            block.append(candidate)
            cursor += 1

        normalized_block, block_changed = _normalize_transition_block(block, base_indent)
        output.append(line)
        output.extend(normalized_block)
        index = cursor
        changed = changed or block_changed

    if not changed:
        return text
    return "\n".join(output).rstrip() + "\n"


def _normalize_transition_block(block: list[str], parent_indent: int) -> tuple[list[str], bool]:
    if not any(_TRANSITION_LIST_KV_RE.match(line.strip()) for line in block):
        return block, False

    rendered: list[str] = []
    current: dict[str, str] | None = None
    changed = False
    item_indent = " " * (parent_indent + 2)

    def flush_current() -> None:
        nonlocal current
        if current is None:
            return
        transition = _render_transition_scalar(current)
        if transition:
            rendered.append(f"{item_indent}- {transition}")
        current = None

    for raw_line in block:
        stripped = raw_line.strip()
        if not stripped:
            continue

        list_match = _TRANSITION_LIST_KV_RE.match(stripped)
        if list_match:
            flush_current()
            key = _normalize_transition_key(list_match.group("key"))
            value = _clean_scalar(list_match.group("value"))
            current = {key: value}
            changed = True
            continue

        nested_match = _TRANSITION_KV_RE.match(stripped)
        if current is not None and _indent_width(raw_line) > parent_indent and nested_match:
            key = _normalize_transition_key(nested_match.group("key"))
            current[key] = _clean_scalar(nested_match.group("value"))
            changed = True
            continue

        flush_current()
        rendered.append(raw_line)

    flush_current()
    if not changed:
        return block, False
    return _trim_excess_blank_lines(rendered), True


def _normalize_transition_key(key: str) -> str:
    lowered = key.strip().lower().replace("-", "_")
    aliases = {
        "from": "from",
        "source": "from",
        "start": "from",
        "initial": "from",
        "to": "to",
        "target": "to",
        "destination": "to",
        "end": "to",
        "action": "action",
        "event": "action",
        "trigger": "action",
        "name": "action",
    }
    return aliases.get(lowered, lowered)


def _render_transition_scalar(fields: dict[str, str]) -> str:
    source = _clean_scalar(fields.get("from", ""))
    target = _clean_scalar(fields.get("to", ""))
    action = _clean_scalar(fields.get("action", ""))
    if source and target:
        return f"{source} -> {target}"
    if action and target:
        return f"{action} -> {target}"
    if source and action:
        return f"{source} -> {action}"
    values = [_clean_scalar(value) for value in fields.values() if _clean_scalar(value)]
    return " -> ".join(values[:2]) if len(values) >= 2 else (values[0] if values else "")


def _parse_inline_list(value: str) -> list[str]:
    cleaned = value.strip()
    if not cleaned:
        return []
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return [_clean_scalar(part) for part in cleaned.split(",") if _clean_scalar(part)]


def _clean_role_name(value: str) -> str:
    cleaned = _clean_scalar(value)
    cleaned = re.sub(r"[^A-Za-z0-9_ -]", "", cleaned).strip()
    return cleaned or "Role"


def _clean_scalar(value: object) -> str:
    cleaned = str(value).strip().strip('"').strip("'")
    return cleaned.strip()


def _indent_width(value: str) -> int:
    return len(value) - len(value.lstrip(" "))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
