from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FeatureRequirement(BaseModel):
    name: str
    description: str
    priority: Literal["must", "should", "could"] = "must"


class ProjectRequirements(BaseModel):
    project_name: str
    description: str = ""
    domain: str | None = None
    features: list[FeatureRequirement] = Field(default_factory=list)
    stack_hints: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class SMLDocumentDraft(BaseModel):
    text: str
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    provenance: list[str] = Field(default_factory=list)


class SemanticPatch(BaseModel):
    target: Literal["sml", "sir", "target_pack", "dependency"]
    patch: str
    rationale: str
    expected_effect: str
