from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RequirementKind = Literal[
    "actor",
    "entity",
    "workflow",
    "business_rule",
    "integration",
    "security",
    "stack",
    "capability",
    "nonfunctional",
    "constraint",
    "report",
    "use_case",
]
RequirementOrigin = Literal["explicit", "inferred", "default"]
RequirementStatus = Literal["accepted", "ambiguous", "contradictory", "unsupported"]
Impact = Literal["low", "medium", "high"]


class RequirementEvidence(BaseModel):
    source_id: str
    line_start: int | None = None
    line_end: int | None = None
    excerpt: str = ""


class RequirementItem(BaseModel):
    id: str
    kind: RequirementKind
    name: str
    description: str
    priority: Literal["must", "should", "could"] = "must"
    origin: RequirementOrigin = "explicit"
    status: RequirementStatus = "accepted"
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[RequirementEvidence] = Field(default_factory=list)


class Ambiguity(BaseModel):
    id: str
    topic: str
    description: str
    impact: Impact = "medium"
    blocking: bool = False
    options: list[str] = Field(default_factory=list)
    related_requirement_ids: list[str] = Field(default_factory=list)


class Contradiction(BaseModel):
    id: str
    topic: str
    description: str
    impact: Impact = "high"
    requirement_ids: list[str] = Field(default_factory=list)


class RequirementAssumption(BaseModel):
    id: str
    statement: str
    impact: Impact = "medium"
    source: Literal["compiler_default", "domain_pack", "inference"] = "inference"
    related_requirement_ids: list[str] = Field(default_factory=list)


class RequirementsIR(BaseModel):
    schema_version: str = "2.1"
    kind: str = "RequirementsIR"
    source_name: str
    source_sha256: str
    title: str
    summary: str
    requirements: list[RequirementItem] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    assumptions: list[RequirementAssumption] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    domain_hints: list[str] = Field(default_factory=list)
    stack_hints: dict[str, str] = Field(default_factory=dict)
    semantic_fingerprint: str = ""

    @property
    def blocking(self) -> bool:
        return bool(self.contradictions) or any(item.blocking for item in self.ambiguities)

    @property
    def explicit_requirement_ids(self) -> list[str]:
        return [item.id for item in self.requirements if item.origin == "explicit"]
