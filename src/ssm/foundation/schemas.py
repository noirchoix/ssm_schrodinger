from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AppEntity(BaseModel):
    name: str
    fields: dict[str, str] = Field(default_factory=dict)
    create_fields: dict[str, str] | None = None
    description: str = ""


class AppRelationship(BaseModel):
    name: str
    source: str
    target: str
    cardinality: Literal["one-to-one", "one-to-many", "many-to-one", "many-to-many"] = "many-to-one"
    required: bool = True


class AppRole(BaseModel):
    name: str
    permissions: list[str] = Field(default_factory=list)


class AppWorkflow(BaseModel):
    name: str
    entity: str
    states: list[str] = Field(default_factory=list)
    transitions: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class AppBusinessRule(BaseModel):
    name: str
    entity: str | None = None
    rule: str
    on_violation: Literal["reject", "warn", "audit"] = "reject"


class AppRoute(BaseModel):
    name: str
    method: Literal["GET", "POST", "PATCH", "PUT", "DELETE"]
    path: str
    auth: Literal["required", "optional", "none"] = "required"
    body: str | None = None
    returns: str | None = None


class AppFoundationPlan(BaseModel):
    app_name: str
    description: str = ""
    app_type: str = "generic"
    domain_pack_candidates: list[str] = Field(default_factory=list)
    entities: list[AppEntity] = Field(default_factory=list)
    relationships: list[AppRelationship] = Field(default_factory=list)
    roles: list[AppRole] = Field(default_factory=list)
    workflows: list[AppWorkflow] = Field(default_factory=list)
    business_rules: list[AppBusinessRule] = Field(default_factory=list)
    routes: list[AppRoute] = Field(default_factory=list)
    reports: list[str] = Field(default_factory=list)
    nonfunctional_requirements: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    backend: str = "FastAPI"
    database: str = "PostgreSQL"
    auth: str = "JWT"
    tenant_enabled: bool = True
    audit_enabled: bool = True


class CapabilityIssue(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"
    suggested_fix: str | None = None


class CapabilityNegotiationResult(BaseModel):
    status: Literal["SUPPORTED", "SUPPORTED_WITH_ASSUMPTIONS", "PARTIALLY_SUPPORTED", "UNSUPPORTED"]
    selected_domain_packs: list[str] = Field(default_factory=list)
    supported_features: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    issues: list[CapabilityIssue] = Field(default_factory=list)

    @property
    def accepted(self) -> bool:
        return self.status in {"SUPPORTED", "SUPPORTED_WITH_ASSUMPTIONS"}
