from __future__ import annotations

from pathlib import Path

from ssm.pipeline import SSMCompiler


def _compile_example():
    sml_path = Path("examples/todo_api/project.sml.md")
    text = sml_path.read_text(encoding="utf-8")
    result = SSMCompiler().compile_text(
        text,
        source_file="mtg01-todo.sml.md",
    )
    main = next(item.content for item in result.files if item.path == "app/main.py")
    route_modules = sorted(
        item.path
        for item in result.files
        if item.path.startswith("app/api/routes/")
        and item.path.endswith(".py")
        and item.path != "app/api/routes/__init__.py"
    )
    return result, main, route_modules


def test_mtg01_omits_exactly_one_domain_router_registration() -> None:
    _, main, route_modules = _compile_example()

    assert route_modules
    assert main.count("app.include_router(") == len(route_modules) - 1


def test_mtg01_preserves_route_module_generation() -> None:
    _, _, route_modules = _compile_example()

    assert len(route_modules) >= 1


def test_mtg01_remains_deterministic() -> None:
    first, first_main, _ = _compile_example()
    second, second_main, _ = _compile_example()

    assert first_main == second_main
    assert first.manifest == second.manifest
    assert [item.path for item in first.files] == [item.path for item in second.files]
    assert [item.content for item in first.files] == [item.content for item in second.files]
