from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SupportStatus = Literal[
    "SUPPORTED",
    "SUPPORTED_WITH_ASSUMPTIONS",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
]
ImplementationStatus = Literal["production", "scaffold", "contract_only", "unsupported"]


class CapabilityPackSpec(BaseModel):
    capability_id: str
    version: str = "1"
    description: str
    triggers: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    guarantees: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    generated_artifacts: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    implementation_status: ImplementationStatus


class CapabilitySelection(BaseModel):
    capability_id: str
    requested: bool = False
    inferred: bool = False
    implementation_status: ImplementationStatus
    support_status: SupportStatus
    guarantees: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)


class CapabilityCompositionIssue(BaseModel):
    code: str
    capability_id: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class CapabilityCompositionResult(BaseModel):
    schema_version: str = "2.3"
    kind: str = "CapabilityComposition"
    status: SupportStatus
    selected: list[CapabilitySelection] = Field(default_factory=list)
    issues: list[CapabilityCompositionIssue] = Field(default_factory=list)
    guarantees: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    semantic_fingerprint: str = ""
