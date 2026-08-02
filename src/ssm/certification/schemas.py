from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CertificationCheck(BaseModel):
    check_id: str
    category: str
    status: Literal["pass", "warning", "fail"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class VariabilityMetrics(BaseModel):
    extraction_runs: int
    unique_requirements_fingerprints: int
    unique_architecture_fingerprints: int
    unique_capability_fingerprints: int
    unique_sml_hashes: int
    unique_generated_tree_hashes: int
    semantic_variance_score: float


class SeniorGradeMetrics(BaseModel):
    requirements_coverage: float
    explicit_requirement_coverage: float
    architecture_consistency: float
    capability_honesty: float
    deterministic_generation: float
    unsupported_visibility: float
    repair_boundary_integrity: float


class CertificationReport(BaseModel):
    schema_version: str = "2.5"
    kind: str = "SeniorGradeCertificationReport"
    status: Literal[
        "CERTIFIED_SUPPORTED_PROFILE",
        "CONDITIONAL_SUPPORTED_PROFILE",
        "REJECTED",
    ]
    profile: str = "FastAPI/PostgreSQL-or-InMemory/JWT/modular-monolith"
    checks: list[CertificationCheck] = Field(default_factory=list)
    variability: VariabilityMetrics
    metrics: SeniorGradeMetrics
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    conclusion: str
