from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

REQUIRED_RECORDS = [
    "generated_app_manifest.json",
    "app_contract.json",
    "eval_run.json",
    "capability_report.json",
    "assumptions.json",
    "unsupported_features.json",
    "provenance_hashes.json",
    "evidence_bundle.json",
]
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "2.0"}


class EvidenceValidationResult(BaseModel):
    ok: bool
    root: str
    records_checked: list[str] = Field(default_factory=list)
    files_hashed: int = 0
    errors: list[str] = Field(default_factory=list)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _safe_generated_path(base: Path, relative_path: str) -> Path:
    candidate = (base / relative_path).resolve()
    resolved_base = base.resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(f"generated file path escapes app root: {relative_path}") from exc
    return candidate


def _validate_provenance(
    base: Path,
    provenance: dict[str, Any],
    errors: list[str],
) -> int:
    if provenance.get("schema_version") != "2.0":
        return 0
    if provenance.get("hash_algorithm") != "sha256":
        errors.append("provenance_hashes hash_algorithm must be sha256")
    hashes = provenance.get("generated_file_sha256")
    if not isinstance(hashes, dict) or not hashes:
        errors.append("provenance_hashes generated_file_sha256 must be a non-empty object")
        return 0
    checked = 0
    for relative_path, expected in sorted(hashes.items()):
        if not isinstance(relative_path, str) or not isinstance(expected, str):
            errors.append("provenance_hashes entries must map string paths to string hashes")
            continue
        try:
            path = _safe_generated_path(base, relative_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file():
            errors.append(f"provenance file is missing: {relative_path}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        checked += 1
        if actual != expected:
            errors.append(f"provenance hash mismatch: {relative_path}")
    return checked


def validate_evidence_directory(root: str | Path) -> EvidenceValidationResult:
    base = Path(root)
    errors: list[str] = []
    checked: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}

    for record in REQUIRED_RECORDS:
        path = base / record
        if not path.exists():
            errors.append(f"missing {record}")
            continue
        checked.append(record)
        try:
            payload = _load(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid {record}: {exc}")
            continue
        payloads[record] = payload
        if payload.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
            errors.append(f"{record} has unsupported schema_version")
        if not payload.get("kind"):
            errors.append(f"{record} is missing kind")

    manifest = payloads.get("generated_app_manifest.json", {})
    if manifest.get("compiler", {}).get("target") != "python.fastapi":
        errors.append("generated_app_manifest target must be python.fastapi")
    generated_files = manifest.get("generated_files", [])
    if generated_files and not isinstance(generated_files, list):
        errors.append("generated_app_manifest generated_files must be a list")
    elif isinstance(generated_files, list):
        for relative_path in generated_files:
            if not isinstance(relative_path, str):
                errors.append("generated_app_manifest generated_files entries must be strings")
                continue
            try:
                path = _safe_generated_path(base, relative_path)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not path.exists():
                errors.append(f"manifest-listed generated file is missing: {relative_path}")

    bundle = payloads.get("evidence_bundle.json", {})
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("evidence_bundle records must be a list")
    else:
        record_set = set(records)
        for record in REQUIRED_RECORDS[:-1]:
            if record not in record_set:
                errors.append(f"evidence_bundle does not reference {record}")

    files_hashed = _validate_provenance(
        base,
        payloads.get("provenance_hashes.json", {}),
        errors,
    )
    return EvidenceValidationResult(
        ok=not errors,
        root=str(base),
        records_checked=checked,
        files_hashed=files_hashed,
        errors=errors,
    )
