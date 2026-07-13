from __future__ import annotations

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
    assert '== ["PositiveValue"]' in generated_test
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
