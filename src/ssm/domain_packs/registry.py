from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ssm.foundation.schemas import AppFoundationPlan


@dataclass(frozen=True)
class DomainPack:
    id: str
    label: str
    keywords: tuple[str, ...]
    default_entities: tuple[str, ...]
    default_roles: tuple[str, ...]
    workflow_verbs: tuple[str, ...] = ()
    allowed_methods: tuple[str, ...] = ("GET", "POST", "PATCH", "PUT", "DELETE")
    unsupported_keywords: tuple[str, ...] = ()
    default_nonfunctional: tuple[str, ...] = (
        "OpenAPI contract tests",
        "Docker support",
        "GitHub Actions CI",
        "coverage gates",
        "security scans",
    )

    def score_prompt(self, prompt: str) -> int:
        lower = prompt.lower()
        return sum(1 for keyword in self.keywords if keyword in lower)

    def supports_method(self, method: str) -> bool:
        return method.upper() in self.allowed_methods


_DOMAIN_PACKS: dict[str, DomainPack] = {
    "generic_crud": DomainPack(
        id="generic_crud",
        label="Generic CRUD API",
        keywords=("crud", "api", "backend", "records", "manage", "create", "update", "delete"),
        default_entities=("Resource",),
        default_roles=("admin", "manager", "viewer"),
    ),
    "workflow_approval": DomainPack(
        id="workflow_approval",
        label="Workflow Approval",
        keywords=("approval", "approve", "reject", "submit", "workflow", "request"),
        default_entities=("Request",),
        default_roles=("admin", "manager", "requester", "viewer"),
        workflow_verbs=("submit", "approve", "reject", "cancel"),
    ),
    "inventory": DomainPack(
        id="inventory",
        label="Inventory Operations",
        keywords=("inventory", "product", "sku", "stock", "warehouse", "supplier"),
        default_entities=("Product", "Warehouse", "Supplier"),
        default_roles=("admin", "inventory_manager", "viewer"),
        workflow_verbs=("receive", "adjust", "reserve", "release"),
    ),
    "hr": DomainPack(
        id="hr",
        label="HR Operations",
        keywords=("hr", "employee", "leave", "onboarding", "manager", "absence"),
        default_entities=("Employee", "LeaveRequest"),
        default_roles=("admin", "hr_admin", "manager", "employee"),
        workflow_verbs=("submit", "approve", "reject", "cancel"),
    ),
    "expense": DomainPack(
        id="expense",
        label="Expense Approval",
        keywords=("expense", "claim", "reimbursement", "receipt", "finance"),
        default_entities=("ExpenseClaim", "Receipt"),
        default_roles=("admin", "finance_manager", "approver", "employee"),
        workflow_verbs=("submit", "approve", "reject", "reimburse"),
    ),
    "crm": DomainPack(
        id="crm",
        label="CRM Pipeline",
        keywords=("crm", "lead", "deal", "customer", "pipeline", "opportunity"),
        default_entities=("Lead", "Deal", "Customer"),
        default_roles=("admin", "sales_manager", "sales_rep", "viewer"),
        workflow_verbs=("qualify", "propose", "win", "lose"),
    ),
    "procurement": DomainPack(
        id="procurement",
        label="Procurement Workflow",
        keywords=("procurement", "purchase", "supplier", "po", "purchase order"),
        default_entities=("Supplier", "PurchaseOrder", "PurchaseOrderLine"),
        default_roles=("admin", "buyer", "approver", "viewer"),
        workflow_verbs=("submit", "approve", "receive", "cancel"),
    ),
    "ticketing": DomainPack(
        id="ticketing",
        label="Ticketing Helpdesk",
        keywords=("ticket", "helpdesk", "support", "issue", "incident"),
        default_entities=("Ticket", "Comment"),
        default_roles=("admin", "agent", "requester", "viewer"),
        workflow_verbs=("assign", "resolve", "close", "reopen"),
    ),
    "school": DomainPack(
        id="school",
        label="School Records",
        keywords=("school", "student", "class", "course", "attendance", "teacher"),
        default_entities=("Student", "Course", "Enrollment"),
        default_roles=("admin", "teacher", "registrar", "viewer"),
    ),
}


def all_domain_packs() -> dict[str, DomainPack]:
    return dict(_DOMAIN_PACKS)


def get_domain_pack(pack_id: str) -> DomainPack | None:
    return _DOMAIN_PACKS.get(pack_id)


def select_domain_packs(prompt: str, *, minimum: int = 1, maximum: int = 3) -> list[DomainPack]:
    scored = sorted(
        ((pack.score_prompt(prompt), pack.id, pack) for pack in _DOMAIN_PACKS.values()),
        key=lambda item: (-item[0], item[1]),
    )
    selected = [pack for score, _, pack in scored if score > 0][:maximum]
    if len(selected) < minimum:
        generic = _DOMAIN_PACKS["generic_crud"]
        if generic not in selected:
            selected.append(generic)
    return selected[:maximum]


def packs_for_plan(plan: AppFoundationPlan) -> list[DomainPack]:
    packs: list[DomainPack] = []
    for pack_id in plan.domain_pack_candidates:
        pack = get_domain_pack(pack_id)
        if pack is not None:
            packs.append(pack)
    if not packs:
        packs = select_domain_packs(plan.description or plan.app_name)
    if "generic_crud" not in {pack.id for pack in packs}:
        packs.append(_DOMAIN_PACKS["generic_crud"])
    return _dedupe(packs)


def _dedupe(packs: Iterable[DomainPack]) -> list[DomainPack]:
    seen: set[str] = set()
    result: list[DomainPack] = []
    for pack in packs:
        if pack.id in seen:
            continue
        seen.add(pack.id)
        result.append(pack)
    return result
