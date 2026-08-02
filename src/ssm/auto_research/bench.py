from __future__ import annotations

import json
from pathlib import Path

from ssm.auto_research.hashing import sha256_value
from ssm.auto_research.schemas import BenchmarkManifest


class BenchmarkValidationError(ValueError):
    pass


def compute_corpus_sha256(root: str | Path, manifest: BenchmarkManifest) -> str:
    base = Path(root)
    payload: list[dict[str, str]] = []
    for case in sorted(manifest.cases, key=lambda item: item.case_id):
        path = (base / case.intent_path).resolve()
        try:
            path.relative_to(base.resolve())
        except ValueError as exc:
            raise BenchmarkValidationError(
                f"Benchmark path escapes corpus root: {case.intent_path}"
            ) from exc
        if not path.is_file():
            raise BenchmarkValidationError(f"Missing benchmark intent: {case.intent_path}")
        payload.append(
            {
                "case_id": case.case_id,
                "intent_sha256": sha256_value(path.read_text(encoding="utf-8")),
                "slices_sha256": sha256_value(case.slices),
            }
        )
    return sha256_value(payload)


def validate_benchmark_manifest(path: str | Path, *, minimum_cases: int = 30) -> BenchmarkManifest:
    manifest_path = Path(path)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = BenchmarkManifest.model_validate(raw)
    if len(manifest.cases) < minimum_cases:
        raise BenchmarkValidationError(
            f"Benchmark contains {len(manifest.cases)} cases; at least {minimum_cases} are required."
        )
    if len({item.case_id for item in manifest.cases}) != len(manifest.cases):
        raise BenchmarkValidationError("Benchmark case IDs must be unique.")
    if not manifest.frozen:
        raise BenchmarkValidationError("Research baseline corpus must be frozen before collection.")
    actual = compute_corpus_sha256(manifest_path.parent, manifest)
    if actual != manifest.corpus_sha256:
        raise BenchmarkValidationError(
            f"Corpus digest mismatch: expected {manifest.corpus_sha256}, observed {actual}."
        )
    expected_id = "sha256:" + sha256_value(
        {
            "schema_version": manifest.schema_version,
            "kind": manifest.kind,
            "name": manifest.name,
            "frozen": manifest.frozen,
            "cases": [item.model_dump(mode="json") for item in manifest.cases],
            "corpus_sha256": manifest.corpus_sha256,
        }
    )
    if manifest.benchmark_id != expected_id:
        raise BenchmarkValidationError("Benchmark ID is not content-addressed from the manifest.")
    return manifest
