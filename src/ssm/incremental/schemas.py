from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DependencyNode(BaseModel):
    id: str
    layer: Literal[
        "requirements",
        "foundation",
        "architecture",
        "capability",
        "sml",
        "sir",
        "artifact",
        "evidence",
    ]
    label: str
    content_hash: str | None = None


class DependencyEdge(BaseModel):
    source: str
    target: str
    relation: str


class SemanticDependencyGraph(BaseModel):
    schema_version: str = "2.4"
    kind: str = "SemanticDependencyGraph"
    nodes: list[DependencyNode] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)


class ArtifactChange(BaseModel):
    path: str
    status: Literal["added", "modified", "removed", "unchanged"]
    before_sha256: str | None = None
    after_sha256: str | None = None
    cause_layers: list[str] = Field(default_factory=list)


class ArtifactDiff(BaseModel):
    schema_version: str = "2.4"
    kind: str = "ArtifactDiff"
    changes: list[ArtifactChange] = Field(default_factory=list)
    added: int = 0
    modified: int = 0
    removed: int = 0
    unchanged: int = 0
    unchanged_proof_sha256: str = ""


class FailureClassification(BaseModel):
    source: str
    failure_code: str
    target_layer: Literal[
        "requirements",
        "foundation",
        "architecture",
        "capability",
        "sml",
        "target_pack",
        "generated_test",
        "environment",
    ]
    retryable: bool
    rationale: str


class RepairDirective(BaseModel):
    target_layer: str
    failure_code: str
    permitted_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    requires_full_regeneration: bool = False
    rationale: str
