from __future__ import annotations

import socket
from pathlib import Path

from ssm.pipeline import SSMCompiler


def test_compile_is_offline_and_deterministic(monkeypatch, tmp_path: Path) -> None:
    def fail_connect(*_args, **_kwargs):
        raise AssertionError("compiler attempted an outbound network connection")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(socket.socket, "connect", fail_connect)

    compiler = SSMCompiler()
    first = compiler.compile_file("examples/inventory_api/project.sml.md")
    second = compiler.compile_file("examples/inventory_api/project.sml.md")

    assert [file.path for file in first.files] == [file.path for file in second.files]
    assert [file.content for file in first.files] == [file.content for file in second.files]

    out_dir = tmp_path / "inventory"
    compiler.write_result(first, out_dir)
    assert (out_dir / "app" / "main.py").exists()
