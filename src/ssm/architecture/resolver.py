from __future__ import annotations

import hashlib
import json
import re

from ssm.architecture.schemas import (
    ArchitectureCandidate,
    ArchitectureModule,
    ArchitecturePlan,
    ArchitectureProof,
    DomainEventSpec,
    FailureModelSpec,
    IntegrationAdapterSpec,
    NonFunctionalRequirementSpec,
    TransactionBoundary,
    UseCaseSpec,
)
from ssm.foundation.schemas import AppFoundationPlan
from ssm.requirements.schemas import RequirementsIR

_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class ConstrainedArchitectureResolver:
    """Resolve a plan into a bounded architecture using explicit candidates.

    The current FastAPI target is a modular layered monolith. Alternatives are
    recorded and rejected rather than silently invented.
    """

    def resolve(
        self, requirements: RequirementsIR, foundation: AppFoundationPlan
    ) -> ArchitecturePlan:
        mutating = any(route.method in _MUTATING_METHODS for route in foundation.routes)
        needs_service_layer = bool(
            mutating
            or foundation.workflows
            or foundation.business_rules
            or foundation.audit_enabled
            or foundation.tenant_enabled
        )
        candidates = [
            ArchitectureCandidate(
                id="arch.direct_route_repository",
                pattern="direct_route_repository",
                status="rejected" if needs_service_layer else "admissible",
                score=0.25,
                reasons=(
                    [
                        "Rejected because workflows, business rules, tenancy, audit, or mutations require explicit application boundaries."
                    ]
                    if needs_service_layer
                    else ["Admissible only for trivial read-only applications."]
                ),
            ),
            ArchitectureCandidate(
                id="arch.layered_modular_monolith",
                pattern="layered_modular_monolith",
                status="selected",
                score=1.0,
                reasons=[
                    "Matches the deterministic FastAPI target pack.",
                    "Preserves route, application-service, repository, and platform boundaries.",
                    "Supports explicit transaction and failure semantics.",
                ],
            ),
            ArchitectureCandidate(
                id="arch.microservices",
                pattern="microservices",
                status="rejected",
                score=0.1,
                reasons=[
                    "No independently deployable bounded contexts or operational requirements justify distributed services.",
                    "The current target stack certifies a modular monolith, not distributed transactions.",
                ],
            ),
        ]
        modules = self._modules(foundation)
        use_cases = self._use_cases(requirements, foundation)
        transactions = [
            TransactionBoundary(
                id=f"tx.{use_case.id}",
                use_case_id=use_case.id,
                consistency_scope=[use_case.entity] if use_case.entity else [],
            )
            for use_case in use_cases
            if use_case.transaction_required
        ]
        events = self._events(use_cases)
        integrations = self._integrations(requirements)
        nfrs = self._nfrs(foundation)
        proof = ArchitectureProof(
            decision_id="architecture.pattern",
            claim="Select the least-complex architecture satisfying declared semantics and current target guarantees.",
            selected_candidate_id="arch.layered_modular_monolith",
            rejected_candidate_ids=[item.id for item in candidates if item.status == "rejected"],
            support=[
                f"entities={len(foundation.entities)}",
                f"mutating_routes={sum(route.method in _MUTATING_METHODS for route in foundation.routes)}",
                f"workflows={len(foundation.workflows)}",
                f"business_rules={len(foundation.business_rules)}",
                f"tenant_enabled={foundation.tenant_enabled}",
                f"audit_enabled={foundation.audit_enabled}",
            ],
        )
        plan = ArchitecturePlan(
            selected_pattern="layered_modular_monolith",
            modules=modules,
            use_cases=use_cases,
            transaction_boundaries=transactions,
            events=events,
            integration_adapters=integrations,
            failure_models=self._failure_models(),
            nonfunctional_requirements=nfrs,
            candidates=candidates,
            proof=proof,
        )
        plan.semantic_fingerprint = self._fingerprint(plan)
        return plan

    def _modules(self, foundation: AppFoundationPlan) -> list[ArchitectureModule]:
        entities = [entity.name for entity in foundation.entities]
        modules = [
            ArchitectureModule(
                id="module.api",
                name="API",
                responsibility="HTTP contracts, authentication dependencies, validation, and response mapping.",
                entities=entities,
                dependencies=["module.application", "module.platform"],
            ),
            ArchitectureModule(
                id="module.application",
                name="Application",
                responsibility="Use-case orchestration, authorization, transactions, and business-rule execution.",
                entities=entities,
                dependencies=["module.domain", "module.persistence", "module.platform"],
            ),
            ArchitectureModule(
                id="module.domain",
                name="Domain",
                responsibility="Entity schemas, invariants, workflows, and domain semantics.",
                entities=entities,
            ),
            ArchitectureModule(
                id="module.persistence",
                name="Persistence",
                responsibility="Repository contracts, database sessions, migrations, and tenant scoping.",
                entities=entities,
                dependencies=["module.domain"],
            ),
            ArchitectureModule(
                id="module.platform",
                name="Platform",
                responsibility="RBAC, tenancy, audit, readiness, workflow runtime, and configuration.",
                dependencies=["module.domain"],
            ),
        ]
        return modules

    def _use_cases(
        self, requirements: RequirementsIR, foundation: AppFoundationPlan
    ) -> list[UseCaseSpec]:
        requirement_by_token = {item.name.lower(): item.id for item in requirements.requirements}
        actors = [role.name for role in foundation.roles]
        default_actor = actors[0] if actors else "AuthenticatedUser"
        result: list[UseCaseSpec] = []
        for route in foundation.routes:
            entity = self._route_entity(route.name, route.body, route.returns)
            command = self._command(route.method, route.name)
            use_case_id = f"usecase.{self._safe_id(route.name)}"
            requirement_ids = {
                req_id
                for token, req_id in requirement_by_token.items()
                if token and token in route.name.lower()
            }
            if entity:
                requirement_ids.update(foundation.requirement_trace.get(f"entity.{entity}", []))
            event_name = f"{entity}{command}ed" if entity else f"{command}Completed"
            result.append(
                UseCaseSpec(
                    id=use_case_id,
                    name=route.name,
                    actor=default_actor,
                    entity=entity,
                    command=command,
                    authorization=(
                        "authenticated_role_permission"
                        if route.auth == "required"
                        else "public_or_optional"
                    ),
                    transaction_required=route.method in _MUTATING_METHODS,
                    preconditions=["request schema valid", "authorization satisfied"],
                    failure_modes=self._route_failures(route.method),
                    emits_events=[event_name] if route.method in _MUTATING_METHODS else [],
                    requirement_ids=sorted(requirement_ids),
                )
            )
        for workflow in foundation.workflows:
            for action in workflow.actions:
                name = f"{self._pascal(action)}{workflow.entity}"
                use_case_id = f"usecase.{self._safe_id(name)}"
                result.append(
                    UseCaseSpec(
                        id=use_case_id,
                        name=name,
                        actor=default_actor,
                        entity=workflow.entity,
                        command=action,
                        authorization="workflow_action_permission",
                        transaction_required=True,
                        preconditions=[
                            "current state permits action",
                            "applicable business rules pass",
                        ],
                        failure_modes=[
                            "FORBIDDEN",
                            "STATE_CONFLICT",
                            "BUSINESS_RULE_REJECTED",
                        ],
                        emits_events=[f"{workflow.name}.{action}"],
                        requirement_ids=foundation.requirement_trace.get(
                            f"workflow.{workflow.name}", []
                        ),
                    )
                )
        deduped = {item.id: item for item in result}
        return sorted(deduped.values(), key=lambda item: item.id)

    def _events(self, use_cases: list[UseCaseSpec]) -> list[DomainEventSpec]:
        events: list[DomainEventSpec] = []
        for use_case in use_cases:
            for event_name in use_case.emits_events:
                events.append(
                    DomainEventSpec(
                        id=f"event.{self._safe_id(event_name)}",
                        name=event_name,
                        producer_use_case_id=use_case.id,
                        payload_fields=["resource_id", "actor", "tenant_id"],
                        delivery="in_process",
                    )
                )
        return sorted({item.id: item for item in events}.values(), key=lambda item: item.id)

    def _integrations(self, requirements: RequirementsIR) -> list[IntegrationAdapterSpec]:
        result: list[IntegrationAdapterSpec] = []
        for item in requirements.requirements:
            if item.kind != "integration":
                continue
            result.append(
                IntegrationAdapterSpec(
                    id=f"integration.{self._safe_id(item.name)}",
                    name=item.name,
                    boundary="outbound_adapter",
                    status=("unsupported" if item.status == "unsupported" else "external_contract"),
                    timeout_policy="required_before implementation",
                    retry_policy="required before implementation",
                    idempotency_policy="required for mutating integrations",
                )
            )
        return result

    def _nfrs(self, foundation: AppFoundationPlan) -> list[NonFunctionalRequirementSpec]:
        result: list[NonFunctionalRequirementSpec] = []
        for index, item in enumerate(sorted(set(foundation.nonfunctional_requirements)), start=1):
            result.append(
                NonFunctionalRequirementSpec(
                    id=f"nfr.{index:03d}",
                    name=item,
                    measurable_obligation=self._nfr_obligation(item),
                    evidence_gate=self._nfr_gate(item),
                )
            )
        return result

    def _failure_models(self) -> list[FailureModelSpec]:
        return [
            FailureModelSpec(code="VALIDATION_ERROR", category="validation", http_status=422),
            FailureModelSpec(code="UNAUTHORIZED", category="authentication", http_status=401),
            FailureModelSpec(code="FORBIDDEN", category="authorization", http_status=403),
            FailureModelSpec(code="NOT_FOUND", category="not_found", http_status=404),
            FailureModelSpec(code="CONFLICT", category="conflict", http_status=409),
            FailureModelSpec(code="STATE_CONFLICT", category="state", http_status=409),
            FailureModelSpec(
                code="BUSINESS_RULE_REJECTED", category="business_rule", http_status=409
            ),
            FailureModelSpec(
                code="DEPENDENCY_UNAVAILABLE",
                category="dependency",
                http_status=503,
                retryable=True,
            ),
            FailureModelSpec(code="RATE_LIMITED", category="rate_limit", http_status=429),
        ]

    def _route_entity(self, route_name: str, body: str | None, returns: str | None) -> str | None:
        value = returns or body
        if value:
            return value.removesuffix("[]").removesuffix("Create").removesuffix("Update")
        tokens = re.findall(r"[A-Z][a-z0-9]*", route_name)
        return tokens[-1] if tokens else None

    def _command(self, method: str, route_name: str) -> str:
        verbs = {
            "GET": "read",
            "POST": "create",
            "PATCH": "update",
            "PUT": "replace",
            "DELETE": "delete",
        }
        return verbs.get(method, self._safe_id(route_name))

    def _route_failures(self, method: str) -> list[str]:
        failures = ["VALIDATION_ERROR", "UNAUTHORIZED", "FORBIDDEN"]
        if method in {"GET", "PATCH", "PUT", "DELETE"}:
            failures.append("NOT_FOUND")
        if method in _MUTATING_METHODS:
            failures.append("CONFLICT")
        return failures

    def _nfr_obligation(self, item: str) -> str:
        lower = item.lower()
        if "coverage" in lower:
            return "Generated test coverage meets configured threshold."
        if "security" in lower:
            return "Static security gates report no blocking findings."
        if "openapi" in lower:
            return "Generated OpenAPI contract matches declared routes."
        if "docker" in lower:
            return "Generated container configuration builds from a clean context."
        return f"Evidence exists for: {item}."

    def _nfr_gate(self, item: str) -> str:
        lower = item.lower()
        if "coverage" in lower:
            return "pytest_cov"
        if "security" in lower:
            return "bandit_and_dependency_audit"
        if "openapi" in lower:
            return "openapi_contract_tests"
        if "docker" in lower:
            return "docker_build"
        if "logging" in lower or "request id" in lower:
            return "runtime_probe"
        return "evidence_record"

    def _fingerprint(self, plan: ArchitecturePlan) -> str:
        payload = plan.model_dump(exclude={"semantic_fingerprint"})
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _safe_id(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "unnamed"

    def _pascal(self, value: str) -> str:
        return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", value) if part)
