from __future__ import annotations

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


class EvidenceValidationResult(BaseModel):
    ok: bool
    root: str
    records_checked: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def validate_evidence_directory(root: str | Path) -> EvidenceValidationResult:
    base = Path(root)
    errors: list[str] = []
    checked: list[str] = []
    for record in REQUIRED_RECORDS:
        path = base / record
        if not path.exists():
            errors.append(f"missing {record}")
            continue
        checked.append(record)
        try:
            payload = _load(path)
        except Exception as exc:
            errors.append(f"invalid {record}: {exc}")
            continue
        if payload.get("schema_version") != "1.0":
            errors.append(f"{record} has unsupported schema_version")
        if not payload.get("kind"):
            errors.append(f"{record} is missing kind")
    if (base / "generated_app_manifest.json").exists():
        manifest = _load(base / "generated_app_manifest.json")
        if manifest.get("compiler", {}).get("target") != "python.fastapi":
            errors.append("generated_app_manifest target must be python.fastapi")
    if (base / "evidence_bundle.json").exists():
        bundle = _load(base / "evidence_bundle.json")
        records = set(bundle.get("records", []))
        for record in REQUIRED_RECORDS[:-1]:
            if record not in records:
                errors.append(f"evidence_bundle does not reference {record}")
    return EvidenceValidationResult(
        ok=not errors, root=str(base), records_checked=checked, errors=errors
    )
