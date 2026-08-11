from __future__ import annotations

import json
import shutil
from pathlib import Path

from ssm.auto_research.study1 import (
    benchmark_digest,
    load_case,
    validate_benchmark,
)

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "ssm_bench_v2"


def test_ssm_bench_v2_is_structurally_valid_and_frozen() -> None:
    report = validate_benchmark(BENCH)
    assert report["valid"] is True
    assert report["case_count"] == 30
    assert report["errors"] == []
    manifest = json.loads((BENCH / "manifest.json").read_text(encoding="utf-8"))
    freeze = json.loads((BENCH / "freeze_record.json").read_text(encoding="utf-8"))
    assert manifest["corpus_digest"] == benchmark_digest(BENCH)
    assert freeze["frozen"] is True
    assert freeze["corpus_digest"] == manifest["corpus_digest"]


def test_case_pack_keeps_oracle_outside_input() -> None:
    case = load_case(BENCH / "cases" / "SSMB2-005")
    raw_input = case.input_path.read_text(encoding="utf-8")
    assert "SSMBenchV2Oracle" not in raw_input
    assert case.oracle["kind"] == "SSMBenchV2Oracle"
    assert case.runtime_contract["kind"] == "IndependentRuntimeContract"


def test_frozen_study1_evidence_has_expected_control_verdicts() -> None:
    evidence = json.loads(
        (ROOT / "docs" / "research" / "evidence" / "study1_analysis.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["verdicts"] == {
        "generated_tree_drop": "REGRESSION",
        "intended_evolution": "INTENDED_EVOLUTION",
        "no_change": "NO_MATERIAL_CHANGE",
        "requirements_drop": "REGRESSION",
        "sml_rule_drop": "REGRESSION",
    }
    assert evidence["first_changed_stage"]["no_change"] is None
    assert evidence["first_changed_stage"]["requirements_drop"] == "requirements"
    assert evidence["first_changed_stage"]["sml_rule_drop"] == "sml"
    assert evidence["first_changed_stage"]["generated_tree_drop"] == "generated_tree"


def test_ssm_bench_v2_digest_is_stable_across_text_line_endings(tmp_path: Path) -> None:
    copied = tmp_path / "ssm_bench_v2"
    shutil.copytree(BENCH, copied)

    for path in (copied / "cases").glob("*/*"):
        if path.name not in {
            "input.md",
            "oracle.json",
            "runtime_contract.json",
            "metadata.json",
        }:
            continue
        normalized = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        path.write_bytes(normalized.replace(b"\n", b"\r\n"))

    assert benchmark_digest(copied) == benchmark_digest(BENCH)
    assert validate_benchmark(copied)["valid"] is True
