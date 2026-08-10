from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ssm.architecture.schemas import ArchitecturePlan
from ssm.capabilities.schemas import CapabilityCompositionResult
from ssm.certification.schemas import CertificationReport
from ssm.foundation.schemas import AppFoundationPlan, CapabilityNegotiationResult
from ssm.incremental.schemas import ArtifactDiff, SemanticDependencyGraph
from ssm.requirements.schemas import RequirementsIR


class CanonicalSemanticContext(BaseModel):
    """Immutable semantic authority shared by offline and online SML synthesis.

    Raw user intent is deterministically collapsed into this context before a
    synthesis strategy is selected.  Online providers receive a bounded view of
    this object rather than unconstrained raw intent.
    """

    schema_version: str = "2.6.2"
    kind: str = "CanonicalSemanticContext"
    source_name: str
    source_sha256: str
    requirements: RequirementsIR
    foundation: AppFoundationPlan
    architecture: ArchitecturePlan
    capabilities: CapabilityCompositionResult
    negotiation: CapabilityNegotiationResult
    protected_semantics: list[str] = Field(default_factory=list)
    unresolved_semantics: list[str] = Field(default_factory=list)
    context_issues: list[str] = Field(default_factory=list)
    semantic_fingerprint: str = ""

    def llm_payload(self) -> dict[str, Any]:
        """Return the bounded provider-facing representation.

        Evidence excerpts and the raw source text are intentionally excluded.
        The provider receives the canonical interpretation plus source identity,
        not a second opportunity to reinterpret the original input.
        """

        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "source": {
                "name": self.source_name,
                "sha256": self.source_sha256,
            },
            "requirements": [
                {
                    "id": item.id,
                    "kind": item.kind,
                    "name": item.name,
                    "priority": item.priority,
                    "origin": item.origin,
                    "status": item.status,
                    "attributes": item.attributes,
                }
                for item in self.requirements.requirements
            ],
            "ambiguities": [item.model_dump(mode="json") for item in self.requirements.ambiguities],
            "contradictions": [
                item.model_dump(mode="json") for item in self.requirements.contradictions
            ],
            "assumptions": [item.model_dump(mode="json") for item in self.requirements.assumptions],
            "unsupported_features": list(self.requirements.unsupported_features),
            "foundation": self.foundation.model_dump(mode="json", exclude={"description"}),
            "architecture": self.architecture.model_dump(mode="json"),
            "capabilities": self.capabilities.model_dump(mode="json"),
            "negotiation": self.negotiation.model_dump(mode="json"),
            "protected_semantics": list(self.protected_semantics),
            "unresolved_semantics": list(self.unresolved_semantics),
            "context_issues": list(self.context_issues),
            "semantic_fingerprint": self.semantic_fingerprint,
        }


class SemanticConformanceDiagnostic(BaseModel):
    code: str
    category: str
    message: str
    severity: Literal["warning", "error"] = "error"
    expected: Any | None = None
    actual: Any | None = None


class SemanticConformanceReport(BaseModel):
    schema_version: str = "2.6.2"
    kind: str = "SemanticConformanceReport"
    status: Literal["PASS", "FAIL"]
    context_fingerprint: str
    candidate_sml_sha256: str
    checks: int = 0
    diagnostics: list[SemanticConformanceDiagnostic] = Field(default_factory=list)
    semantic_fingerprint: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == "PASS"


class CollapsePlan(BaseModel):
    schema_version: str = "2.6"
    kind: str = "SchrodingerCollapsePlan"
    requirements: RequirementsIR
    foundation: AppFoundationPlan
    architecture: ArchitecturePlan
    capabilities: CapabilityCompositionResult
    negotiation: CapabilityNegotiationResult
    canonical_context: CanonicalSemanticContext
    sml_text: str
    semantic_conformance: SemanticConformanceReport


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
