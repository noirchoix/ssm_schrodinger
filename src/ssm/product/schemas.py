from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ssm.architecture.schemas import ArchitecturePlan
from ssm.capabilities.schemas import CapabilityCompositionResult
from ssm.certification.schemas import CertificationReport
from ssm.foundation.schemas import AppFoundationPlan, CapabilityNegotiationResult
from ssm.incremental.schemas import ArtifactDiff, SemanticDependencyGraph
from ssm.requirements.schemas import RequirementsIR


class CollapsePlan(BaseModel):
    schema_version: str = "2.6"
    kind: str = "SchrodingerCollapsePlan"
    requirements: RequirementsIR
    foundation: AppFoundationPlan
    architecture: ArchitecturePlan
    capabilities: CapabilityCompositionResult
    negotiation: CapabilityNegotiationResult
    sml_text: str


class ProductBuildResult(BaseModel):
    schema_version: str = "2.6"
    kind: str = "SchrodingerProductBuild"
    status: Literal["ACCEPTED", "CONDITIONAL", "REJECTED"]
    out_dir: str | None = None
    generated_app_dir: str | None = None
    generated_file_count: int = 0
    requirements_fingerprint: str
    architecture_fingerprint: str
    capability_fingerprint: str
    selected_architecture: str
    negotiation_status: str
    capability_status: str
    artifact_diff: ArtifactDiff | None = None
    dependency_graph: SemanticDependencyGraph | None = None
    certification: CertificationReport | None = None
    warnings: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
