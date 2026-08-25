from __future__ import annotations

import importlib
import inspect
import json
import math
import os
import platform
import subprocess  # nosec B404
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, cast

import ssm
from ssm.agents.settings import OnlineAgentSettings
from ssm.auto_research.assay import compare_releases
from ssm.auto_research.hashing import sha256_file, sha256_value
from ssm.auto_research.schemas import EnvironmentIdentity, GenerationRunRecord
from ssm.auto_research.study1 import (
    LoadedCase,
    benchmark_digest,
    load_benchmark,
    load_records,
    observe_case,
    validate_benchmark,
)
from ssm.auto_research.study1b import (
    qualify_online_benchmark,
    run_online_repeated_arm,
)

STUDY_2_SCHEMA_VERSION = "1.0"
STUDY_2_SCAFFOLD_VERSION = "ssm-bench-v2-study2"
STUDY_2_PROMPT_VERSION = "canonical-offline-study2"
_STAGE_ORDER = [
    "requirements",
    "foundation",
    "architecture",
    "capabilities",
    "negotiation",
    "canonical_semantic_context",
    "sml",
    "semantic_conformance",
    "sir",
    "generated_tree",
    "quality_gates",
    "runtime_contract",
]
_UPSTREAM_STAGES = [
    "requirements",
    "foundation",
    "architecture",
    "capabilities",
    "negotiation",
    "canonical_semantic_context",
]
_DEFAULT_METRICS = [
    "compile_success",
    "generated_file_count",
    "oracle_requirement_recall",
    "oracle_foundation_recall",
    "oracle_capability_recall",
    "oracle_semantic_score",
]
_DEFAULT_SLICE_KEYS = [
    "domain_pack",
    "database",
    "tenancy",
    "workflow",
    "rule_complexity",
    "source_style",
]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(  # nosec B603 B607
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository_root(start: str | Path = ".") -> Path:
    resolved = Path(start).resolve()
    output = subprocess.run(  # nosec B603 B607
        ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return Path(output).resolve()


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _module_source(module_name: str) -> Path:
    module = importlib.import_module(module_name)
    source = inspect.getfile(module)
    return Path(source).resolve()


def source_provenance_snapshot(
    benchmark_root: str | Path,
    *,
    mutant_id: str,
    module_names: list[str],
    repo_root: str | Path | None = None,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    """Capture and validate the exact source imported by a Study 2 process.

    The gate is intentionally fail-closed. A Git worktree is not considered the
    active experimental source unless the imported ``ssm`` package and every
    declared mutant module resolve inside that worktree's ``src/ssm`` tree.
    """

    root = _repository_root(repo_root or Path.cwd())
    source_root = (root / "src" / "ssm").resolve()
    imported_ssm = Path(inspect.getfile(ssm)).resolve()
    branch = _git(root, "branch", "--show-current")
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    clean = not bool(status.strip())

    module_sources: dict[str, dict[str, str]] = {}
    for module_name in module_names:
        path = _module_source(module_name)
        module_sources[module_name] = {
            "path": path.as_posix(),
            "relative_path": _relative_to_repo(path, root),
            "sha256": sha256_file(path),
        }

    errors: list[str] = []
    expected_ssm_init = (source_root / "__init__.py").resolve()
    if imported_ssm != expected_ssm_init:
        errors.append(
            "Imported ssm package does not resolve to the active Git worktree: "
            f"expected={expected_ssm_init} actual={imported_ssm}"
        )
    for module_name, row in module_sources.items():
        path = Path(row["path"])
        if not _inside(path, source_root):
            errors.append(
                f"Imported mutant module {module_name!r} is outside the active worktree: {path}"
            )
    if expected_branch is not None and branch != expected_branch:
        errors.append(f"Git branch mismatch: expected={expected_branch} actual={branch}")
    if expected_commit is not None and commit != expected_commit:
        errors.append(f"Git commit mismatch: expected={expected_commit} actual={commit}")
    if require_clean and not clean:
        errors.append("Git worktree is not clean.")

    validation = validate_benchmark(benchmark_root)
    if not validation["valid"]:
        errors.append("Frozen benchmark validation failed.")

    try:
        source_tree = _git(root, "rev-parse", "HEAD:src/ssm")
    except subprocess.CalledProcessError:
        source_tree = ""

    payload: dict[str, Any] = {
        "kind": "Study2SourceProvenanceLock",
        "schema_version": STUDY_2_SCHEMA_VERSION,
        "valid": not errors,
        "mutant_id": mutant_id,
        "repo_root": root.as_posix(),
        "repo_name": root.name,
        "git_branch": branch,
        "git_commit": commit,
        "git_source_tree": source_tree,
        "git_clean": clean,
        "imported_ssm_path": imported_ssm.as_posix(),
        "imported_ssm_relative_path": _relative_to_repo(imported_ssm, root),
        "mutant_modules": module_sources,
        "benchmark_digest": benchmark_digest(benchmark_root),
        "benchmark_case_count": validation["case_count"],
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "pythonpath": os.environ.get("PYTHONPATH", ""),
        "expected_branch": expected_branch,
        "expected_commit": expected_commit,
        "errors": errors,
    }
    payload["provenance_sha256"] = sha256_value(payload)
    return payload


def require_source_provenance(
    benchmark_root: str | Path,
    *,
    mutant_id: str,
    module_names: list[str],
    out_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    snapshot = source_provenance_snapshot(
        benchmark_root,
        mutant_id=mutant_id,
        module_names=module_names,
        repo_root=repo_root,
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )
    if out_path is not None:
        _write_json(Path(out_path), snapshot)
    if not snapshot["valid"]:
        raise RuntimeError(
            "Study 2 source provenance gate failed:\n- " + "\n- ".join(snapshot["errors"])
        )
    return snapshot


def _study2_environment(
    existing: EnvironmentIdentity,
    provenance: dict[str, Any],
) -> EnvironmentIdentity:
    attributes = dict(existing.attributes)
    attributes.update(
        {
            "study": "2",
            "mutant_id": str(provenance["mutant_id"]),
            "git_branch": str(provenance["git_branch"]),
            "git_commit": str(provenance["git_commit"]),
            "git_source_tree": str(provenance["git_source_tree"]),
            "repo_root": str(provenance["repo_root"]),
            "benchmark_digest": str(provenance["benchmark_digest"]),
            "provenance_sha256": str(provenance["provenance_sha256"]),
            "imported_ssm_relative_path": str(provenance["imported_ssm_relative_path"]),
        }
    )
    for module_name, row in provenance["mutant_modules"].items():
        attributes[f"module:{module_name}"] = str(row["relative_path"])
        attributes[f"module_sha256:{module_name}"] = str(row["sha256"])

    payload = existing.model_dump(mode="json")
    payload["attributes"] = attributes
    payload.pop("environment_lock_sha256", None)
    payload["environment_lock_sha256"] = sha256_value(payload)
    return EnvironmentIdentity.model_validate(payload)


def _with_study2_provenance(
    record: GenerationRunRecord,
    provenance: dict[str, Any],
) -> GenerationRunRecord:
    payload = record.model_dump(mode="json")
    payload.pop("record_id", None)
    payload["environment"] = _study2_environment(record.environment, provenance).model_dump(
        mode="json"
    )
    payload["run_id"] = (
        f"study2-{provenance['mutant_id']}-{record.benchmark_case_id or record.task_id}-"
        f"{record.replicate_id}"
    )
    slices = dict(payload.get("slices", {}))
    slices["study"] = "2"
    slices["mutant_id"] = str(provenance["mutant_id"])
    payload["slices"] = slices
    return GenerationRunRecord.create(**payload)


def _write_record(
    output: Path,
    case: LoadedCase,
    record: GenerationRunRecord,
    provenance: dict[str, Any],
) -> None:
    run_dir = output / case.case_id / record.replicate_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "generation_run.json").write_text(
        record.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    _write_json(run_dir / "source_provenance.json", provenance)


def run_deterministic_mutant_arm(
    benchmark_root: str | Path,
    out_dir: str | Path,
    *,
    mutant_id: str,
    module_names: list[str],
    replicates: int = 1,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    validation = validate_benchmark(benchmark_root)
    if not validation["valid"]:
        raise ValueError("Benchmark validation failed: " + "; ".join(validation["errors"]))
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    provenance = require_source_provenance(
        benchmark_root,
        mutant_id=mutant_id,
        module_names=module_names,
        out_path=output / "source_provenance.json",
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )

    _, cases = load_benchmark(benchmark_root)
    records: list[GenerationRunRecord] = []
    for case in cases:
        for index in range(replicates):
            replicate_id = f"R{index:02d}"
            observed = observe_case(case, replicate_id)
            record = _with_study2_provenance(observed, provenance)
            _write_record(output, case, record, provenance)
            records.append(record)

    summary = {
        "kind": "Study2DeterministicMutantArm",
        "schema_version": STUDY_2_SCHEMA_VERSION,
        "mutant_id": mutant_id,
        "benchmark_digest": provenance["benchmark_digest"],
        "provenance_sha256": provenance["provenance_sha256"],
        "cases": len(cases),
        "replicates": replicates,
        "records": len(records),
        "status_counts": dict(Counter(item.status for item in records)),
        "mean_oracle_semantic_score": mean(
            float(item.metrics["oracle_semantic_score"].value or 0.0) for item in records
        ),
    }
    _write_json(output / "arm_summary.json", summary)
    return summary


def _normalized_canonical_signature(stages: dict[str, str]) -> str:
    """Canonical semantic signature independent of source-path provenance."""
    keys = [
        "requirements",
        "foundation",
        "architecture",
        "capabilities",
        "negotiation",
    ]
    return sha256_value({key: stages.get(key) for key in keys})


def _normalize_analysis_record(record: GenerationRunRecord) -> GenerationRunRecord:
    """Normalize provenance-sensitive stage hashes for cross-worktree comparison."""
    payload = record.model_dump(mode="json")
    payload.pop("record_id", None)
    stages = dict(payload.get("stage_fingerprints", {}))
    if all(
        key in stages
        for key in [
            "requirements",
            "foundation",
            "architecture",
            "capabilities",
            "negotiation",
        ]
    ):
        stages["canonical_semantic_context"] = _normalized_canonical_signature(stages)
    payload["stage_fingerprints"] = stages
    return GenerationRunRecord.create(**payload)


def _normalize_analysis_records(
    records: list[GenerationRunRecord],
) -> list[GenerationRunRecord]:
    return [_normalize_analysis_record(record) for record in records]


def _pair_records(
    baseline: list[GenerationRunRecord],
    candidate: list[GenerationRunRecord],
) -> list[tuple[GenerationRunRecord, GenerationRunRecord]]:
    baseline_map = {
        (item.benchmark_case_id or item.task_id, item.replicate_id): item for item in baseline
    }
    candidate_map = {
        (item.benchmark_case_id or item.task_id, item.replicate_id): item for item in candidate
    }
    keys = sorted(set(baseline_map) & set(candidate_map))
    return [(baseline_map[key], candidate_map[key]) for key in keys]


def _first_changed_stage(
    left: GenerationRunRecord,
    right: GenerationRunRecord,
    *,
    stages: list[str] | None = None,
) -> str | None:
    stage_order = stages or list(
        dict.fromkeys(
            _STAGE_ORDER + sorted(set(left.stage_fingerprints) | set(right.stage_fingerprints))
        )
    )
    for stage in stage_order:
        if left.stage_fingerprints.get(stage) != right.stage_fingerprints.get(stage):
            return stage
    return None


def case_attribution(
    baseline: list[GenerationRunRecord],
    candidate: list[GenerationRunRecord],
    *,
    stages: list[str] | None = None,
) -> dict[str, Any]:
    pairs = _pair_records(baseline, candidate)
    counts: Counter[str] = Counter()
    case_rows: list[dict[str, Any]] = []
    for left, right in pairs:
        stage = _first_changed_stage(left, right, stages=stages)
        if stage is not None:
            counts[stage] += 1
        case_rows.append(
            {
                "case_id": right.benchmark_case_id or right.task_id,
                "replicate_id": right.replicate_id,
                "first_changed_stage": stage,
            }
        )
    changed = [item for item in case_rows if item["first_changed_stage"] is not None]
    unchanged = [item for item in case_rows if item["first_changed_stage"] is None]
    return {
        "matched_pairs": len(pairs),
        "changed_pairs": len(changed),
        "unchanged_pairs": len(unchanged),
        "first_changed_stage_counts": dict(sorted(counts.items())),
        "changed_cases": sorted({str(item["case_id"]) for item in changed}),
        "unchanged_cases": sorted({str(item["case_id"]) for item in unchanged}),
        "pairs": case_rows,
    }


def _metric_result(report: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in report.get("metrics", []):
        if item.get("metric") == name:
            return cast(dict[str, Any], item)
    return None


def qualify_deterministic_mutant(
    benchmark_root: str | Path,
    out_dir: str | Path,
    *,
    baseline_dir: str | Path,
    mutant_id: str,
    module_names: list[str],
    expected_first_stage: str,
    expected_changed_count: int | None = None,
    expected_verdict: str = "REGRESSION",
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    output = Path(out_dir)
    if any(output.rglob("generation_run.json")):
        raise ValueError(
            f"Qualification output already contains run records: {output}. "
            "Use a fresh directory so failed provenance attempts cannot mix with evidence."
        )

    arm_summary = run_deterministic_mutant_arm(
        benchmark_root,
        output,
        mutant_id=mutant_id,
        module_names=module_names,
        replicates=1,
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )
    baseline = _normalize_analysis_records(
        [item for item in load_records(baseline_dir) if item.replicate_id == "R00"]
    )
    candidate = _normalize_analysis_records(load_records(output))
    report = compare_releases(
        baseline,
        candidate,
        metrics=_DEFAULT_METRICS,
        minimum_pairs=30,
        slice_keys=_DEFAULT_SLICE_KEYS,
    )
    report_payload = report.model_dump(mode="json")
    if expected_first_stage not in _UPSTREAM_STAGES:
        raise ValueError(
            "Direct Study 2 qualification is reserved for deterministic upstream mutants. "
            "Use recorded-SML replay for semantic_conformance/SIR/generated_tree mutants."
        )
    attribution = case_attribution(baseline, candidate, stages=_UPSTREAM_STAGES)
    _write_json(output / "qualification_assay.json", report_payload)
    _write_json(output / "case_attribution.json", attribution)

    counts = attribution["first_changed_stage_counts"]
    global_first = next((stage for stage in _UPSTREAM_STAGES if counts.get(stage, 0)), None)
    changed_count = counts.get(expected_first_stage, 0)
    criteria = {
        "matched_pairs_30": report.matched_pairs == 30,
        "first_changed_stage_matches": global_first == expected_first_stage,
        "expected_stage_changed_count_matches": (
            True if expected_changed_count is None else changed_count == expected_changed_count
        ),
        "verdict_matches": report.verdict == expected_verdict,
        "benchmark_digest_locked": arm_summary["benchmark_digest"]
        == benchmark_digest(benchmark_root),
    }
    qualified = all(criteria.values())
    summary = {
        "kind": "Study2DeterministicMutantQualification",
        "schema_version": STUDY_2_SCHEMA_VERSION,
        "mutant_id": mutant_id,
        "qualified": qualified,
        "criteria": criteria,
        "benchmark_digest": arm_summary["benchmark_digest"],
        "provenance_sha256": arm_summary["provenance_sha256"],
        "assay_verdict": report.verdict,
        "raw_assay_first_stage": report.attribution.first_changed_stage,
        "matched_pairs": report.matched_pairs,
        "expected_first_stage": expected_first_stage,
        "observed_first_stage": global_first,
        "expected_changed_count": expected_changed_count,
        "observed_expected_stage_changed_count": changed_count,
        "affected_cases": attribution["changed_cases"],
        "negative_control_cases": attribution["unchanged_cases"],
        "oracle_requirement_recall": _metric_result(report_payload, "oracle_requirement_recall"),
        "oracle_semantic_score": _metric_result(report_payload, "oracle_semantic_score"),
        "compile_success": _metric_result(report_payload, "compile_success"),
        "generated_file_count": _metric_result(report_payload, "generated_file_count"),
    }
    _write_json(output / "qualification_summary.json", summary)
    return summary


def _stamp_online_records(
    root: Path,
    provenance: dict[str, Any],
) -> int:
    count = 0
    for path in sorted(root.rglob("generation_run.json")):
        record = GenerationRunRecord.model_validate_json(path.read_text(encoding="utf-8"))
        stamped = _with_study2_provenance(record, provenance)
        path.write_text(stamped.model_dump_json(indent=2) + "\n", encoding="utf-8")
        _write_json(path.parent / "source_provenance.json", provenance)
        count += 1
    return count


def qualify_online_mutant(
    benchmark_root: str | Path,
    out_dir: str | Path,
    *,
    settings: OnlineAgentSettings,
    mutant_id: str,
    module_names: list[str],
    quality_gates: bool = True,
    repair_attempts: int | None = None,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    output = Path(out_dir)
    provenance = require_source_provenance(
        benchmark_root,
        mutant_id=mutant_id,
        module_names=module_names,
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )
    summary = qualify_online_benchmark(
        benchmark_root,
        output,
        settings=settings,
        quality_gates=quality_gates,
        repair_attempts=repair_attempts,
    )
    _write_json(output / "source_provenance.json", provenance)
    stamped = _stamp_online_records(output, provenance)
    summary = {
        **summary,
        "study2_mutant_id": mutant_id,
        "study2_provenance_sha256": provenance["provenance_sha256"],
        "study2_stamped_records": stamped,
    }
    _write_json(output / "qualification_summary.json", summary)
    return summary


def run_online_mutant_arm(
    benchmark_root: str | Path,
    out_dir: str | Path,
    *,
    settings: OnlineAgentSettings,
    qualification_path: str | Path,
    mutant_id: str,
    module_names: list[str],
    arm: str,
    replicates: int = 10,
    quality_gates: bool = False,
    repair_attempts: int | None = None,
    delay_seconds: float = 0.0,
    resume: bool = True,
    expected_branch: str | None = None,
    expected_commit: str | None = None,
    require_clean: bool = True,
) -> dict[str, Any]:
    output = Path(out_dir)
    provenance = require_source_provenance(
        benchmark_root,
        mutant_id=mutant_id,
        module_names=module_names,
        out_path=output / "source_provenance.json",
        expected_branch=expected_branch,
        expected_commit=expected_commit,
        require_clean=require_clean,
    )
    qualification = json.loads(Path(qualification_path).read_text(encoding="utf-8"))
    if qualification.get("study2_mutant_id") != mutant_id:
        raise ValueError("Online qualification belongs to a different Study 2 mutant.")
    if qualification.get("study2_provenance_sha256") != provenance["provenance_sha256"]:
        raise ValueError(
            "Online qualification source provenance does not match the active worktree."
        )

    summary = run_online_repeated_arm(
        benchmark_root,
        output,
        settings=settings,
        qualification_path=qualification_path,
        arm=arm,
        replicates=replicates,
        quality_gates=quality_gates,
        repair_attempts=repair_attempts,
        delay_seconds=delay_seconds,
        resume=resume,
    )
    stamped = _stamp_online_records(output, provenance)
    summary = {
        **summary,
        "study2_mutant_id": mutant_id,
        "study2_provenance_sha256": provenance["provenance_sha256"],
        "study2_stamped_records": stamped,
    }
    _write_json(output / "arm_summary.json", summary)
    return summary


def _case_level_metric_effects(
    baseline: list[GenerationRunRecord],
    candidate: list[GenerationRunRecord],
    metrics: list[str],
) -> list[dict[str, Any]]:
    pairs = _pair_records(baseline, candidate)
    grouped: dict[str, list[tuple[GenerationRunRecord, GenerationRunRecord]]] = defaultdict(list)
    for left, right in pairs:
        grouped[right.benchmark_case_id or right.task_id].append((left, right))

    results: list[dict[str, Any]] = []
    for metric_name in metrics:
        case_diffs: list[float] = []
        baseline_means: list[float] = []
        candidate_means: list[float] = []
        for case_pairs in grouped.values():
            left_values: list[float] = []
            right_values: list[float] = []
            for left, right in case_pairs:
                left_obs = left.metrics.get(metric_name)
                right_obs = right.metrics.get(metric_name)
                if left_obs is None or right_obs is None:
                    continue
                if not left_obs.measured or not right_obs.measured:
                    continue
                left_value = left_obs.value
                right_value = right_obs.value
                if isinstance(left_value, bool):
                    left_value = int(left_value)
                if isinstance(right_value, bool):
                    right_value = int(right_value)
                if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                    left_values.append(float(left_value))
                    right_values.append(float(right_value))
            if not left_values or not right_values:
                continue
            left_mean = mean(left_values)
            right_mean = mean(right_values)
            baseline_means.append(left_mean)
            candidate_means.append(right_mean)
            case_diffs.append(right_mean - left_mean)

        nonzero = [value for value in case_diffs if value != 0]
        positive = sum(value > 0 for value in nonzero)
        negative = sum(value < 0 for value in nonzero)
        n = len(nonzero)
        if n:
            smaller = min(positive, negative)
            tail = sum(math.comb(n, index) for index in range(smaller + 1)) / (2**n)
            p_value = float(min(1.0, 2 * tail))
        else:
            p_value = 1.0
        effect = mean(case_diffs) if case_diffs else None
        results.append(
            {
                "metric": metric_name,
                "case_pairs": len(case_diffs),
                "baseline_case_mean": mean(baseline_means) if baseline_means else None,
                "candidate_case_mean": mean(candidate_means) if candidate_means else None,
                "case_mean_effect": effect,
                "nonzero_case_effects": n,
                "p_value": p_value,
                "method": "case-aggregated-paired-exact-sign-test",
            }
        )
    return results


def compare_online_mutant_to_noise_floor(
    study1b_online_dir: str | Path,
    mutant_online_dir: str | Path,
    out_dir: str | Path,
    *,
    expected_first_stage: str,
    expected_affected_cases: list[str] | None = None,
) -> dict[str, Any]:
    baseline = _normalize_analysis_records(load_records(study1b_online_dir))
    candidate = _normalize_analysis_records(load_records(mutant_online_dir))
    metrics = [
        "compile_success",
        "generated_file_count",
        "first_candidate_conformance",
        "final_candidate_conformance",
        "repair_rounds",
        "runtime_contract_pass",
        "oracle_requirement_recall",
        "oracle_foundation_recall",
        "oracle_capability_recall",
        "oracle_semantic_score",
    ]
    report = compare_releases(
        baseline,
        candidate,
        metrics=metrics,
        minimum_pairs=30,
        slice_keys=_DEFAULT_SLICE_KEYS,
    )
    attribution = case_attribution(baseline, candidate, stages=_UPSTREAM_STAGES)
    case_level = _case_level_metric_effects(baseline, candidate, metrics)
    pairs = _pair_records(baseline, candidate)

    expected_set = set(expected_affected_cases or [])
    expected_stage_pairs = [
        item for item in attribution["pairs"] if item["first_changed_stage"] == expected_first_stage
    ]
    expected_stage_cases = {str(item["case_id"]) for item in expected_stage_pairs}
    affected_case_lock = None if not expected_set else expected_stage_cases == expected_set

    upstream_stages = _STAGE_ORDER[:6]
    negative_control_upstream_mismatches: list[dict[str, str]] = []
    if expected_set:
        for left, right in pairs:
            case_id = right.benchmark_case_id or right.task_id
            if case_id in expected_set:
                continue
            for stage in upstream_stages:
                if left.stage_fingerprints.get(stage) != right.stage_fingerprints.get(stage):
                    negative_control_upstream_mismatches.append(
                        {"case_id": case_id, "replicate_id": right.replicate_id, "stage": stage}
                    )
                    break

    summary = {
        "kind": "Study2OnlineNoiseFloorComparison",
        "schema_version": STUDY_2_SCHEMA_VERSION,
        "baseline_records": len(baseline),
        "candidate_records": len(candidate),
        "matched_pairs": len(pairs),
        "raw_assay": report.model_dump(mode="json"),
        "case_attribution": attribution,
        "case_level_primary_inference": case_level,
        "expected_first_stage": expected_first_stage,
        "expected_affected_cases": sorted(expected_set),
        "observed_expected_stage_cases": sorted(expected_stage_cases),
        "expected_affected_case_lock": affected_case_lock,
        "negative_control_upstream_mismatches": negative_control_upstream_mismatches,
        "negative_control_upstream_lock": not negative_control_upstream_mismatches,
        "interpretation": (
            "Raw downstream SML/SIR/generated-tree inequality is treated as Study 1B stochastic "
            "background. Primary causal evidence is an upstream deterministic stage shift and "
            "case-aggregated semantic/runtime effects."
        ),
    }
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "study2_online_noise_comparison.json", summary)
    return summary
