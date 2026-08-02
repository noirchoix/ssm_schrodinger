from __future__ import annotations

from ssm.capabilities.schemas import CapabilityPackSpec

_PACKS: dict[str, CapabilityPackSpec] = {
    "rbac": CapabilityPackSpec(
        capability_id="rbac",
        description="Generated role and permission runtime.",
        triggers=["rbac", "role", "permission"],
        guarantees=["role_permission_map", "authorization_decisions"],
        generated_artifacts=["app/platform/rbac.py"],
        required_tests=["platform_rbac_test"],
        required_evidence=["app_contract.roles"],
        implementation_status="production",
    ),
    "tenant_isolation": CapabilityPackSpec(
        capability_id="tenant_isolation",
        description="Tenant context propagation and tenant-scoped repositories.",
        triggers=["tenant", "multi-tenant", "tenant isolation"],
        prerequisites=["rbac"],
        guarantees=["tenant_context", "tenant_scoped_storage"],
        generated_artifacts=["app/platform/tenancy.py"],
        required_tests=["tenant_isolation_test"],
        required_evidence=["app_contract.tenant_scope"],
        implementation_status="production",
    ),
    "audit": CapabilityPackSpec(
        capability_id="audit",
        description="Persistent or in-memory audit event capture.",
        triggers=["audit", "audit log", "audit trail"],
        guarantees=["mutation_audit_events", "tenant_partitioned_audit_reads"],
        generated_artifacts=["app/platform/audit.py"],
        required_tests=["audit_persistence_test"],
        required_evidence=["app_contract.audit_storage"],
        implementation_status="production",
    ),
    "workflow": CapabilityPackSpec(
        capability_id="workflow",
        description="State-machine transition and business-rule runtime.",
        triggers=["workflow", "approval", "approve", "reject"],
        prerequisites=["audit"],
        guarantees=["transition_enforcement", "business_rule_evaluation"],
        generated_artifacts=["app/platform/workflow.py"],
        required_tests=["workflow_transition_test"],
        required_evidence=["app_contract.workflows"],
        implementation_status="production",
    ),
    "observability": CapabilityPackSpec(
        capability_id="observability",
        description="Request IDs, structured logging, readiness, and health evidence.",
        triggers=["observability", "metrics", "tracing", "structured logging"],
        guarantees=["request_id", "structured_logging", "readiness_endpoint"],
        generated_artifacts=["app/core/logging.py", "app/platform/readiness.py"],
        required_tests=["readiness_test", "request_id_test"],
        required_evidence=["eval_run.expected_gates"],
        implementation_status="production",
    ),
    "background_jobs": CapabilityPackSpec(
        capability_id="background_jobs",
        description="Durable asynchronous job execution contract.",
        triggers=["background job", "worker", "queue", "celery", "asynchronous"],
        prerequisites=["observability"],
        guarantees=["job_contract", "retry_classification"],
        assumptions=[
            "A durable broker and worker target are not generated in the current FastAPI pack."
        ],
        generated_artifacts=[],
        required_tests=["job_idempotency_test", "job_retry_test"],
        required_evidence=["capability_report.background_jobs"],
        implementation_status="contract_only",
    ),
    "notifications": CapabilityPackSpec(
        capability_id="notifications",
        description="Notification intent, template, and delivery-boundary contract.",
        triggers=["notification", "notify", "email alert"],
        prerequisites=["background_jobs"],
        guarantees=["notification_contract"],
        assumptions=["External email/SMS delivery remains an adapter responsibility."],
        generated_artifacts=[],
        required_tests=["notification_contract_test"],
        required_evidence=["capability_report.notifications"],
        implementation_status="contract_only",
    ),
    "idempotency": CapabilityPackSpec(
        capability_id="idempotency",
        description="Idempotency-key and duplicate-command handling contract.",
        triggers=["idempotency", "idempotent", "duplicate request"],
        guarantees=["idempotency_contract", "duplicate_command_classification"],
        assumptions=["Persistent idempotency-key storage is not yet emitted by the target pack."],
        generated_artifacts=[],
        required_tests=["duplicate_request_test"],
        required_evidence=["capability_report.idempotency"],
        implementation_status="contract_only",
    ),
    "webhooks": CapabilityPackSpec(
        capability_id="webhooks",
        description="Outbound webhook delivery contract.",
        triggers=["webhook"],
        prerequisites=["background_jobs", "idempotency", "observability"],
        guarantees=["signed_webhook_contract", "delivery_attempt_model"],
        assumptions=["Durable delivery and signing adapters are scaffolds only."],
        generated_artifacts=[],
        required_tests=["webhook_signature_test", "webhook_retry_test"],
        required_evidence=["capability_report.webhooks"],
        implementation_status="scaffold",
    ),
    "soft_delete_retention": CapabilityPackSpec(
        capability_id="soft_delete_retention",
        description="Soft deletion and data-retention policy contract.",
        triggers=["soft delete", "retention", "data retention"],
        guarantees=["retention_policy_contract", "deletion_state_contract"],
        assumptions=["Entity-level deleted_at fields and purge jobs are not yet emitted."],
        generated_artifacts=[],
        required_tests=["soft_delete_visibility_test", "retention_policy_test"],
        required_evidence=["capability_report.retention"],
        implementation_status="contract_only",
    ),
}


def all_capability_packs() -> dict[str, CapabilityPackSpec]:
    return {key: value.model_copy(deep=True) for key, value in _PACKS.items()}


def get_capability_pack(capability_id: str) -> CapabilityPackSpec | None:
    pack = _PACKS.get(capability_id)
    return pack.model_copy(deep=True) if pack else None
