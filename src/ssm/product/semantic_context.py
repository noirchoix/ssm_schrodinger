from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any, Literal

from ssm.auto_research.hashing import sha256_value
from ssm.frontend.parser import SMLParser
from ssm.models import SMLDocument, SMLSection
from ssm.product.schemas import (
    CanonicalSemanticContext,
    SemanticConformanceDiagnostic,
    SemanticConformanceReport,
)


class SemanticConformanceVerifier:
    """Verify candidate SML against the deterministic canonical semantic context.

    The verifier is intentionally structural. It does not require byte-for-byte
    equality with the offline renderer, but it does require the candidate to
    preserve the canonical stack, entities, relationships, workflows, executable
    rules, routes, and enabled platform primitives. Derived Create/Update models
    and representationally equivalent PATCH bodies are allowed.
    """

    def __init__(self) -> None:
        self.parser = SMLParser()

    def verify(
        self,
        context: CanonicalSemanticContext,
        candidate_sml: str,
        *,
        source_file: str = "<candidate-sml>",
    ) -> SemanticConformanceReport:
        document = self.parser.parse_text(candidate_sml, source_file=source_file)
        diagnostics: list[SemanticConformanceDiagnostic] = []
        checks = 0

        def check(
            condition: bool,
            *,
            code: str,
            category: str,
            message: str,
            expected: Any | None = None,
            actual: Any | None = None,
            severity: Literal["warning", "error"] = "error",
        ) -> None:
            nonlocal checks
            checks += 1
            if condition:
                return
            diagnostics.append(
                SemanticConformanceDiagnostic(
                    code=code,
                    category=category,
                    message=message,
                    severity=severity,
                    expected=expected,
                    actual=actual,
                )
            )

        self._verify_stack(context, document, check)
        self._verify_platform_primitives(context, document, check)
        self._verify_capabilities(context, document, check)
        self._verify_entities(context, document, check)
        self._verify_relationships(context, document, check)
        self._verify_roles(context, document, check)
        self._verify_workflows(context, document, check)
        self._verify_business_rules(context, document, check)
        self._verify_routes(context, document, check)
        self._verify_reports(context, document, check)
        self._verify_required_scaffolding(context, document, check)

        status: Literal["PASS", "FAIL"] = (
            "FAIL" if any(item.severity == "error" for item in diagnostics) else "PASS"
        )
        payload = {
            "status": status,
            "context_fingerprint": context.semantic_fingerprint,
            "candidate_sml_sha256": sha256_value(candidate_sml),
            "checks": checks,
            "diagnostics": [item.model_dump(mode="json") for item in diagnostics],
        }
        return SemanticConformanceReport(
            status=status,
            context_fingerprint=context.semantic_fingerprint,
            candidate_sml_sha256=sha256_value(candidate_sml),
            checks=checks,
            diagnostics=diagnostics,
            semantic_fingerprint=sha256_value(payload),
        )

    def format_diagnostics(self, report: SemanticConformanceReport) -> str:
        if report.accepted:
            return "Semantic conformance passed."
        lines = ["Semantic conformance failed:"]
        for item in report.diagnostics:
            if item.severity != "error":
                continue
            detail = ""
            if item.expected is not None or item.actual is not None:
                expected = json.dumps(item.expected, sort_keys=True, default=str)
                actual = json.dumps(item.actual, sort_keys=True, default=str)
                detail = f" Expected={expected}; actual={actual}."
            lines.append(f"- {item.code} [{item.category}]: {item.message}{detail}")
        return "\n".join(lines)

    def _verify_stack(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        stack = self._first(document, "Stack")
        check(
            stack is not None,
            code="SCV001",
            category="stack",
            message="Candidate SML must declare #Stack.",
        )
        if stack is None:
            return
        for key, expected in {
            "backend": context.foundation.backend,
            "database": context.foundation.database,
            "auth": context.foundation.auth,
        }.items():
            actual = stack.fields.get(key)
            check(
                self._norm(str(actual or "")) == self._norm(str(expected)),
                code="SCV002",
                category="stack",
                message=f"Stack field {key!r} diverges from canonical semantics.",
                expected=expected,
                actual=actual,
            )

    def _verify_platform_primitives(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        tenant = self._first(document, "Tenant")
        audit = self._first(document, "Audit")
        tenant_enabled = bool(tenant and tenant.fields.get("enabled") is True)
        audit_enabled = bool(audit and audit.fields.get("enabled") is True)
        check(
            tenant_enabled == context.foundation.tenant_enabled,
            code="SCV010",
            category="tenancy",
            message="Tenant enablement must match the canonical foundation.",
            expected=context.foundation.tenant_enabled,
            actual=tenant_enabled,
        )
        check(
            audit_enabled == context.foundation.audit_enabled,
            code="SCV011",
            category="audit",
            message="Audit enablement must match the canonical foundation.",
            expected=context.foundation.audit_enabled,
            actual=audit_enabled,
        )

    def _verify_capabilities(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = {
            self._norm_name(section.name or "")
            for section in document.sections_of_type("Capability")
            if section.name
        }
        expected = {self._norm_name(item) for item in context.foundation.domain_pack_candidates}
        # Generic CRUD is the compiler's implicit fallback when no capability section exists.
        if not actual and expected == {"genericcrud"}:
            actual = {"genericcrud"}
        for capability in sorted(expected):
            check(
                capability in actual,
                code="SCV020",
                category="capability",
                message="Required domain capability is missing from candidate SML.",
                expected=capability,
                actual=sorted(actual),
            )

    def _verify_entities(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        models = {
            self._norm_name(section.name or ""): section
            for section in document.sections_of_type("DataModel")
            if section.name
        }
        allowed_model_names: set[str] = set()
        for entity in context.foundation.entities:
            base = self._norm_name(entity.name)
            allowed_model_names.update({base, f"{base}create", f"{base}update"})
            section = models.get(base)
            check(
                section is not None,
                code="SCV030",
                category="entity",
                message=f"Canonical entity {entity.name} is missing.",
                expected=entity.name,
                actual=sorted(section.name for section in models.values() if section.name),
            )
            if section is not None:
                self._verify_fields(entity.name, entity.fields, section, check)

            create_section = models.get(f"{base}create")
            check(
                create_section is not None,
                code="SCV031",
                category="entity",
                message=f"Create schema for canonical entity {entity.name} is missing.",
                expected=f"{entity.name}Create",
                actual=sorted(section.name for section in models.values() if section.name),
            )
            if create_section is not None:
                expected_create = entity.create_fields or {
                    name: descriptor
                    for name, descriptor in entity.fields.items()
                    if "primary" not in descriptor.lower()
                }
                self._verify_fields(f"{entity.name}Create", expected_create, create_section, check)

        for normalized, section in models.items():
            if normalized in allowed_model_names:
                continue
            check(
                False,
                code="SCV032",
                category="entity",
                message=f"Candidate introduces non-canonical data model {section.name}.",
                expected=sorted(allowed_model_names),
                actual=section.name,
            )

    def _verify_fields(
        self,
        model_name: str,
        expected_fields: dict[str, str],
        section: SMLSection,
        check: Any,
    ) -> None:
        actual_fields = section.fields.get("fields")
        if not isinstance(actual_fields, dict):
            check(
                False,
                code="SCV033",
                category="field",
                message=f"Data model {model_name} must contain a fields mapping.",
                expected=sorted(expected_fields),
                actual=actual_fields,
            )
            return
        actual_by_name = {self._norm_name(str(key)): value for key, value in actual_fields.items()}
        for field_name, descriptor in expected_fields.items():
            normalized = self._norm_name(field_name)
            actual_descriptor = actual_by_name.get(normalized)
            check(
                actual_descriptor is not None,
                code="SCV034",
                category="field",
                message=f"Required field {model_name}.{field_name} is missing.",
                expected=descriptor,
                actual=None,
            )
            if actual_descriptor is None:
                continue
            expected_tokens = self._descriptor_tokens(descriptor)
            actual_tokens = self._descriptor_tokens(str(actual_descriptor))
            check(
                expected_tokens.issubset(actual_tokens),
                code="SCV035",
                category="field",
                message=f"Field contract {model_name}.{field_name} was weakened or changed.",
                expected=sorted(expected_tokens),
                actual=sorted(actual_tokens),
            )

    def _verify_relationships(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = list(document.sections_of_type("Relationship"))
        for relationship in context.foundation.relationships:
            match = next(
                (
                    section
                    for section in actual
                    if self._norm_name(str(section.fields.get("source", "")))
                    == self._norm_name(relationship.source)
                    and self._norm_name(str(section.fields.get("target", "")))
                    == self._norm_name(relationship.target)
                    and self._norm(str(section.fields.get("cardinality", "")))
                    == self._norm(relationship.cardinality)
                ),
                None,
            )
            check(
                match is not None,
                code="SCV040",
                category="relationship",
                message=f"Canonical relationship {relationship.name} is missing or changed.",
                expected=relationship.model_dump(mode="json"),
                actual=[item.fields for item in actual],
            )
            if match is not None:
                actual_required = bool(match.fields.get("required", False))
                check(
                    actual_required == relationship.required,
                    code="SCV041",
                    category="relationship",
                    message=f"Relationship requiredness changed for {relationship.name}.",
                    expected=relationship.required,
                    actual=actual_required,
                )

        for section in actual:
            matches_canonical = any(
                self._norm_name(str(section.fields.get("source", "")))
                == self._norm_name(item.source)
                and self._norm_name(str(section.fields.get("target", "")))
                == self._norm_name(item.target)
                and self._norm(str(section.fields.get("cardinality", "")))
                == self._norm(item.cardinality)
                for item in context.foundation.relationships
            )
            check(
                matches_canonical,
                code="SCV042",
                category="relationship",
                message=f"Candidate introduces non-canonical relationship {section.name}.",
                expected=[
                    item.model_dump(mode="json") for item in context.foundation.relationships
                ],
                actual=section.fields,
            )

    def _verify_roles(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = {
            self._norm_name(section.name or ""): section
            for section in document.sections_of_type("Role")
            if section.name
        }
        requirement_by_name = {
            self._norm_name(item.name): item
            for item in context.requirements.requirements
            if item.kind == "actor"
        }
        for role in context.foundation.roles:
            requirement = requirement_by_name.get(self._norm_name(role.name))
            # Inferred domain-pack roles are advisory; explicit actor semantics are protected.
            if requirement is None or requirement.origin != "explicit":
                continue
            section = actual.get(self._norm_name(role.name))
            check(
                section is not None,
                code="SCV050",
                category="role",
                message=f"Explicit canonical role {role.name} is missing.",
                expected=role.name,
                actual=sorted(item.name for item in actual.values() if item.name),
            )

    def _verify_workflows(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = list(document.sections_of_type("Workflow"))
        for workflow in context.foundation.workflows:
            match = next(
                (
                    section
                    for section in actual
                    if self._norm_name(str(section.fields.get("entity", "")))
                    == self._norm_name(workflow.entity)
                ),
                None,
            )
            check(
                match is not None,
                code="SCV060",
                category="workflow",
                message=f"Workflow for canonical entity {workflow.entity} is missing.",
                expected=workflow.model_dump(mode="json"),
                actual=[item.fields for item in actual],
            )
            if match is None:
                continue
            for key, expected_values in {
                "states": workflow.states,
                "transitions": workflow.transitions,
                "actions": workflow.actions,
            }.items():
                actual_values = match.fields.get(key, [])
                if not isinstance(actual_values, list):
                    actual_values = []
                expected_normalized = {self._norm(str(item)) for item in expected_values}
                actual_normalized = {self._norm(str(item)) for item in actual_values}
                check(
                    expected_normalized.issubset(actual_normalized),
                    code="SCV061",
                    category="workflow",
                    message=f"Workflow {workflow.name} does not preserve canonical {key}.",
                    expected=sorted(expected_normalized),
                    actual=sorted(actual_normalized),
                )

    def _verify_business_rules(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = [
            *document.sections_of_type("BusinessRule"),
            *document.sections_of_type("Invariant"),
        ]
        for rule in context.foundation.business_rules:
            match = next(
                (
                    section
                    for section in actual
                    if self._norm(str(section.fields.get("rule", ""))) == self._norm(rule.rule)
                    and self._norm_name(str(section.fields.get("entity", "")))
                    == self._norm_name(rule.entity or "")
                ),
                None,
            )
            check(
                match is not None,
                code="SCV070",
                category="business_rule",
                message=f"Canonical executable rule {rule.name} is missing or changed.",
                expected=rule.model_dump(mode="json"),
                actual=[item.fields for item in actual],
            )

        for section in actual:
            matches_canonical = any(
                self._norm(str(section.fields.get("rule", ""))) == self._norm(item.rule)
                and self._norm_name(str(section.fields.get("entity", "")))
                == self._norm_name(item.entity or "")
                for item in context.foundation.business_rules
            )
            check(
                matches_canonical,
                code="SCV071",
                category="business_rule",
                message=f"Candidate introduces non-canonical executable rule {section.name}.",
                expected=[
                    item.model_dump(mode="json") for item in context.foundation.business_rules
                ],
                actual=section.fields,
            )

    def _verify_routes(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = list(document.sections_of_type("Route"))
        for route in context.foundation.routes:
            match = next(
                (
                    section
                    for section in actual
                    if self._norm(str(section.fields.get("method", ""))) == self._norm(route.method)
                    and self._norm_path(str(section.fields.get("path", "")))
                    == self._norm_path(route.path)
                ),
                None,
            )
            check(
                match is not None,
                code="SCV080",
                category="route",
                message=f"Canonical route {route.method} {route.path} is missing.",
                expected=route.model_dump(mode="json"),
                actual=[
                    {
                        "method": item.fields.get("method"),
                        "path": item.fields.get("path"),
                    }
                    for item in actual
                ],
            )
            if match is None:
                continue
            check(
                self._norm(str(match.fields.get("auth", "required"))) == self._norm(route.auth),
                code="SCV081",
                category="route",
                message=f"Authorization contract changed for {route.method} {route.path}.",
                expected=route.auth,
                actual=match.fields.get("auth"),
            )
            expected_body = route.body
            actual_body = match.fields.get("body")
            if expected_body is None:
                expected_body = None
            if route.method in {"PATCH", "PUT"} and expected_body:
                base = re.sub(r"Create$", "", expected_body)
                allowed_bodies = {
                    self._norm_name(expected_body),
                    self._norm_name(f"{base}Update"),
                }
                body_ok = (
                    actual_body is not None and self._norm_name(str(actual_body)) in allowed_bodies
                )
            else:
                body_ok = self._schema_equivalent(expected_body, actual_body)
            check(
                body_ok,
                code="SCV082",
                category="route",
                message=f"Body schema changed for {route.method} {route.path}.",
                expected=expected_body,
                actual=actual_body,
            )
            check(
                self._schema_equivalent(route.returns, match.fields.get("returns")),
                code="SCV083",
                category="route",
                message=f"Return schema changed for {route.method} {route.path}.",
                expected=route.returns,
                actual=match.fields.get("returns"),
            )

        canonical_route_keys = {
            (self._norm(item.method), self._norm_path(item.path))
            for item in context.foundation.routes
        }
        for section in actual:
            key = (
                self._norm(str(section.fields.get("method", ""))),
                self._norm_path(str(section.fields.get("path", ""))),
            )
            check(
                key in canonical_route_keys,
                code="SCV084",
                category="route",
                message=f"Candidate introduces non-canonical route {key[0]} {key[1]}.",
                expected=sorted(canonical_route_keys),
                actual=key,
            )

    def _verify_reports(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        actual = {
            self._norm_name(section.name or "")
            for section in document.sections_of_type("Report")
            if section.name
        }
        for report in context.foundation.reports:
            check(
                self._norm_name(report) in actual,
                code="SCV090",
                category="report",
                message=f"Canonical report {report} is missing.",
                expected=report,
                actual=sorted(actual),
            )

    def _verify_required_scaffolding(
        self, context: CanonicalSemanticContext, document: SMLDocument, check: Any
    ) -> None:
        policies = list(document.sections_of_type("Policy"))
        error_policy = next(
            (item for item in policies if self._norm_name(item.name or "") == "errorhandling"),
            None,
        )
        check(
            error_policy is not None,
            code="SCV100",
            category="policy",
            message="Candidate must preserve the ErrorHandling policy section.",
        )
        if error_policy is not None:
            check(
                self._norm(str(error_policy.fields.get("broad_catch", ""))) == "forbidden",
                code="SCV102",
                category="policy",
                message="ErrorHandling broad_catch policy must remain forbidden.",
                expected="forbidden",
                actual=error_policy.fields.get("broad_catch"),
            )

        constraints = list(document.sections_of_type("Constraint"))
        architecture_constraint = next(
            (item for item in constraints if self._norm_name(item.name or "") == "architecture"),
            None,
        )
        check(
            architecture_constraint is not None,
            code="SCV101",
            category="constraint",
            message="Candidate must preserve the Architecture constraint section.",
        )
        if architecture_constraint is not None:
            expected = context.architecture.selected_pattern
            actual = architecture_constraint.fields.get("architecture")
            if actual is None:
                # ``pattern`` is a common representational alias emitted by live models.
                # Treat it as syntax-level drift while preserving exact semantic comparison.
                actual = architecture_constraint.fields.get("pattern")
            check(
                self._norm_architecture(str(actual or "")) == self._norm_architecture(expected),
                code="SCV103",
                category="constraint",
                message="Architecture constraint diverges from the canonical architecture.",
                expected=expected,
                actual=actual,
            )

    def _first(self, document: SMLDocument, section_type: str) -> SMLSection | None:
        sections = document.sections_of_type(section_type)
        return sections[0] if sections else None

    def _descriptor_tokens(self, descriptor: str) -> set[str]:
        tokens = re.split(r"\s+", descriptor.strip().lower())
        return {token for token in tokens if token}

    def _schema_equivalent(self, expected: Any, actual: Any) -> bool:
        expected_norm = self._norm_schema(expected)
        actual_norm = self._norm_schema(actual)
        return expected_norm == actual_norm

    def _norm_schema(self, value: Any) -> str:
        if value is None:
            return "none"
        return self._norm_name(str(value).replace("[]", "array"))

    def _norm_path(self, value: str) -> str:
        return re.sub(r"/+", "/", value.strip().lower()).rstrip("/") or "/"

    def _norm(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _norm_name(self, value: str) -> str:
        return "".join(character.lower() for character in value if character.isalnum())

    def _norm_architecture(self, value: str) -> str:
        normalized = self._norm_name(value)
        aliases = {
            "layered": "layeredmodularmonolith",
            "layeredmodularmonolith": "layeredmodularmonolith",
        }
        return aliases.get(normalized, normalized)


def build_canonical_semantic_context(
    *,
    source_name: str,
    source_sha256: str,
    requirements: Any,
    foundation: Any,
    architecture: Any,
    capabilities: Any,
    negotiation: Any,
) -> CanonicalSemanticContext:
    """Construct and fingerprint the deterministic semantic authority object."""

    context_issues = _context_integrity_issues(foundation)
    protected = [
        f"stack.backend={foundation.backend}",
        f"stack.database={foundation.database}",
        f"stack.auth={foundation.auth}",
        f"tenant.enabled={str(foundation.tenant_enabled).lower()}",
        f"audit.enabled={str(foundation.audit_enabled).lower()}",
        *[f"entity:{entity.name}" for entity in foundation.entities],
        *[f"workflow:{workflow.name}" for workflow in foundation.workflows],
        *[f"rule:{rule.name}" for rule in foundation.business_rules],
        *[f"route:{route.method}:{route.path}" for route in foundation.routes],
    ]
    unresolved = [
        *[item.description for item in requirements.ambiguities],
        *[item.description for item in requirements.contradictions],
        *list(foundation.questions),
        *list(negotiation.unsupported_features),
    ]
    base = CanonicalSemanticContext(
        source_name=source_name,
        source_sha256=source_sha256,
        requirements=requirements,
        foundation=foundation,
        architecture=architecture,
        capabilities=capabilities,
        negotiation=negotiation,
        protected_semantics=sorted(set(protected)),
        unresolved_semantics=sorted(set(unresolved)),
        context_issues=context_issues,
    )
    payload = base.model_dump(mode="json", exclude={"semantic_fingerprint"})
    return base.model_copy(update={"semantic_fingerprint": sha256_value(payload)})


def canonical_context_prompt(context: CanonicalSemanticContext, *, repair_issue: str = "") -> str:
    """Serialize the only semantic payload an online SML synthesizer may consume."""

    payload = json.dumps(context.llm_payload(), indent=2, sort_keys=True)
    capabilities = "\n".join(
        f"#Capability {capability}\nstatus: requested"
        for capability in context.foundation.domain_pack_candidates
    )
    capability_block = capabilities or "#Capability generic_crud\nstatus: requested"
    architecture = (
        "layered"
        if context.architecture.selected_pattern == "layered_modular_monolith"
        else context.architecture.selected_pattern
    )
    representation = (
        "MANDATORY SML REPRESENTATION ENVELOPE (deterministically derived from the canonical "
        "context; this adds no new product semantics):\n"
        "- Emit every capability section exactly as listed below; do not omit them.\n"
        f"{capability_block}\n"
        "- Preserve this policy exactly:\n"
        "#Policy ErrorHandling\n"
        "broad_catch: forbidden\n"
        "- Preserve this architecture constraint using the `architecture` key:\n"
        "#Constraint Architecture\n"
        f"architecture: {architecture}\n"
        "Do not replace `architecture:` with `pattern:` and do not rename capability IDs."
    )
    repair = ""
    if repair_issue:
        repair = (
            "\n\nREPAIR DIAGNOSTICS FROM DETERMINISTIC VERIFIERS:\n"
            f"{repair_issue}\n"
            "Repair only the SML representation. Do not alter the canonical semantics. "
            "Apply every diagnostic literally when an exact expected value is supplied."
        )
    return (
        "Generate SML from the canonical semantic context below. The context is authoritative. "
        "Do not reinterpret the original user request, invent domain entities, remove required "
        "semantics, or silently resolve listed uncertainty. Return only the required JSON object.\n\n"
        f"{representation}\n\n"
        "CANONICAL SEMANTIC CONTEXT:\n"
        f"{payload}{repair}"
    )


def _context_integrity_issues(foundation: Any) -> list[str]:
    issues: list[str] = []
    entities = {entity.name for entity in foundation.entities}
    for relationship in foundation.relationships:
        if relationship.source not in entities or relationship.target not in entities:
            issues.append(
                f"relationship {relationship.name} references undeclared entity "
                f"{relationship.source}->{relationship.target}"
            )
    for workflow in foundation.workflows:
        if workflow.entity not in entities:
            issues.append(
                f"workflow {workflow.name} references undeclared entity {workflow.entity}"
            )
    for rule in foundation.business_rules:
        if rule.entity and rule.entity not in entities:
            issues.append(f"rule {rule.name} references undeclared entity {rule.entity}")
    return sorted(set(issues))


def conformance_error_messages(report: SemanticConformanceReport) -> Iterable[str]:
    for item in report.diagnostics:
        if item.severity == "error":
            yield f"{item.code} [{item.category}] {item.message}"
