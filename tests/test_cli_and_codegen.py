from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path

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
