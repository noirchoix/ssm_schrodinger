from __future__ import annotations

import json
import platform as platform_module
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ssm import __version__
from ssm.auto_research.hashing import sha256_file, sha256_value, write_canonical_json
from ssm.auto_research.schemas import (
    ArtifactReference,
    EnvironmentIdentity,
    GenerationRunRecord,
    MetricObservation,
)


def environment_identity(
    root: str | Path,
    *,
    provider: str | None = None,
    model: str | None = None,
    scaffold_version: str | None = None,
    prompt_version: str | None = None,
    attributes: dict[str, str] | None = None,
) -> EnvironmentIdentity:
    base = Path(root)
    lock_files = [
        base / "pyproject.toml",
        base / "requirements.txt",
        base / "requirements.lock",
        base / "uv.lock",
        base / "poetry.lock",
    ]
    present = {path.name: sha256_file(path) for path in lock_files if path.is_file()}
    dependency_digest = sha256_value(present) if present else None
    payload = {
        "compiler_version": __version__,
        "python_version": platform_module.python_version(),
        "platform": platform_module.platform(),
        "provider": provider,
        "model": model,
        "scaffold_version": scaffold_version,
        "prompt_version": prompt_version,
        "dependency_lock_sha256": dependency_digest,
        "attributes": attributes or {},
    }
    return EnvironmentIdentity(
        compiler_version=__version__,
        python_version=platform_module.python_version(),
        platform=platform_module.platform(),
        provider=provider,
        model=model,
        scaffold_version=scaffold_version,
        prompt_version=prompt_version,
        dependency_lock_sha256=dependency_digest,
        environment_lock_sha256=sha256_value(payload),
        attributes=attributes or {},
    )


def artifact_references(
    root: str | Path, *, exclude: set[str] | None = None
) -> list[ArtifactReference]:
    base = Path(root)
    excluded = exclude or set()
    rows: list[ArtifactReference] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        if relative in excluded or relative.startswith(".git/") or "__pycache__" in relative:
            continue
        rows.append(
            ArtifactReference(
                name=path.name,
                kind=_artifact_kind(relative),
                relative_path=relative,
                sha256=sha256_file(path),
            )
        )
    return rows


def build_generation_run_record(
    *,
    output: str | Path,
    source_text: str,
    source_name: str,
    status: str,
    started_at: datetime,
    duration_ms: int,
    task_id: str | None = None,
    benchmark_case_id: str | None = None,
    replicate_id: str = "0",
    stage_fingerprints: dict[str, str] | None = None,
    metrics: dict[str, MetricObservation] | None = None,
    trace_ids: list[str] | None = None,
    eval_run_ids: list[str] | None = None,
    slices: dict[str, str] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    provider: str | None = None,
    model: str | None = None,
    scaffold_version: str | None = None,
    prompt_version: str | None = None,
    run_id: str | None = None,
) -> GenerationRunRecord:
    root = Path(output)
    observed_metrics = dict(metrics or {})
    observed_metrics.setdefault(
        "build_duration_ms",
        MetricObservation(
            name="build_duration_ms", value=duration_ms, unit="ms", source="monotonic_clock"
        ),
    )
    observed_metrics.setdefault(
        "artifact_count",
        MetricObservation(
            name="artifact_count",
            value=len(
                artifact_references(root, exclude={"generation_run.json", "build_manifest.json"})
            ),
            unit="files",
            source="output_tree",
        ),
    )
    return GenerationRunRecord.create(
        run_id=run_id or f"run:{uuid.uuid4().hex}",
        task_id=task_id or source_name,
        benchmark_case_id=benchmark_case_id,
        replicate_id=replicate_id,
        started_at=started_at.astimezone(UTC).isoformat(),
        completed_at=datetime.now(UTC).isoformat(),
        status=status,
        reproducibility="REPRODUCIBLE" if status in {"ACCEPTED", "CONDITIONAL"} else "UNKNOWN",
        source_name=source_name,
        source_sha256=sha256_value(source_text),
        environment=environment_identity(
            _find_project_root(root),
            provider=provider,
            model=model,
            scaffold_version=scaffold_version,
            prompt_version=prompt_version,
        ),
        stage_fingerprints=stage_fingerprints or {},
        metrics=observed_metrics,
        artifacts=artifact_references(root, exclude={"generation_run.json", "build_manifest.json"}),
        trace_ids=trace_ids or [],
        eval_run_ids=eval_run_ids or [],
        slices=slices or {},
        warnings=warnings or [],
        errors=errors or [],
    )


def write_generation_run_record(path: str | Path, record: GenerationRunRecord) -> None:
    write_canonical_json(path, record.model_dump(mode="json"))


def load_generation_run_record(path: str | Path) -> GenerationRunRecord:
    record = GenerationRunRecord.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    if not record.verify_identity():
        raise ValueError("GenerationRunRecord content address does not match its payload.")
    return record


def now_utc() -> datetime:
    return datetime.now(UTC)


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def _artifact_kind(relative: str) -> str:
    if relative.endswith(".json"):
        return "record"
    if relative.endswith(".md"):
        return "specification"
    if relative.endswith(".jsonl"):
        return "trace"
    if relative.startswith("generated_app/"):
        return "generated_artifact"
    return "artifact"


def _find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()
