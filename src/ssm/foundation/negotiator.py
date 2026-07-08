from __future__ import annotations

from typing import Literal

from ssm.domain_packs.registry import all_domain_packs, packs_for_plan
from ssm.foundation.schemas import (
    AppFoundationPlan,
    CapabilityIssue,
    CapabilityNegotiationResult,
)
from ssm.frontend.parser import SMLParser
from ssm.semantic.field_parser import normalize_schema_name

_SUPPORTED_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}
_UNSUPPORTED_INTEGRATIONS = {
    "stripe",
    "payment",
    "tax",
    "shipping carrier",
    "external email provider",
    "sms gateway",
}


class CapabilityNegotiator:
    """Negotiates app-foundation plans against compiler/domain-pack capabilities."""

    def negotiate_plan(self, plan: AppFoundationPlan) -> CapabilityNegotiationResult:
        packs = packs_for_plan(plan)
        issues: list[CapabilityIssue] = []
        unsupported = list(plan.unsupported_features)
        for feature in plan.unsupported_features:
            issues.append(
                CapabilityIssue(
                    code="CAP_UNSUPPORTED_FEATURE",
                    message=f"Requested feature is outside this version's generator scope: {feature}",
                    severity="error",
                    suggested_fix="Represent the feature as an external integration stub or defer it.",
                )
            )
        for route in plan.routes:
            if route.method not in _SUPPORTED_METHODS:
                unsupported.append(f"route method {route.method}")
                issues.append(
                    CapabilityIssue(
                        code="CAP_UNSUPPORTED_ROUTE_METHOD",
                        message=f"Route {route.name} uses unsupported method {route.method}.",
                        severity="error",
                    )
                )
            if "{" in route.path and "}" not in route.path:
                issues.append(
                    CapabilityIssue(
                        code="CAP_INVALID_PATH_TEMPLATE",
                        message=f"Route {route.name} has an invalid path template.",
                        severity="error",
                    )
                )
        if not plan.entities:
            issues.append(
                CapabilityIssue(
                    code="CAP_NO_ENTITIES",
                    message="No entities were identified for this app foundation.",
                    severity="error",
                )
            )
        if plan.relationships:
            entity_names = {entity.name for entity in plan.entities}
            for relationship in plan.relationships:
                if (
                    relationship.source not in entity_names
                    or relationship.target not in entity_names
                ):
                    issues.append(
                        CapabilityIssue(
                            code="CAP_RELATIONSHIP_UNRESOLVED_ENTITY",
                            message=(
                                f"Relationship {relationship.name} references an entity that is not "
                                "declared in the plan."
                            ),
                            severity="error",
                        )
                    )
        status = self._status(issues, plan.assumptions)
        return CapabilityNegotiationResult(
            status=status,
            selected_domain_packs=[pack.id for pack in packs],
            supported_features=self._supported_features(plan),
            unsupported_features=sorted(set(unsupported)),
            assumptions=plan.assumptions,
            issues=issues,
        )

    def negotiate_sml_text(
        self, text: str, source_file: str = "<memory>"
    ) -> CapabilityNegotiationResult:
        document = SMLParser().parse_text(text, source_file=source_file)
        issues: list[CapabilityIssue] = []
        packs = [
            section.name for section in document.sections_of_type("Capability") if section.name
        ]
        if not packs:
            packs = ["generic_crud"]
        models = {
            section.name for section in document.sections_of_type("DataModel") if section.name
        }
        for section in document.sections_of_type("Route"):
            method = str(section.fields.get("method", "GET")).upper()
            if method not in _SUPPORTED_METHODS:
                issues.append(
                    CapabilityIssue(
                        code="CAP_UNSUPPORTED_ROUTE_METHOD",
                        message=f"Route {section.name} uses unsupported method {method}.",
                        severity="error",
                    )
                )
            for key in ["body", "returns"]:
                value = section.fields.get(key)
                if value and str(value).lower() != "none":
                    schema = normalize_schema_name(str(value))
                    if schema not in models and schema.lower() not in {"none", "null"}:
                        issues.append(
                            CapabilityIssue(
                                code="CAP_UNRESOLVED_SCHEMA",
                                message=f"Route {section.name} references undeclared schema {schema}.",
                                severity="error",
                            )
                        )
        for section in document.sections_of_type("Integration"):
            name = (section.name or "").lower()
            if name in _UNSUPPORTED_INTEGRATIONS:
                issues.append(
                    CapabilityIssue(
                        code="CAP_UNSUPPORTED_INTEGRATION",
                        message=f"Integration {section.name} is outside this compiler version.",
                        severity="error",
                        suggested_fix="Represent it as an outbound event or defer to a later integration pack.",
                    )
                )
        known_packs = all_domain_packs()
        selected = [pack for pack in packs if pack in known_packs]
        if not selected:
            selected = ["generic_crud"]
        return CapabilityNegotiationResult(
            status=self._status(issues, []),
            selected_domain_packs=selected,
            supported_features=["crud", "relationships", "workflow-semantics", "quality-gates"],
            unsupported_features=[issue.message for issue in issues if issue.severity == "error"],
            assumptions=[],
            issues=issues,
        )

    def _supported_features(self, plan: AppFoundationPlan) -> list[str]:
        features = ["crud", "typed-routes", "quality-gates", "openapi-contracts"]
        if plan.relationships:
            features.append("relationship-foundation")
        if plan.workflows:
            features.append("workflow-foundation")
        if plan.tenant_enabled:
            features.append("tenant-foundation")
        if plan.audit_enabled:
            features.append("audit-foundation")
        return sorted(set(features))

    def _status(
        self, issues: list[CapabilityIssue], assumptions: list[str]
    ) -> Literal["SUPPORTED", "SUPPORTED_WITH_ASSUMPTIONS", "PARTIALLY_SUPPORTED", "UNSUPPORTED"]:
        if any(issue.severity == "error" for issue in issues):
            return "UNSUPPORTED"
        if issues:
            return "PARTIALLY_SUPPORTED"
        if assumptions:
            return "SUPPORTED_WITH_ASSUMPTIONS"
        return "SUPPORTED"
