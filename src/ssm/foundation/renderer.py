from __future__ import annotations

from ssm.foundation.schemas import AppEntity, AppFoundationPlan


class FoundationSMLRenderer:
    """Render AppFoundationPlan into deterministic SML."""

    def render(self, plan: AppFoundationPlan) -> str:
        lines: list[str] = [
            "#Project",
            f"name: {plan.app_name}",
            f"description: {plan.description}",
            "",
            "#Stack",
            f"backend: {plan.backend}",
            f"database: {plan.database}",
            f"auth: {plan.auth}",
            "",
        ]
        for pack in plan.domain_pack_candidates:
            lines.extend([f"#Capability {pack}", "status: requested", ""])
        if plan.tenant_enabled:
            lines.extend(["#Tenant", "enabled: true", "scope: organization", ""])
        if plan.audit_enabled:
            lines.extend(["#Audit", "enabled: true", "events: mutation", ""])
        for role in plan.roles:
            lines.extend([f"#Role {self._pascal(role.name)}", "permissions:"])
            lines.extend([f"  - {permission}" for permission in role.permissions])
            lines.append("")
        for entity in plan.entities:
            lines.extend(self._entity_sections(entity))
        for relationship in plan.relationships:
            lines.extend(
                [
                    f"#Relationship {relationship.name}",
                    f"source: {relationship.source}",
                    f"target: {relationship.target}",
                    f"cardinality: {relationship.cardinality}",
                    f"required: {str(relationship.required).lower()}",
                    "",
                ]
            )
        for workflow in plan.workflows:
            lines.extend(
                [
                    f"#Workflow {workflow.name}",
                    f"entity: {workflow.entity}",
                    "states:",
                ]
            )
            lines.extend([f"  - {state}" for state in workflow.states])
            lines.append("transitions:")
            lines.extend([f"  - {transition}" for transition in workflow.transitions])
            lines.append("actions:")
            lines.extend([f"  - {action}" for action in workflow.actions])
            lines.append("")
        for rule in plan.business_rules:
            section_type = "Invariant" if rule.on_violation == "reject" else "BusinessRule"
            lines.extend(
                [
                    f"#{section_type} {rule.name}",
                    *([f"entity: {rule.entity}"] if rule.entity else []),
                    f"rule: {rule.rule}",
                    f"on_violation: {rule.on_violation}",
                    "",
                ]
            )
        for route in plan.routes:
            lines.extend(
                [
                    f"#Route {route.name}",
                    f"method: {route.method}",
                    f"path: {route.path}",
                    f"auth: {route.auth}",
                ]
            )
            if route.body:
                lines.append(f"body: {route.body}")
            else:
                lines.append("body: none")
            if route.returns:
                lines.append(f"returns: {route.returns}")
            lines.append("")
        for report in plan.reports:
            lines.extend([f"#Report {report}", "type: query_view", ""])
        lines.extend(
            [
                "#Policy ErrorHandling",
                "broad_catch: forbidden",
                "",
                "#Constraint Architecture",
                "architecture: layered",
                "",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def _entity_sections(self, entity: AppEntity) -> list[str]:
        lines = [f"#DataModel {entity.name}", "fields:"]
        for name, descriptor in entity.fields.items():
            lines.append(f"  {name}: {descriptor}")
        lines.append("")
        create_fields = entity.create_fields
        if create_fields is None:
            create_fields = {
                name: descriptor
                for name, descriptor in entity.fields.items()
                if "primary" not in descriptor.lower()
            }
        lines.extend([f"#DataModel {entity.name}Create", "fields:"])
        for name, descriptor in create_fields.items():
            lines.append(f"  {name}: {descriptor}")
        lines.append("")
        return lines

    def _pascal(self, value: str) -> str:
        return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)
