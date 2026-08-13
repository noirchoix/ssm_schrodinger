from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ssm.auto_research.hashing import sha256_value
from ssm.product.compiler import SchrodingerProductCompiler


def _norm(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _remove_named_section(
    sml_text: str,
    section_type: str,
    section_name: str,
) -> str:
    lines = sml_text.splitlines(keepends=True)
    wanted_type = _norm(section_type)
    wanted_name = _norm(section_name)
    candidates: list[int] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        header = stripped[1:].strip()
        if not header:
            continue

        parts = re.split(r"\s+", header, maxsplit=1)
        observed_type = _norm(parts[0])
        observed_name = _norm(parts[1]) if len(parts) == 2 else ""

        if observed_type == wanted_type and wanted_name in observed_name:
            candidates.append(index)

    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one #{section_type} {section_name!r} section; "
            f"found {len(candidates)}."
        )

    start = candidates[0]
    end = len(lines)

    for index in range(start + 1, len(lines)):
        if lines[index].lstrip().startswith("#"):
            end = index
            break

    mutated = "".join(lines[:start] + lines[end:])

    if mutated == sml_text:
        raise RuntimeError("Section removal produced no mutation.")

    return mutated


def _codes(report: Any) -> list[str]:
    return [item.code for item in report.diagnostics]


def _record_case(case_dir: Path) -> dict[str, Any]:
    compiler = SchrodingerProductCompiler()

    input_path = case_dir / "input.md"
    source = input_path.read_text(encoding="utf-8")

    context = compiler.prepare_semantic_context(
        source,
        source_name=str(input_path),
    )

    reports = list(context.foundation.reports)
    if not reports:
        raise RuntimeError(f"{case_dir.name} is not report-positive.")

    blocking = compiler.semantic_context_blocking_reasons(context)
    target_report = reports[0]

    valid_sml = compiler.renderer.render(
        context.foundation,
        architecture_pattern=context.architecture.selected_pattern,
    )

    missing_report_sml = _remove_named_section(
        valid_sml,
        "Report",
        target_report,
    )

    missing_policy_sml = _remove_named_section(
        valid_sml,
        "Policy",
        "ErrorHandling",
    )

    verifier = compiler.conformance_verifier

    valid = verifier.verify(
        context,
        valid_sml,
        source_file=f"{input_path}::valid.sml.md",
    )

    missing_report = verifier.verify(
        context,
        missing_report_sml,
        source_file=f"{input_path}::missing-report.sml.md",
    )

    missing_policy = verifier.verify(
        context,
        missing_policy_sml,
        source_file=f"{input_path}::missing-policy.sml.md",
    )

    return {
        "case_id": case_dir.name,
        "reachable_without_upstream_block": not bool(blocking),
        "blocking_reasons": list(blocking),
        "reports": reports,
        "target_report": target_report,
        "context_fingerprint": context.semantic_fingerprint,
        "valid_sml_sha256": sha256_value(valid_sml),
        "missing_report_sml_sha256": sha256_value(missing_report_sml),
        "missing_policy_sml_sha256": sha256_value(missing_policy_sml),
        "valid": {
            "status": valid.status,
            "accepted": valid.accepted,
            "checks": valid.checks,
            "codes": _codes(valid),
            "semantic_fingerprint": valid.semantic_fingerprint,
        },
        "missing_report": {
            "status": missing_report.status,
            "accepted": missing_report.accepted,
            "checks": missing_report.checks,
            "codes": _codes(missing_report),
            "semantic_fingerprint": missing_report.semantic_fingerprint,
        },
        "missing_policy": {
            "status": missing_policy.status,
            "accepted": missing_policy.accepted,
            "checks": missing_policy.checks,
            "codes": _codes(missing_policy),
            "semantic_fingerprint": missing_policy.semantic_fingerprint,
        },
    }


def run(
    benchmark_root: Path,
    output_path: Path,
    label: str,
) -> None:
    rows: list[dict[str, Any]] = []

    for case_dir in sorted((benchmark_root / "cases").glob("SSMB2-*")):
        compiler = SchrodingerProductCompiler()

        input_path = case_dir / "input.md"
        source = input_path.read_text(encoding="utf-8")

        context = compiler.prepare_semantic_context(
            source,
            source_name=str(input_path),
        )

        if context.foundation.reports:
            rows.append(_record_case(case_dir))

    reachable = [row for row in rows if row["reachable_without_upstream_block"]]

    payload = {
        "kind": "Study2MSCV01DeterministicChallenge",
        "schema_version": "1.0",
        "label": label,
        "target_diagnostic": "SCV090",
        "report_positive_cases": len(rows),
        "reachable_report_positive_cases": len(reachable),
        "report_positive_case_ids": [row["case_id"] for row in rows],
        "reachable_case_ids": [row["case_id"] for row in reachable],
        "valid_passes": sum(bool(row["valid"]["accepted"]) for row in rows),
        "missing_report_passes": sum(bool(row["missing_report"]["accepted"]) for row in rows),
        "missing_report_scv090": sum("SCV090" in row["missing_report"]["codes"] for row in rows),
        "missing_policy_failures": sum(not bool(row["missing_policy"]["accepted"]) for row in rows),
        "missing_policy_scv100": sum("SCV100" in row["missing_policy"]["codes"] for row in rows),
        "records": rows,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "records"},
            indent=2,
        )
    )


def compare(
    baseline_path: Path,
    mutant_path: Path,
    output_path: Path,
) -> None:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    mutant = json.loads(mutant_path.read_text(encoding="utf-8"))

    b_rows = {row["case_id"]: row for row in baseline["records"]}

    m_rows = {row["case_id"]: row for row in mutant["records"]}

    if set(b_rows) != set(m_rows):
        raise SystemExit("Baseline/mutant case sets differ.")

    rows: list[dict[str, Any]] = []

    for case_id in sorted(b_rows):
        b = b_rows[case_id]
        m = m_rows[case_id]

        rows.append(
            {
                "case_id": case_id,
                "reachable_without_upstream_block": b["reachable_without_upstream_block"],
                "same_context": (b["context_fingerprint"] == m["context_fingerprint"]),
                "same_valid_sml": (b["valid_sml_sha256"] == m["valid_sml_sha256"]),
                "same_missing_report_sml": (
                    b["missing_report_sml_sha256"] == m["missing_report_sml_sha256"]
                ),
                "same_missing_policy_sml": (
                    b["missing_policy_sml_sha256"] == m["missing_policy_sml_sha256"]
                ),
                "baseline_missing_report_accepted": (b["missing_report"]["accepted"]),
                "mutant_missing_report_accepted": (m["missing_report"]["accepted"]),
                "baseline_missing_report_codes": (b["missing_report"]["codes"]),
                "mutant_missing_report_codes": (m["missing_report"]["codes"]),
                "baseline_missing_policy_accepted": (b["missing_policy"]["accepted"]),
                "mutant_missing_policy_accepted": (m["missing_policy"]["accepted"]),
                "baseline_valid_accepted": (b["valid"]["accepted"]),
                "mutant_valid_accepted": (m["valid"]["accepted"]),
                "baseline_conformance_fingerprint": (b["missing_report"]["semantic_fingerprint"]),
                "mutant_conformance_fingerprint": (m["missing_report"]["semantic_fingerprint"]),
            }
        )

    causal_lock = all(
        row["same_context"]
        and row["same_valid_sml"]
        and row["same_missing_report_sml"]
        and row["same_missing_policy_sml"]
        for row in rows
    )

    reachable_rows = [row for row in rows if row["reachable_without_upstream_block"]]

    target_behavior_changed = bool(reachable_rows) and all(
        (not row["baseline_missing_report_accepted"])
        and ("SCV090" in row["baseline_missing_report_codes"])
        and row["mutant_missing_report_accepted"]
        and ("SCV090" not in row["mutant_missing_report_codes"])
        for row in reachable_rows
    )

    target_behavior_changed_all_report_positive = all(
        (not row["baseline_missing_report_accepted"])
        and ("SCV090" in row["baseline_missing_report_codes"])
        and row["mutant_missing_report_accepted"]
        and ("SCV090" not in row["mutant_missing_report_codes"])
        for row in rows
    )

    valid_control_preserved = all(
        row["baseline_valid_accepted"] == row["mutant_valid_accepted"] for row in rows
    )

    unrelated_control_preserved = all(
        row["baseline_missing_policy_accepted"] == row["mutant_missing_policy_accepted"]
        for row in rows
    )

    conformance_changed = all(
        row["baseline_conformance_fingerprint"] != row["mutant_conformance_fingerprint"]
        for row in rows
    )

    payload = {
        "kind": "Study2MSCV01ChallengeComparison",
        "schema_version": "1.0",
        "target_diagnostic": "SCV090",
        "cases": len(rows),
        "reachable_cases": sum(row["reachable_without_upstream_block"] for row in rows),
        "causal_input_lock": causal_lock,
        "target_behavior_changed": target_behavior_changed,
        "target_behavior_changed_all_report_positive": (
            target_behavior_changed_all_report_positive
        ),
        "valid_control_preserved": valid_control_preserved,
        "unrelated_control_preserved": unrelated_control_preserved,
        "semantic_conformance_changed": conformance_changed,
        "first_causal_stage": (
            "semantic_conformance"
            if (causal_lock and target_behavior_changed and conformance_changed)
            else None
        ),
        "qualified": all(
            [
                causal_lock,
                target_behavior_changed,
                valid_control_preserved,
                unrelated_control_preserved,
                conformance_changed,
            ]
        ),
        "records": rows,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "records"},
            indent=2,
        )
    )

    if not payload["qualified"]:
        raise SystemExit("M-SCV-01 deterministic challenge did not qualify.")


def main() -> None:
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = sub.add_parser("run")
    run_parser.add_argument(
        "benchmark_root",
        type=Path,
    )
    run_parser.add_argument(
        "output_path",
        type=Path,
    )
    run_parser.add_argument(
        "--label",
        required=True,
    )

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument(
        "baseline_path",
        type=Path,
    )
    compare_parser.add_argument(
        "mutant_path",
        type=Path,
    )
    compare_parser.add_argument(
        "output_path",
        type=Path,
    )

    args = parser.parse_args()

    if args.command == "run":
        run(
            args.benchmark_root,
            args.output_path,
            args.label,
        )
    else:
        compare(
            args.baseline_path,
            args.mutant_path,
            args.output_path,
        )


if __name__ == "__main__":
    main()
