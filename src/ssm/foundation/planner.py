from __future__ import annotations

import re

from ssm.domain_packs.registry import select_domain_packs
from ssm.foundation.schemas import (
    AppBusinessRule,
    AppEntity,
    AppFoundationPlan,
    AppRelationship,
    AppRole,
    AppRoute,
    AppWorkflow,
)


def _title_from_prompt(prompt: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", prompt)
    if not words:
        return "Generated Application"
    important = [w for w in words if w.lower() not in {"build", "a", "an", "the", "with"}]
    return " ".join(important[:4]).title() or "Generated Application"


class AppFoundationPlanner:
    """Deterministic app-foundation planner.

    The planner turns an app idea into a bounded, compiler-negotiable foundation
    plan. Online LLMs may produce this schema later, but the offline planner is
    deliberately conservative and reproducible.
    """

    def plan(self, prompt: str) -> AppFoundationPlan:
        lower = prompt.lower()
        packs = select_domain_packs(prompt)
        pack_ids = [pack.id for pack in packs]
        entities = self._entities_for_prompt(lower)
        routes = self._routes_for_entities(entities, lower)
        workflows = self._workflows_for_prompt(lower)
        rules = self._rules_for_prompt(lower)
        relationships = self._relationships_for_prompt(lower, {entity.name for entity in entities})
        roles = self._roles_for_packs(pack_ids)
        unsupported = self._unsupported_features(lower)
        return AppFoundationPlan(
            app_name=_title_from_prompt(prompt),
            description=prompt,
            app_type=pack_ids[0] if pack_ids else "generic",
            domain_pack_candidates=pack_ids,
            entities=entities,
            relationships=relationships,
            roles=roles,
            workflows=workflows,
            business_rules=rules,
            routes=routes,
            reports=self._reports_for_prompt(lower),
            nonfunctional_requirements=[
                "OpenAPI contract tests",
                "Docker support",
                "GitHub Actions CI",
                "coverage gates",
                "security scans",
                "request IDs",
                "structured logging",
            ],
            unsupported_features=unsupported,
            assumptions=[
                "Planner generated a bounded backend foundation, not a complete custom product.",
                "Unsupported integrations are surfaced before deterministic code generation.",
            ],
            questions=self._questions_for_prompt(lower),
            backend="FastAPI",
            database="PostgreSQL" if "postgres" in lower or "saas" in lower else "InMemory",
            auth="JWT"
            if any(word in lower for word in ["auth", "jwt", "saas", "login"])
            else "JWT",
            tenant_enabled="saas" in lower or "tenant" in lower,
            audit_enabled="audit" in lower or "approval" in lower or "saas" in lower,
        )

    def _entities_for_prompt(self, lower: str) -> list[AppEntity]:
        if "leave" in lower or "hr" in lower or "employee" in lower:
            return [
                AppEntity(
                    name="Employee",
                    fields={
                        "id": "uuid primary",
                        "name": "string required max=120",
                        "email": "string unique required max=180",
                        "leave_balance": "int default=0",
                    },
                    create_fields={
                        "name": "string required max=120",
                        "email": "string unique required max=180",
                        "leave_balance": "int default=0",
                    },
                ),
                AppEntity(
                    name="LeaveRequest",
                    fields={
                        "id": "uuid primary",
                        "employee_id": "uuid required",
                        "requested_days": "int required",
                        "status": "string required max=40 default=draft",
                    },
                    create_fields={
                        "employee_id": "uuid required",
                        "requested_days": "int required",
                        "status": "string required max=40 default=draft",
                    },
                ),
            ]
        if "expense" in lower or "receipt" in lower or "reimbursement" in lower:
            return [
                AppEntity(
                    name="ExpenseClaim",
                    fields={
                        "id": "uuid primary",
                        "employee_name": "string required max=120",
                        "amount": "float required",
                        "status": "string required max=40 default=draft",
                    },
                    create_fields={
                        "employee_name": "string required max=120",
                        "amount": "float required",
                        "status": "string required max=40 default=draft",
                    },
                )
            ]
        if "crm" in lower or "deal" in lower or "lead" in lower:
            return [
                AppEntity(
                    name="Lead",
                    fields={
                        "id": "uuid primary",
                        "name": "string required max=120",
                        "email": "string unique required max=180",
                        "stage": "string required max=40 default=new",
                    },
                    create_fields={
                        "name": "string required max=120",
                        "email": "string unique required max=180",
                        "stage": "string required max=40 default=new",
                    },
                ),
                AppEntity(
                    name="Deal",
                    fields={
                        "id": "uuid primary",
                        "lead_id": "uuid required",
                        "amount": "float default=0",
                        "stage": "string required max=40 default=qualified",
                    },
                    create_fields={
                        "lead_id": "uuid required",
                        "amount": "float default=0",
                        "stage": "string required max=40 default=qualified",
                    },
                ),
            ]
        if "ticket" in lower or "helpdesk" in lower or "support" in lower:
            return [
                AppEntity(
                    name="Ticket",
                    fields={
                        "id": "uuid primary",
                        "title": "string required max=160",
                        "status": "string required max=40 default=open",
                        "priority": "string required max=40 default=normal",
                    },
                    create_fields={
                        "title": "string required max=160",
                        "status": "string required max=40 default=open",
                        "priority": "string required max=40 default=normal",
                    },
                )
            ]
        if "school" in lower or "student" in lower or "course" in lower:
            return [
                AppEntity(
                    name="Student",
                    fields={
                        "id": "uuid primary",
                        "name": "string required max=120",
                        "student_number": "string unique required max=60",
                    },
                    create_fields={
                        "name": "string required max=120",
                        "student_number": "string unique required max=60",
                    },
                ),
                AppEntity(
                    name="Course",
                    fields={
                        "id": "uuid primary",
                        "title": "string required max=160",
                        "code": "string unique required max=40",
                    },
                    create_fields={
                        "title": "string required max=160",
                        "code": "string unique required max=40",
                    },
                ),
            ]
        if "todo" in lower and "inventory" not in lower:
            return [
                AppEntity(
                    name="Todo",
                    fields={
                        "id": "uuid primary",
                        "title": "string required max=120",
                        "completed": "bool default=false",
                    },
                    create_fields={
                        "title": "string required max=120",
                        "completed": "bool default=false",
                    },
                )
            ]
        return [
            AppEntity(
                name="Product",
                fields={
                    "id": "uuid primary",
                    "name": "string required max=120",
                    "sku": "string unique required max=80",
                    "quantity": "int default=0",
                },
                create_fields={
                    "name": "string required max=120",
                    "sku": "string unique required max=80",
                    "quantity": "int default=0",
                },
            )
        ]

    def _routes_for_entities(self, entities: list[AppEntity], lower: str) -> list[AppRoute]:
        routes: list[AppRoute] = []
        wants_crud = any(word in lower for word in ["crud", "update", "delete", "full"])
        for entity in entities[:2]:
            plural = self._plural(entity.name)
            create = f"{entity.name}Create"
            routes.extend(
                [
                    AppRoute(
                        name=f"List{plural.title().replace(' ', '')}",
                        method="GET",
                        path=f"/{plural}",
                        returns=f"{entity.name}[]",
                    ),
                    AppRoute(
                        name=f"Create{entity.name}",
                        method="POST",
                        path=f"/{plural}",
                        body=create,
                        returns=entity.name,
                    ),
                ]
            )
            if wants_crud:
                routes.extend(
                    [
                        AppRoute(
                            name=f"Get{entity.name}",
                            method="GET",
                            path=f"/{plural}/{{id}}",
                            returns=entity.name,
                        ),
                        AppRoute(
                            name=f"Update{entity.name}",
                            method="PATCH",
                            path=f"/{plural}/{{id}}",
                            body=create,
                            returns=entity.name,
                        ),
                        AppRoute(
                            name=f"Delete{entity.name}",
                            method="DELETE",
                            path=f"/{plural}/{{id}}",
                            returns=entity.name,
                        ),
                    ]
                )
        return routes

    def _workflows_for_prompt(self, lower: str) -> list[AppWorkflow]:
        if any(word in lower for word in ["approval", "approve", "leave", "expense"]):
            entity = "LeaveRequest" if "leave" in lower else "ExpenseClaim"
            return [
                AppWorkflow(
                    name=f"{entity}Approval",
                    entity=entity,
                    states=["draft", "submitted", "approved", "rejected"],
                    transitions=[
                        "draft -> submitted",
                        "submitted -> approved",
                        "submitted -> rejected",
                    ],
                    actions=["submit", "approve", "reject"],
                )
            ]
        if any(word in lower for word in ["ticket", "helpdesk"]):
            return [
                AppWorkflow(
                    name="TicketLifecycle",
                    entity="Ticket",
                    states=["open", "assigned", "resolved", "closed", "reopened"],
                    transitions=["open -> assigned", "assigned -> resolved", "resolved -> closed"],
                    actions=["assign", "resolve", "close", "reopen"],
                )
            ]
        return []

    def _rules_for_prompt(self, lower: str) -> list[AppBusinessRule]:
        rules: list[AppBusinessRule] = []
        if "leave" in lower:
            rules.append(
                AppBusinessRule(
                    name="LeaveBalanceCannotGoNegative",
                    entity="LeaveRequest",
                    rule="requested_days <= employee.leave_balance",
                )
            )
        if "stock" in lower or "inventory" in lower:
            rules.append(
                AppBusinessRule(
                    name="PreventNegativeStock",
                    entity="Product",
                    rule="quantity >= 0",
                )
            )
        if "expense" in lower:
            rules.append(
                AppBusinessRule(
                    name="ExpenseAmountMustBePositive",
                    entity="ExpenseClaim",
                    rule="amount >= 0",
                )
            )
        return rules

    def _relationships_for_prompt(
        self, lower: str, entity_names: set[str]
    ) -> list[AppRelationship]:
        relationships: list[AppRelationship] = []
        if {"Employee", "LeaveRequest"}.issubset(entity_names):
            relationships.append(
                AppRelationship(
                    name="EmployeeLeaveRequests",
                    source="LeaveRequest",
                    target="Employee",
                    cardinality="many-to-one",
                )
            )
        if {"Lead", "Deal"}.issubset(entity_names):
            relationships.append(
                AppRelationship(
                    name="LeadDeals",
                    source="Deal",
                    target="Lead",
                    cardinality="many-to-one",
                )
            )
        if "supplier" in lower and "Product" in entity_names:
            relationships.append(
                AppRelationship(
                    name="ProductSupplier",
                    source="Product",
                    target="Supplier",
                    cardinality="many-to-one",
                )
            )
        return relationships

    def _roles_for_packs(self, pack_ids: list[str]) -> list[AppRole]:
        role_names: list[str] = []
        for pack_id in pack_ids:
            if pack_id == "hr":
                role_names.extend(["admin", "hr_admin", "manager", "employee"])
            elif pack_id == "expense":
                role_names.extend(["admin", "finance_manager", "approver", "employee"])
            elif pack_id == "ticketing":
                role_names.extend(["admin", "agent", "requester", "viewer"])
            else:
                role_names.extend(["admin", "manager", "viewer"])
        if not role_names:
            role_names = ["admin", "manager", "viewer"]
        unique = sorted(set(role_names))
        return [
            AppRole(name=name, permissions=["read", "write"] if name != "viewer" else ["read"])
            for name in unique
        ]

    def _reports_for_prompt(self, lower: str) -> list[str]:
        reports = []
        if "report" in lower or "dashboard" in lower:
            reports.append("OperationalSummary")
        if "inventory" in lower:
            reports.append("LowStockSummary")
        return reports

    def _unsupported_features(self, lower: str) -> list[str]:
        unsupported = []
        for keyword in ["payment", "stripe", "tax", "shipping carrier", "email integration"]:
            if keyword in lower:
                unsupported.append(keyword)
        return unsupported

    def _questions_for_prompt(self, lower: str) -> list[str]:
        questions = []
        if "approval" in lower and "manager" not in lower:
            questions.append("Which role is allowed to approve submitted records?")
        if "tenant" not in lower and "saas" in lower:
            questions.append("Should all business records be tenant-scoped?")
        return questions

    def _plural(self, entity_name: str) -> str:
        lowered = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", entity_name)
        lowered = re.sub("([a-z0-9])([A-Z])", r"\1_\2", lowered).lower()
        if lowered.endswith("y"):
            return lowered[:-1] + "ies"
        if lowered.endswith("s"):
            return lowered
        return lowered + "s"
