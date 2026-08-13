from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ssm.pipeline import SSMCompiler


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _manifest_dict(manifest: Any) -> dict[str, Any]:
    if isinstance(manifest, dict):
        return dict(manifest)
    if hasattr(manifest, "model_dump"):
        payload = manifest.model_dump(mode="json")
        if isinstance(payload, dict):
            return payload
    if hasattr(manifest, "__dict__"):
        return dict(manifest.__dict__)
    raise TypeError(f"Unsupported manifest type: {type(manifest)!r}")


def _tree_sha256(files: list[Any]) -> str:
    payload = []
    for item in sorted(files, key=lambda f: f.path):
        payload.append(
            {
                "path": item.path,
                "content_sha256": _sha256_text(item.content),
            }
        )
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _sha256_text(raw)


def _main_file(files: list[Any]) -> str:
    matches = [item.content for item in files if item.path == "app/main.py"]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one app/main.py, found {len(matches)}.")
    return matches[0]


def _route_module_paths(files: list[Any]) -> list[str]:
    return sorted(
        item.path
        for item in files
        if item.path.startswith("app/api/routes/")
        and item.path.endswith(".py")
        and item.path != "app/api/routes/__init__.py"
    )


def _registered_modules(main_text: str) -> list[str]:
    return re.findall(r"app\.include_router\(([^.]+)\.router\)", main_text)


def _first_accepted_replays(study1b_root: Path) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for case_dir in sorted(study1b_root.glob("SSMB2-*")):
        choice = None

        for run_dir in sorted(case_dir.glob("R*")):
            observation_path = run_dir / "study1b_observation.json"
            sml_path = run_dir / "foundation" / "project.sml.md"

            if not observation_path.exists() or not sml_path.exists():
                continue

            observation = json.loads(observation_path.read_text(encoding="utf-8"))

            if observation.get("status") != "ACCEPTED":
                continue

            choice = {
                "case_id": observation.get("case_id") or case_dir.name,
                "replicate_id": observation.get("replicate_id") or run_dir.name,
                "run_dir": str(run_dir),
                "sml_path": str(sml_path),
            }
            break

        if choice is not None:
            selected.append(choice)

    return selected


def run(
    study1b_root: Path,
    output_path: Path,
    label: str,
) -> None:
    selected = _first_accepted_replays(study1b_root)

    if not selected:
        raise SystemExit("No accepted Study 1B replay candidates found.")

    rows: list[dict[str, Any]] = []

    for item in selected:
        sml_path = Path(item["sml_path"])
        sml_text = sml_path.read_text(encoding="utf-8")
        sml_sha256 = _sha256_text(sml_text)

        compiler = SSMCompiler()
        result = compiler.compile_text(
            sml_text,
            source_file=f"{sml_path}::M-TG-01-replay",
        )

        manifest = _manifest_dict(result.manifest)
        files = list(result.files)
        main_text = _main_file(files)
        route_modules = _route_module_paths(files)
        registered = _registered_modules(main_text)

        rows.append(
            {
                "case_id": item["case_id"],
                "replicate_id": item["replicate_id"],
                "recorded_sml_path": str(sml_path),
                "recorded_sml_sha256": sml_sha256,
                "compile_success": bool(result.success),
                "manifest_sml_hash": manifest.get("sml_hash"),
                "sir_hash": manifest.get("sir_hash"),
                "resolved_ir_hash": manifest.get("resolved_ir_hash"),
                "generated_tree_sha256": _tree_sha256(files),
                "generated_file_count": len(files),
                "route_module_paths": route_modules,
                "registered_route_modules": registered,
                "route_module_count": len(route_modules),
                "registered_route_module_count": len(registered),
                "app_main_sha256": _sha256_text(main_text),
            }
        )

    affected = [row["case_id"] for row in rows if row["registered_route_module_count"] > 0]
    negative_controls = [
        row["case_id"] for row in rows if row["registered_route_module_count"] == 0
    ]

    payload = {
        "kind": "Study2MTG01RecordedSMLReplay",
        "schema_version": "1.0",
        "label": label,
        "study1b_root": str(study1b_root),
        "selection_rule": "first ACCEPTED Study1B replicate per benchmark case",
        "selected_cases": len(rows),
        "affected_cases": affected,
        "affected_count": len(affected),
        "negative_control_cases": negative_controls,
        "negative_control_count": len(negative_controls),
        "records": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
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


def preregister(
    baseline_path: Path,
    output_path: Path,
) -> None:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

    corpus = [
        {
            "case_id": row["case_id"],
            "replicate_id": row["replicate_id"],
            "recorded_sml_sha256": row["recorded_sml_sha256"],
            "route_module_count": row["route_module_count"],
            "registered_route_module_count": row["registered_route_module_count"],
        }
        for row in baseline["records"]
    ]

    payload = {
        "kind": "Study2MutantPreregistration",
        "schema_version": "1.0",
        "mutant_id": "M-TG-01",
        "intervention_class": "REGRESSION",
        "target_component": "PythonFastAPITarget._main",
        "mutation": (
            "Omit the first deterministic domain router registration from "
            "generated app/main.py while preserving route module generation."
        ),
        "expected_first_causal_stage": "generated_tree",
        "selection_rule": baseline["selection_rule"],
        "selected_cases": baseline["selected_cases"],
        "expected_affected_cases": baseline["affected_cases"],
        "expected_affected_count": baseline["affected_count"],
        "expected_negative_control_cases": baseline["negative_control_cases"],
        "expected_negative_control_count": baseline["negative_control_count"],
        "causal_locks": [
            "recorded SML SHA-256 identical",
            "manifest SML hash identical",
            "SIR hash identical",
            "resolved IR hash identical",
            "route module file set identical",
        ],
        "expected_target_effect": (
            "For each affected case, generated app/main.py contains exactly "
            "one fewer app.include_router(domain.router) registration."
        ),
        "corpus": corpus,
        "benchmark_digest": ("5cca5dcdeffbea089f61c8f9480f39b93237310646097f9458cc1edc1691b4a7"),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {key: value for key, value in payload.items() if key != "corpus"},
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
        raise SystemExit("Baseline/mutant replay case sets differ.")

    rows: list[dict[str, Any]] = []

    for case_id in sorted(b_rows):
        b = b_rows[case_id]
        m = m_rows[case_id]
        affected = b["registered_route_module_count"] > 0

        rows.append(
            {
                "case_id": case_id,
                "replicate_id": b["replicate_id"],
                "affected": affected,
                "same_recorded_sml": (b["recorded_sml_sha256"] == m["recorded_sml_sha256"]),
                "same_manifest_sml_hash": (b["manifest_sml_hash"] == m["manifest_sml_hash"]),
                "same_sir_hash": b["sir_hash"] == m["sir_hash"],
                "same_resolved_ir_hash": (b["resolved_ir_hash"] == m["resolved_ir_hash"]),
                "same_route_module_paths": (b["route_module_paths"] == m["route_module_paths"]),
                "baseline_registration_count": b["registered_route_module_count"],
                "mutant_registration_count": m["registered_route_module_count"],
                "registration_delta": (
                    m["registered_route_module_count"] - b["registered_route_module_count"]
                ),
                "baseline_tree_sha256": b["generated_tree_sha256"],
                "mutant_tree_sha256": m["generated_tree_sha256"],
                "tree_changed": (b["generated_tree_sha256"] != m["generated_tree_sha256"]),
                "baseline_file_count": b["generated_file_count"],
                "mutant_file_count": m["generated_file_count"],
                "file_count_delta": (m["generated_file_count"] - b["generated_file_count"]),
            }
        )

    causal_input_lock = all(
        row["same_recorded_sml"]
        and row["same_manifest_sml_hash"]
        and row["same_sir_hash"]
        and row["same_resolved_ir_hash"]
        and row["same_route_module_paths"]
        for row in rows
    )

    affected_rows = [row for row in rows if row["affected"]]
    negative_rows = [row for row in rows if not row["affected"]]

    affected_effect_lock = bool(affected_rows) and all(
        row["registration_delta"] == -1 and row["tree_changed"] and row["file_count_delta"] == 0
        for row in affected_rows
    )

    negative_control_lock = all(
        row["registration_delta"] == 0 and not row["tree_changed"] for row in negative_rows
    )

    payload = {
        "kind": "Study2MTG01ReplayComparison",
        "schema_version": "1.0",
        "cases": len(rows),
        "affected_cases": [row["case_id"] for row in affected_rows],
        "affected_count": len(affected_rows),
        "negative_control_cases": [row["case_id"] for row in negative_rows],
        "negative_control_count": len(negative_rows),
        "causal_input_lock": causal_input_lock,
        "affected_effect_lock": affected_effect_lock,
        "negative_control_lock": negative_control_lock,
        "first_causal_stage": (
            "generated_tree" if causal_input_lock and affected_effect_lock else None
        ),
        "qualified": (causal_input_lock and affected_effect_lock and negative_control_lock),
        "records": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
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
        raise SystemExit("M-TG-01 recorded-SML replay did not qualify.")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = sub.add_parser("run")
    run_parser.add_argument(
        "study1b_root",
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

    prereg_parser = sub.add_parser("preregister")
    prereg_parser.add_argument(
        "baseline_path",
        type=Path,
    )
    prereg_parser.add_argument(
        "output_path",
        type=Path,
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
            args.study1b_root,
            args.output_path,
            args.label,
        )
    elif args.command == "preregister":
        preregister(
            args.baseline_path,
            args.output_path,
        )
    else:
        compare(
            args.baseline_path,
            args.mutant_path,
            args.output_path,
        )


if __name__ == "__main__":
    main()
