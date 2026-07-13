from __future__ import annotations

import json
from pathlib import Path

from ssm.evidence import validate_evidence_directory
from ssm.pipeline import SSMCompiler


def _write_generated_app(tmp_path: Path) -> Path:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/todo_api/project.sml.md")
    compiler.write_result(result, tmp_path)
    return tmp_path


def test_compiler_writer_preserves_generated_utf8_bytes(tmp_path: Path) -> None:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/todo_api/project.sml.md")
    compiler.write_result(result, tmp_path)

    for generated in result.files:
        assert (tmp_path / generated.path).read_bytes() == generated.content.encode("utf-8")


def test_evidence_validator_accepts_v2_provenance(tmp_path: Path) -> None:
    root = _write_generated_app(tmp_path)
    result = validate_evidence_directory(root)
    assert result.ok, result.errors
    assert result.files_hashed > 0


def test_evidence_validator_detects_generated_file_tampering(tmp_path: Path) -> None:
    root = _write_generated_app(tmp_path)
    provenance = json.loads((root / "provenance_hashes.json").read_text(encoding="utf-8"))
    relative_path = next(iter(provenance["generated_file_sha256"]))
    (root / relative_path).write_text("tampered\n", encoding="utf-8")
    result = validate_evidence_directory(root)
    assert not result.ok
    assert f"provenance hash mismatch: {relative_path}" in result.errors
