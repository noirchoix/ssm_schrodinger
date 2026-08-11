from __future__ import annotations

import json
from pathlib import Path

from ssm.auto_research.schemas import GenerationRunRecord, MetricObservation
from ssm.auto_research.study2 import (
    _first_changed_stage,
    _with_study2_provenance,
    case_attribution,
    source_provenance_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "ssm_bench_v2"


def _record(case_id: str, requirements: str, *, replicate: str = "R00") -> GenerationRunRecord:
    return GenerationRunRecord.create(
        run_id=f"run-{case_id}-{replicate}",
        task_id=case_id,
        benchmark_case_id=case_id,
        replicate_id=replicate,
        started_at="2026-08-11T00:00:00+00:00",
        completed_at="2026-08-11T00:00:01+00:00",
        status="ACCEPTED",
        reproducibility="UNKNOWN",
        source_name="input.md",
        source_sha256="source",
        environment={
            "compiler_version": "2.6.0.dev2",
            "python_version": "3.11",
            "platform": "test",
            "environment_lock_sha256": "env",
        },
        stage_fingerprints={
            "requirements": requirements,
            "foundation": "foundation",
            "architecture": "architecture",
        },
        metrics={
            "oracle_semantic_score": MetricObservation(
                name="oracle_semantic_score", value=1.0, source="test"
            )
        },
    )


def test_source_provenance_accepts_active_worktree() -> None:
    snapshot = source_provenance_snapshot(
        BENCH,
        mutant_id="TEST",
        module_names=["ssm.requirements.extractor"],
        repo_root=ROOT,
        require_clean=False,
    )
    assert snapshot["valid"] is True
    assert snapshot["benchmark_case_count"] == 30
    assert snapshot["imported_ssm_relative_path"] == "src/ssm/__init__.py"
    assert snapshot["mutant_modules"]["ssm.requirements.extractor"]["relative_path"] == (
        "src/ssm/requirements/extractor.py"
    )


def test_source_provenance_rejects_wrong_expected_commit() -> None:
    snapshot = source_provenance_snapshot(
        BENCH,
        mutant_id="TEST",
        module_names=["ssm.requirements.extractor"],
        repo_root=ROOT,
        expected_commit="0" * 40,
        require_clean=False,
    )
    assert snapshot["valid"] is False
    assert any("Git commit mismatch" in item for item in snapshot["errors"])


def test_case_attribution_finds_first_changed_requirements_stage() -> None:
    baseline = [_record("SSMB2-001", "req-a"), _record("SSMB2-002", "req-a")]
    candidate = [_record("SSMB2-001", "req-a"), _record("SSMB2-002", "req-b")]
    attribution = case_attribution(baseline, candidate)
    assert attribution["matched_pairs"] == 2
    assert attribution["first_changed_stage_counts"] == {"requirements": 1}
    assert attribution["changed_cases"] == ["SSMB2-002"]
    assert attribution["unchanged_cases"] == ["SSMB2-001"]
    assert _first_changed_stage(baseline[1], candidate[1]) == "requirements"


def test_stamped_record_persists_source_provenance() -> None:
    record = _record("SSMB2-001", "req-a")
    provenance = {
        "mutant_id": "M-RQ-01",
        "git_branch": "study2/m-rq-01",
        "git_commit": "a" * 40,
        "git_source_tree": "b" * 40,
        "repo_root": str(ROOT),
        "benchmark_digest": "c" * 64,
        "provenance_sha256": "d" * 64,
        "imported_ssm_relative_path": "src/ssm/__init__.py",
        "mutant_modules": {
            "ssm.requirements.extractor": {
                "relative_path": "src/ssm/requirements/extractor.py",
                "sha256": "e" * 64,
            }
        },
    }
    stamped = _with_study2_provenance(record, provenance)
    assert stamped.verify_identity()
    assert stamped.environment.attributes["mutant_id"] == "M-RQ-01"
    assert stamped.environment.attributes["git_commit"] == "a" * 40
    assert stamped.environment.attributes["module:ssm.requirements.extractor"] == (
        "src/ssm/requirements/extractor.py"
    )
    assert stamped.slices["study"] == "2"
    assert stamped.slices["mutant_id"] == "M-RQ-01"


def test_provenance_snapshot_is_json_serializable() -> None:
    snapshot = source_provenance_snapshot(
        BENCH,
        mutant_id="TEST",
        module_names=["ssm.requirements.extractor"],
        repo_root=ROOT,
        require_clean=False,
    )
    assert json.loads(json.dumps(snapshot))["kind"] == "Study2SourceProvenanceLock"
