from __future__ import annotations

import ast
import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

from ssm.agents import online as online_agent
from ssm.pipeline import SSMCompiler


def test_cli_compile_writes_project(tmp_path: Path) -> None:
    out = tmp_path / "generated"
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "ssm.cli.main",
            "compile",
            "examples/todo_api/project.sml.md",
            "--out",
            str(out),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["success"] is True
    assert (out / "app/main.py").exists()
    assert (out / "proof_trace.json").exists()
    assert (out / "sml.manifest.json").exists()


def test_generated_fastapi_project_imports(tmp_path: Path, monkeypatch) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/todo_api/project.sml.md")
    compiler.write_result(result, tmp_path)
    sys.path.insert(0, str(tmp_path))
    try:
        import app.main as generated_main

        assert generated_main.app is not None
    finally:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(tmp_path))


def test_postgres_inventory_selects_sqlalchemy_target_pack(tmp_path: Path) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/inventory_api/project.sml.md")
    paths = {f.path for f in result.files}
    assert "app/db/session.py" in paths
    assert "app/db/base.py" in paths
    assert "app/repositories/product_repository.py" in paths
    assert result.resolution.selected["repository_strategy"].id == "sqlalchemy"


def test_generated_inventory_includes_v11_hardening_artifacts(tmp_path: Path) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/inventory_api/project.sml.md")
    paths = {file.path for file in result.files}
    assert "docker-compose.yml" in paths
    assert ".github/workflows/ci.yml" in paths
    assert "tests/test_openapi_contract.py" in paths
    assert "tests/test_load_smoke.py" in paths
    assert "tests/test_postgres_integration.py" in paths
    assert "load/locustfile.py" in paths
    pyproject = next(file.content for file in result.files if file.path == "pyproject.toml")
    assert "--cov-fail-under=80" in pyproject


def test_generated_project_uses_formatter_owned_line_length_policy() -> None:
    result = SSMCompiler().compile_file("examples/hr_leave_api/project.sml.md")
    pyproject = next(file.content for file in result.files if file.path == "pyproject.toml")

    assert "[tool.ruff.lint]" in pyproject
    assert 'ignore = ["E501"]' in pyproject


def _workflow_rule_project(rule_entity: str) -> str:
    return f"""#Project WorkflowRuleTest
name: WorkflowRuleTest

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel LeaveRequest
fields:
  id: uuid primary
  requested_days: int required

#DataModel Tenant
fields:
  id: uuid primary
  active: bool required

#Workflow LeaveApproval
entity: LeaveRequest
states:
  - pending
  - approved
transitions:
  - pending -> approved
actions:
  - approve_leave

#BusinessRule PositiveValue
entity: {rule_entity}
rule: requested_days > 0
on_violation: reject
"""


def _generated_platform_test(sml: str) -> str:
    result = SSMCompiler().compile_text(sml, "workflow-rule-test.sml.md")
    return next(
        file.content for file in result.files if file.path == "tests/test_platform_primitives.py"
    )


def test_unrelated_business_rule_does_not_activate_selected_workflow_assertions() -> None:
    generated_test = _generated_platform_test(_workflow_rule_project("Tenant"))

    assert "PositiveValue" not in generated_test
    assert 'assert payload["rules"] == []' in generated_test
    assert 'assert payload["allowed"] is True' in generated_test


def test_applicable_business_rule_generates_result_consistency_assertions() -> None:
    generated_test = _generated_platform_test(_workflow_rule_project("LeaveRequest"))

    assert 'assert sorted(item["name"] for item in payload["rules"]) ==' in generated_test
    assert "PositiveValue" in generated_test
    assert 'expected_allowed = all(item["passed"] for item in payload["rules"])' in generated_test
    assert 'assert payload["allowed"] is expected_allowed' in generated_test
    assert '"accepted" if expected_allowed else "business_rule_rejected"' in generated_test


def test_online_prompt_defines_executable_runtime_rule_contract() -> None:
    prompt = online_agent._SYSTEM_PROMPT

    assert "#BusinessRule LeaveRequestDateValidation" in prompt
    assert "entity: LeaveRequest" in prompt
    assert "rule: end_date > start_date" in prompt
    assert "on_violation: reject" in prompt
    assert "do not use severity for runtime behavior" in prompt


def test_cli_draft_and_repair_commands(tmp_path: Path) -> None:
    draft_path = tmp_path / "draft.sml.md"
    env = dict(os.environ)
    env["PYTHONPATH"] = "src" + os.pathsep + env.get("PYTHONPATH", "")
    draft = subprocess.run(
        [
            sys.executable,
            "-m",
            "ssm.cli.main",
            "draft",
            "--prompt",
            "Build a FastAPI products API with PostgreSQL and JWT auth",
            "--out",
            str(draft_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert draft.returncode == 0, draft.stderr
    assert draft_path.exists()
    assert "#Project" in draft_path.read_text(encoding="utf-8")

    repair = subprocess.run(
        [
            sys.executable,
            "-m",
            "ssm.cli.main",
            "repair-missing-schema",
            "ProductCreate",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert repair.returncode == 0, repair.stderr
    payload = json.loads(repair.stdout)
    assert payload["target"] == "sml"
    assert "ProductCreate" in payload["patch"]


def test_generated_update_contract_uses_declared_update_schema() -> None:
    sml = """#Project LiveUpdateContract
name: LiveUpdateContract

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#DataModel LeaveRequest
fields:
  id: uuid primary
  status: string required default=pending
  start_date: datetime required default=now
  end_date: datetime required default=2026-07-31T17:00:00+00:00

#DataModel LeaveRequestCreate
fields:
  status: string required default=pending
  start_date: datetime required default=now
  end_date: datetime required default=2026-07-31T17:00:00+00:00

#DataModel LeaveRequestUpdate
fields:
  status: string
  start_date: datetime
  end_date: datetime

#Route ListLeaveRequests
method: GET
path: /leave-requests
auth: required
body: none
returns: LeaveRequest[]

#Route CreateLeaveRequest
method: POST
path: /leave-requests
auth: required
body: LeaveRequestCreate
returns: LeaveRequest

#Route UpdateLeaveRequest
method: PATCH
path: /leave-requests/{id}
auth: required
body: LeaveRequestUpdate
returns: LeaveRequest
"""

    result = SSMCompiler().compile_text(sml, "live-update-contract.sml.md")
    files = {file.path: file.content for file in result.files}

    assert "payload: LeaveRequestUpdate" in files["app/services/leave_request_service.py"]
    assert "payload: LeaveRequestUpdate" in files["app/repositories/leave_request_repository.py"]
    assert (
        'model_dump(mode="python", exclude_unset=True)'
        in files["app/repositories/leave_request_repository.py"]
    )
    assert "default_factory=lambda: datetime.now(UTC)" in files["app/schemas/leave_request.py"]
    assert "datetime.fromisoformat(" in files["app/schemas/leave_request.py"]
    assert "2026-07-31T17:00:00+00:00" in files["app/schemas/leave_request.py"]


def test_invalid_temporal_default_is_rejected_before_source_generation() -> None:
    sml = """#Project InvalidTemporalDefault
name: InvalidTemporalDefault

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel Event
fields:
  id: uuid primary
  starts_at: datetime required default=not-a-time

#DataModel EventCreate
fields:
  starts_at: datetime required default=not-a-time

#Route ListEvents
method: GET
path: /events
auth: required
body: none
returns: Event[]
"""

    try:
        SSMCompiler().compile_text(sml, "invalid-temporal-default.sml.md")
    except Exception as exc:
        assert "TGT202" in str(exc)
    else:
        raise AssertionError("invalid datetime default must be rejected")


def _patch_effective_state_project(database: str = "InMemory") -> str:
    return f"""#Project ProductPatchRules
name: ProductPatchRules

#Stack
backend: FastAPI
database: {database}
auth: JWT

#DataModel Product
fields:
  id: uuid primary
  quantity: int required
  max_stock: int required

#DataModel ProductCreate
fields:
  quantity: int required
  max_stock: int required

#DataModel ProductUpdate
fields:
  quantity: int
  max_stock: int

#Invariant StockCapacity
entity: Product
rule: quantity <= max_stock
on_violation: reject

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Route UpdateProduct
method: PATCH
path: /products/{{id}}
auth: required
body: ProductUpdate
returns: Product
"""


def test_generated_patch_uses_effective_state_for_multi_field_rules() -> None:
    result = SSMCompiler().compile_text(
        _patch_effective_state_project("PostgreSQL"),
        "patch-effective-state.sml.md",
    )
    files = {file.path: file.content for file in result.files}
    service = files["app/services/product_service.py"]

    assert "current_row = self.repository.get(db, item_id)" in service
    assert 'updates = payload.model_dump(mode="python", exclude_unset=True)' in service
    assert '{**current.model_dump(mode="python"), **updates}' in service
    assert "candidate.quantity" in service
    assert "StockCapacity" in service
    assert "quantity <= max_stock" in service
    assert "context = candidate.model_dump" in service
    assert "passed, detail = evaluate_rule(expression, context)" in service
    assert "def evaluate_rule" in files["app/platform/workflow.py"]


def test_generated_patch_effective_state_handles_omitted_and_supplied_fields(
    tmp_path: Path,
) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_text(
        _patch_effective_state_project(),
        "patch-effective-state-runtime.sml.md",
    )
    compiler.write_result(result, tmp_path)

    script = """
from app.core.errors import ValidationDomainError
from app.schemas.product_create import ProductCreate
from app.schemas.product_update import ProductUpdate
from app.services.product_service import service

created = service.create(ProductCreate(quantity=5, max_stock=10))
item_id = str(created.id)

omitted_quantity = service.update(item_id, ProductUpdate(max_stock=6))
assert omitted_quantity.quantity == 5
assert omitted_quantity.max_stock == 6

supplied_quantity = service.update(item_id, ProductUpdate(quantity=6))
assert supplied_quantity.quantity == 6
assert supplied_quantity.max_stock == 6

try:
    service.update(item_id, ProductUpdate(quantity=7))
except ValidationDomainError:
    pass
else:
    raise AssertionError("cross-field invariant should reject quantity > max_stock")

persisted = service.get(item_id)
assert persisted.quantity == 6
assert persisted.max_stock == 6
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


def _contextual_patch_rule_project() -> str:
    return """#Project ContextualPatchRules
name: ContextualPatchRules

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel LeaveRequest
fields:
  id: uuid primary
  employee_id: uuid required
  requested_days: int required

#DataModel LeaveRequestCreate
fields:
  employee_id: uuid required
  requested_days: int required

#DataModel LeaveRequestUpdate
fields:
  requested_days: int

#Workflow LeaveApproval
entity: LeaveRequest
states:
  - draft
  - approved
transitions:
  - draft -> approved
actions:
  - approve_leave

#Invariant LeaveBalanceCannotGoNegative
entity: LeaveRequest
rule: requested_days <= employee.leave_balance
on_violation: reject

#Route CreateLeaveRequest
method: POST
path: /leave-requests
auth: required
body: LeaveRequestCreate
returns: LeaveRequest

#Route UpdateLeaveRequest
method: PATCH
path: /leave-requests/{id}
auth: required
body: LeaveRequestUpdate
returns: LeaveRequest
"""


def test_contextual_invariant_stays_out_of_generic_crud_service() -> None:
    result = SSMCompiler().compile_text(
        _contextual_patch_rule_project(),
        "contextual-patch-rule.sml.md",
    )
    files = {file.path: file.content for file in result.files}
    service = files["app/services/leave_request_service.py"]
    workflow = files["app/platform/workflow.py"]

    assert "LeaveBalanceCannotGoNegative" not in service
    assert "requested_days <= employee.leave_balance" not in service
    assert "from app.platform.workflow import evaluate_rule" not in service
    assert "LeaveBalanceCannotGoNegative" in workflow
    assert "requested_days <= employee.leave_balance" in workflow


def test_contextual_rule_allows_crud_patch_but_remains_enforced_by_workflow(
    tmp_path: Path,
) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_text(
        _contextual_patch_rule_project(),
        "contextual-patch-rule-runtime.sml.md",
    )
    compiler.write_result(result, tmp_path)

    script = """
from uuid import UUID

from app.platform.workflow import workflow_runtime
from app.schemas.leave_request_create import LeaveRequestCreate
from app.schemas.leave_request_update import LeaveRequestUpdate
from app.services.leave_request_service import service

created = service.create(
    LeaveRequestCreate(
        employee_id=UUID("00000000-0000-4000-8000-000000000001"),
        requested_days=2,
    )
)
item_id = str(created.id)

updated = service.update(item_id, LeaveRequestUpdate(requested_days=3))
assert updated.requested_days == 3

missing_context = workflow_runtime.transition(
    "LeaveApproval",
    item_id,
    "approve_leave",
    context={"requested_days": 3},
)
assert missing_context.allowed is False
assert missing_context.reason == "business_rule_rejected"
assert missing_context.version == 0
assert missing_context.rules[0].detail.startswith("Missing rule context")

valid_context = workflow_runtime.transition(
    "LeaveApproval",
    item_id,
    "approve_leave",
    context={"requested_days": 3, "employee": {"leave_balance": 5}},
)
assert valid_context.allowed is True
assert valid_context.reason == "accepted"
assert valid_context.version == 1
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


def test_business_rules_remain_workflow_scoped_even_when_entity_local() -> None:
    sml = _contextual_patch_rule_project().replace(
        "#Invariant LeaveBalanceCannotGoNegative\n"
        "entity: LeaveRequest\n"
        "rule: requested_days <= employee.leave_balance\n"
        "on_violation: reject",
        "#BusinessRule PositiveRequestedDays\n"
        "entity: LeaveRequest\n"
        "rule: requested_days > 0\n"
        "on_violation: reject",
    )

    result = SSMCompiler().compile_text(sml, "business-rule-scope.sml.md")
    files = {file.path: file.content for file in result.files}

    assert "PositiveRequestedDays" not in files["app/services/leave_request_service.py"]
    assert "PositiveRequestedDays" in files["app/platform/workflow.py"]


def _distinct_route_body_project(update_method: str = "PATCH") -> str:
    return f"""#Project RouteBodyFixtures
name: RouteBodyFixtures

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel LeaveRequest
fields:
  id: uuid primary
  employee_id: uuid required
  requested_days: int required
  status: string

#DataModel LeaveRequestCreate
fields:
  employee_id: uuid required
  requested_days: int required

#DataModel LeaveRequestUpdate
fields:
  status: string

#Route ListLeaveRequests
method: GET
path: /leave-requests
auth: required
body: none
returns: LeaveRequest[]

#Route CreateLeaveRequest
method: POST
path: /leave-requests
auth: required
body: LeaveRequestCreate
returns: LeaveRequest

#Route GetLeaveRequest
method: GET
path: /leave-requests/{{id}}
auth: required
body: none
returns: LeaveRequest

#Route UpdateLeaveRequest
method: {update_method}
path: /leave-requests/{{id}}
auth: required
body: LeaveRequestUpdate
returns: LeaveRequest

#Route DeleteLeaveRequest
method: DELETE
path: /leave-requests/{{id}}
auth: required
body: none
returns: LeaveRequest
"""


def test_generated_route_tests_use_declared_update_schema_and_http_method() -> None:
    patch_result = SSMCompiler().compile_text(
        _distinct_route_body_project("PATCH"),
        "route-body-patch.sml.md",
    )
    patch_files = {file.path: file.content for file in patch_result.files}

    assert "LeaveRequestUpdate" in patch_files["tests/factories.py"]
    assert "status-leave_request_update-two" in patch_files["tests/factories.py"]
    assert "update_payload_for_route(" in patch_files["tests/test_api.py"]
    assert "LeaveRequestUpdate" in patch_files["tests/test_api.py"]
    assert "partial=True" in patch_files["tests/test_api.py"]
    assert "response = client.patch(" in patch_files["tests/test_api.py"]
    assert "assert response.status_code == 200, response.text" in patch_files["tests/test_api.py"]
    assert (
        "from app.schemas.leave_request_update import LeaveRequestUpdate"
        in patch_files["tests/test_service_contracts.py"]
    )
    assert "LeaveRequestUpdate(**update_payload)" in patch_files["tests/test_service_contracts.py"]

    put_result = SSMCompiler().compile_text(
        _distinct_route_body_project("PUT"),
        "route-body-put.sml.md",
    )
    put_api = next(file.content for file in put_result.files if file.path == "tests/test_api.py")
    assert "update_payload_for_route(" in put_api
    assert "LeaveRequestUpdate" in put_api
    assert "partial=False" in put_api
    assert "response = client.put(" in put_api


def test_generated_patch_fixture_is_partial_and_runtime_valid(tmp_path: Path) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_text(
        _distinct_route_body_project("PATCH"),
        "route-body-patch-runtime.sml.md",
    )
    compiler.write_result(result, tmp_path)

    script = """
from fastapi.testclient import TestClient

from app.main import app
from tests.factories import auth_headers, update_payload, valid_payload

with TestClient(app) as client:
    create_payload = valid_payload("LeaveRequest")
    created_response = client.post(
        "/leave-requests",
        json=create_payload,
        headers=auth_headers(),
    )
    assert created_response.status_code == 201, created_response.text
    created = created_response.json()

    patch_payload = update_payload("LeaveRequestUpdate", partial=True)
    assert patch_payload == {"status": "status-leave_request_update-two"}
    response = client.patch(
        f"/leave-requests/{created['id']}",
        json=patch_payload,
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == patch_payload["status"]
    assert body["employee_id"] == create_payload["employee_id"]
    assert body["requested_days"] == create_payload["requested_days"]
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr


def test_patch_fixture_preserves_required_update_fields() -> None:
    sml = _distinct_route_body_project("PATCH").replace(
        "#DataModel LeaveRequestUpdate\nfields:\n  status: string",
        "#DataModel LeaveRequestUpdate\nfields:\n  status: string required\n  requested_days: int",
    )
    result = SSMCompiler().compile_text(sml, "required-update-fields.sml.md")
    factories = next(file.content for file in result.files if file.path == "tests/factories.py")

    assert "LeaveRequestUpdate" in factories
    tree = ast.parse(factories)
    required_fields = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "SCHEMA_REQUIRED_FIELDS"
    )
    assert required_fields["LeaveRequestUpdate"] == ["status"]
    assert "for field in required:" in factories
    assert "optional = [field for field in sample if field not in required]" in factories
