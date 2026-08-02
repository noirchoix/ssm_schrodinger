from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ArchitectureModule(BaseModel):
    id: str
    name: str
    responsibility: str
    entities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class UseCaseSpec(BaseModel):
    id: str
    name: str
    actor: str
    entity: str | None = None
    command: str
    authorization: str
    transaction_required: bool = False
    preconditions: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    emits_events: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)


class TransactionBoundary(BaseModel):
    id: str
    use_case_id: str
    consistency_scope: list[str] = Field(default_factory=list)
    isolation_expectation: str = "atomic"


class DomainEventSpec(BaseModel):
    id: str
    name: str
    producer_use_case_id: str
    payload_fields: list[str] = Field(default_factory=list)
    delivery: Literal["in_process", "outbox_required", "external"] = "in_process"


class IntegrationAdapterSpec(BaseModel):
    id: str
    name: str
    boundary: str
    status: Literal["implemented", "scaffold", "external_contract", "unsupported"]
    timeout_policy: str | None = None
    retry_policy: str | None = None
    idempotency_policy: str | None = None


class FailureModelSpec(BaseModel):
    code: str
    category: Literal[
        "validation",
        "authentication",
        "authorization",
        "not_found",
        "conflict",
        "state",
        "business_rule",
        "dependency",
        "rate_limit",
    ]
    http_status: int
    retryable: bool = False


class NonFunctionalRequirementSpec(BaseModel):
    id: str
    name: str
    measurable_obligation: str
    evidence_gate: str


class ArchitectureCandidate(BaseModel):
    id: str
    pattern: str
    status: Literal["selected", "admissible", "rejected"]
    score: float
    reasons: list[str] = Field(default_factory=list)


class ArchitectureProof(BaseModel):
    decision_id: str
    claim: str
    selected_candidate_id: str
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    support: list[str] = Field(default_factory=list)


class ArchitecturePlan(BaseModel):
    schema_version: str = "2.2"
    kind: str = "ArchitecturePlan"
    selected_pattern: str
    modules: list[ArchitectureModule] = Field(default_factory=list)
    use_cases: list[UseCaseSpec] = Field(default_factory=list)
    transaction_boundaries: list[TransactionBoundary] = Field(default_factory=list)
    events: list[DomainEventSpec] = Field(default_factory=list)
    integration_adapters: list[IntegrationAdapterSpec] = Field(default_factory=list)
    failure_models: list[FailureModelSpec] = Field(default_factory=list)
    nonfunctional_requirements: list[NonFunctionalRequirementSpec] = Field(default_factory=list)
    candidates: list[ArchitectureCandidate] = Field(default_factory=list)
    proof: ArchitectureProof
    semantic_fingerprint: str = ""
