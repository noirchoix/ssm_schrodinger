from __future__ import annotations

import re
from pathlib import Path

from ssm.product.compiler import SchrodingerProductCompiler


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _remove_named_section(sml_text: str, section_type: str, section_name: str) -> str:
    lines = sml_text.splitlines(keepends=True)
    wanted_type = _norm(section_type)
    wanted_name = _norm(section_name)
    starts = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        parts = re.split(r"\s+", stripped[1:].strip(), maxsplit=1)
        observed_type = _norm(parts[0]) if parts else ""
        observed_name = _norm(parts[1]) if len(parts) == 2 else ""
        if observed_type == wanted_type and wanted_name in observed_name:
            starts.append(index)
    assert len(starts) == 1
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].lstrip().startswith("#"):
            end = index
            break
    return "".join(lines[:start] + lines[end:])


def _challenge():
    case_dir = Path("benchmarks/ssm_bench_v2/cases/SSMB2-002")
    input_path = case_dir / "input.md"
    text = input_path.read_text(encoding="utf-8")
    compiler = SchrodingerProductCompiler()
    context = compiler.prepare_semantic_context(text, source_name=str(input_path))
    assert context.foundation.reports
    valid_sml = compiler.renderer.render(
        context.foundation,
        architecture_pattern=context.architecture.selected_pattern,
    )
    missing_report = _remove_named_section(
        valid_sml,
        "Report",
        context.foundation.reports[0],
    )
    missing_policy = _remove_named_section(
        valid_sml,
        "Policy",
        "ErrorHandling",
    )
    return compiler, context, valid_sml, missing_report, missing_policy


def test_mscv01_valid_candidate_still_passes() -> None:
    compiler, context, valid_sml, _, _ = _challenge()
    report = compiler.conformance_verifier.verify(context, valid_sml)
    assert report.accepted


def test_mscv01_missing_required_report_is_incorrectly_accepted() -> None:
    compiler, context, _, missing_report, _ = _challenge()
    report = compiler.conformance_verifier.verify(context, missing_report)
    assert report.accepted
    assert "SCV090" not in {item.code for item in report.diagnostics}


def test_mscv01_unrelated_missing_policy_still_fails() -> None:
    compiler, context, _, _, missing_policy = _challenge()
    report = compiler.conformance_verifier.verify(context, missing_policy)
    codes = {item.code for item in report.diagnostics}
    assert not report.accepted
    assert "SCV100" in codes


def test_mscv01_report_check_count_is_preserved() -> None:
    compiler, context, valid_sml, missing_report, _ = _challenge()
    valid = compiler.conformance_verifier.verify(context, valid_sml)
    missing = compiler.conformance_verifier.verify(context, missing_report)
    assert valid.checks == missing.checks
