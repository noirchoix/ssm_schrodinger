from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from pytest import MonkeyPatch

import ssm.foundation.builder as builder_module
from ssm.agents.online import (
    OnlineDraftService,
    OnlineDraftValidationError,
    normalize_online_sml,
)
from ssm.foundation.builder import OnlineBuildService
from ssm.pipeline import SSMCompiler

DEEPSEEK_STYLE_SML = """#Project
name: HR Leave Approval SaaS
description: HR leave workflow foundation

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

roles:
  - name: Manager
    permissions:
      - approve_leave
      - reject_leave
  - name: Employee
    permissions:
      - create_leave_request
      - view_own_leave_requests

#DataModel Employee
fields:
  id: uuid primary
  name: string required max=120

#DataModel EmployeeCreate
fields:
  name: string required max=120

#Route ListEmployees
method: GET
path: /employees
auth: required
body: none
returns: Employee[]

#Policy ErrorHandling
rules: [standard_errors]

#Constraint Architecture
rules: [deterministic_generation]
"""

DEEPSEEK_STYLE_RELATIONSHIP_SML = """#Project
name: HR Leave Approval SaaS
description: HR leave workflow foundation

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#DataModel Employee
fields:
  id: uuid primary
  manager_id: uuid optional
  name: string required max=120

#DataModel EmployeeCreate
fields:
  manager_id: uuid optional
  name: string required max=120

#Relationship EmployeeManager
- from: Employee.manager_id
  to: Employee.id
  type: many-to-one
  required: false

#Route ListEmployees
method: GET
path: /employees
auth: required
body: none
returns: Employee[]

#Policy ErrorHandling
rules: [standard_errors]

#Constraint Architecture
rules: [deterministic_generation]
"""


class RecordingCompiler:
    def __init__(self) -> None:
        self.compiled_text = ""

    def compile_text(self, text: str, *, source_file: str) -> object:
        assert source_file == "<online-draft>"
        self.compiled_text = text
        return object()


def test_normalize_online_sml_flattens_deepseek_style_roles() -> None:
    normalized = normalize_online_sml(DEEPSEEK_STYLE_SML)

    assert "roles:" not in normalized
    assert "#Role Manager" in normalized
    assert "permissions: [approve_leave, reject_leave]" in normalized
    assert "#Role Employee" in normalized
    assert "permissions: [create_leave_request, view_own_leave_requests]" in normalized
    assert "#DataModel Employee" in normalized


def test_normalize_online_sml_flattens_relationship_list_items() -> None:
    normalized = normalize_online_sml(DEEPSEEK_STYLE_RELATIONSHIP_SML)

    assert "- from:" not in normalized
    assert "  to:" not in normalized
    assert "source: Employee" in normalized
    assert "target: Employee" in normalized
    assert "cardinality: many-to-one" in normalized
    assert "required: false" in normalized


def test_normalized_relationship_sml_compiles_with_core_compiler() -> None:
    normalized = normalize_online_sml(DEEPSEEK_STYLE_RELATIONSHIP_SML)

    result = SSMCompiler().compile_text(normalized, source_file="<test>")

    assert result.success is True
    generated_paths = {file.path for file in result.files}
    assert "app/models/employee.py" in generated_paths
    assert "app/api/routes/employee.py" in generated_paths


def test_online_draft_parse_validates_normalized_relationship_sml() -> None:
    service = object.__new__(OnlineDraftService)
    compiler = RecordingCompiler()
    service.compiler = compiler
    payload = json.dumps(
        {
            "text": DEEPSEEK_STYLE_RELATIONSHIP_SML,
            "assumptions": [],
            "unresolved_questions": [],
            "provenance": ["test"],
        }
    )

    draft = service._parse_and_validate(payload)

    assert draft.text == compiler.compiled_text
    assert "- from:" not in draft.text
    assert "source: Employee" in draft.text
    assert "target: Employee" in draft.text


def test_online_draft_parse_validates_normalized_sml() -> None:
    service = object.__new__(OnlineDraftService)
    compiler = RecordingCompiler()
    service.compiler = compiler
    payload = json.dumps(
        {
            "text": DEEPSEEK_STYLE_SML,
            "assumptions": [],
            "unresolved_questions": [],
            "provenance": ["test"],
        }
    )

    draft = service._parse_and_validate(payload)

    assert draft.text == compiler.compiled_text
    assert "roles:" not in draft.text
    assert "#Role Manager" in draft.text


def test_online_build_records_online_draft_validation_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    class AlwaysInvalidDraftService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def draft(self, prompt: str) -> object:
            raise OnlineDraftValidationError(
                "ERROR SML008: Nested list blocks under 'roles' are not supported in V1."
            )

    monkeypatch.setattr(builder_module, "OnlineDraftService", AlwaysInvalidDraftService)
    service = object.__new__(OnlineBuildService)
    service.settings = SimpleNamespace(llm_max_retries=0)
    service.compiler = object()
    service.negotiator = object()

    result = service.build(prompt="Build an HR leave app", out_dir=tmp_path, repair_attempts=1)

    assert result.status == "REJECTED"
    assert result.attempts == 1
    assert result.repair_trace_path is not None
    trace = json.loads(Path(result.repair_trace_path).read_text(encoding="utf-8"))
    assert trace["final_status"] == "REJECTED"
    assert trace["events"][0]["stage"] == "online_draft"
    assert trace["events"][0]["status"] == "rejected"
    assert "SML008" in trace["events"][0]["message"]
