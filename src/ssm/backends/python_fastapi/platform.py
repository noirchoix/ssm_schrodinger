from __future__ import annotations

import hashlib
import json
import re
from pprint import pformat
from textwrap import dedent
from typing import Any

from ssm.models import CompileManifest, GeneratedFile, ResolutionResult, SIRGraph
from ssm.semantic.field_parser import normalize_schema_name

EVIDENCE_RECORD_NAMES = [
    "generated_app_manifest.json",
    "app_contract.json",
    "eval_run.json",
    "capability_report.json",
    "assumptions.json",
    "unsupported_features.json",
    "provenance_hashes.json",
    "evidence_bundle.json",
]


def platform_source_files(graph: SIRGraph, repo_strategy: str) -> list[GeneratedFile]:
    workflows = _workflow_specs(graph)
    rules = _rule_specs(graph)
    roles = _role_specs(graph)
    tenant_enabled = _section_enabled(graph, "Tenant")
    audit_enabled = _section_enabled(graph, "Audit")
    sqlalchemy_enabled = repo_strategy == "sqlalchemy"
    files = [
        GeneratedFile(path="app/platform/__init__.py", content=""),
        GeneratedFile(
            path="app/platform/tenancy.py", content=_tenancy_py(tenant_enabled, sqlalchemy_enabled)
        ),
        GeneratedFile(path="app/platform/rbac.py", content=_rbac_py(roles)),
        GeneratedFile(
            path="app/platform/audit.py", content=_audit_py(audit_enabled, sqlalchemy_enabled)
        ),
        GeneratedFile(
            path="app/platform/workflow.py",
            content=_workflow_py(workflows, rules, sqlalchemy_enabled),
        ),
        GeneratedFile(path="app/platform/readiness.py", content=_readiness_py()),
        GeneratedFile(
            path="app/api/routes/platform.py",
            content=_platform_routes_py(sqlalchemy_enabled),
        ),
        GeneratedFile(path="app/cli/__init__.py", content=""),
        GeneratedFile(
            path="app/cli/seed_admin.py",
            content=_seed_admin_py(sqlalchemy_enabled),
        ),
    ]
    if sqlalchemy_enabled:
        files.append(
            GeneratedFile(
                path="app/platform/models.py",
                content=_platform_models_py(
                    tenant_enabled, audit_enabled, bool(workflows), sqlalchemy_enabled
                ),
            )
        )
    files.extend(_admin_ui_files(graph))
    return files


def platform_migration_files(graph: SIRGraph, repo_strategy: str) -> list[GeneratedFile]:
    if repo_strategy != "sqlalchemy":
        return []
    return [
        GeneratedFile(
            path="app/db/migrations/versions/0002_platform_runtime.py",
            content=_platform_migration_py(
                tenant_enabled=_section_enabled(graph, "Tenant"),
                audit_enabled=_section_enabled(graph, "Audit"),
                workflow_enabled=bool(_workflow_specs(graph)),
            ),
        )
    ]


def evidence_record_files(
    graph: SIRGraph,
    resolution: ResolutionResult,
    manifest: CompileManifest,
    generated_files: list[GeneratedFile],
) -> list[GeneratedFile]:
    del resolution
    capabilities = _capability_specs(graph)
    assumptions = _assumption_specs(graph)
    unsupported = _unsupported_features(graph)
    roles = _role_specs(graph)
    workflows = _workflow_specs(graph)
    rules = _rule_specs(graph)
    tenant_enabled = _section_enabled(graph, "Tenant")
    audit_enabled = _section_enabled(graph, "Audit")
    route_specs = _route_specs(graph)
    entity_specs = _entity_specs(graph)
    content_hashes = {
        item.path: hashlib.sha256(item.content.encode("utf-8")).hexdigest()
        for item in sorted(generated_files, key=lambda file: file.path)
        if item.path not in EVIDENCE_RECORD_NAMES
        and item.path not in {"sml.manifest.json", "docs/release_evidence.md"}
    }

    generated_app_manifest = {
        "schema_version": "2.0",
        "kind": "GeneratedAppManifest",
        "platform_release": "2.0.0-dev",
        "compiler": {
            "version": manifest.compiler_version,
            "target": manifest.target,
        },
        "hashes": {
            "sml_sha256": manifest.sml_hash,
            "sir_sha256": manifest.sir_hash,
            "resolved_ir_sha256": manifest.resolved_ir_hash,
        },
        "generated_files": manifest.generated_files,
        "selected_candidates": manifest.selected_candidates,
        "proof_count": manifest.proof_count,
    }
    acceptance_gates = [
        "pytest",
        "coverage",
        "ruff",
        "ruff_format",
        "mypy",
        "compileall",
        "bandit",
        "pip_audit",
        "alembic_cycle",
        "tenant_isolation",
        "audit_persistence",
        "workflow_orchestration",
        "admin_typecheck",
        "admin_build",
        "online_repair_trace",
        "secret_scan",
    ]
    app_contract = {
        "schema_version": "2.0",
        "kind": "AppContract",
        "project": _project_spec(graph),
        "stack": _stack_spec(graph),
        "entities": entity_specs,
        "routes": route_specs,
        "tenant_enabled": tenant_enabled,
        "tenant_scope": "all_route_owned_entities" if tenant_enabled else "disabled",
        "audit_enabled": audit_enabled,
        "audit_storage": "database" if _uses_sqlalchemy(graph) else "memory",
        "roles": roles,
        "workflows": workflows,
        "business_rules": rules,
        "admin": {
            "kind": "react-vite",
            "crud_pages": True,
            "openapi_client": True,
            "auth_aware": True,
            "tenant_aware": tenant_enabled,
        },
        "acceptance_gates": acceptance_gates,
    }
    capability_report = {
        "schema_version": "2.0",
        "kind": "CapabilityReport",
        "requested_capabilities": capabilities,
        "supported_features": [
            "crud",
            "relationship_metadata",
            "full_tenant_scoped_repositories",
            "rbac_role_permission_runtime",
            "database_backed_audit_persistence",
            "workflow_state_persistence",
            "workflow_transition_enforcement",
            "business_rule_evaluation",
            "generated_admin_crud_ui",
            "generated_openapi_client",
            "production_frontend_build_pipeline",
            "bounded_online_repair_loop",
            "evidence_records_with_file_provenance",
        ],
        "partially_supported_features": [],
        "unsupported_features": unsupported,
    }
    eval_run = {
        "schema_version": "2.0",
        "kind": "EvalRunRecord",
        "status": "ACCEPTANCE_GATES_REQUIRED",
        "deterministic_compile": True,
        "expected_gates": acceptance_gates,
        "notes": [
            "This record is emitted at compile time; the V2.0 E2E release gate supplies runtime evidence.",
            "Online model output remains limited to SML drafts and repairs.",
        ],
    }
    assumptions_doc = {
        "schema_version": "2.0",
        "kind": "Assumptions",
        "items": assumptions,
    }
    unsupported_doc = {
        "schema_version": "2.0",
        "kind": "UnsupportedFeatures",
        "items": unsupported,
    }
    provenance_hashes = {
        "schema_version": "2.0",
        "kind": "ProvenanceHashes",
        "compiler_input_hashes": generated_app_manifest["hashes"],
        "selected_candidates": manifest.selected_candidates,
        "generated_file_sha256": content_hashes,
        "hash_algorithm": "sha256",
    }
    evidence_bundle = {
        "schema_version": "2.0",
        "kind": "ReleaseEvidenceBundle",
        "records": EVIDENCE_RECORD_NAMES[:-1],
        "summary": {
            "entity_count": len(entity_specs),
            "route_count": len(route_specs),
            "workflow_count": len(workflows),
            "business_rule_count": len(rules),
            "role_count": len(roles),
            "tenant_enabled": tenant_enabled,
            "audit_enabled": audit_enabled,
            "provenance_file_count": len(content_hashes),
        },
    }
    payloads: dict[str, dict[str, Any]] = {
        "generated_app_manifest.json": generated_app_manifest,
        "app_contract.json": app_contract,
        "eval_run.json": eval_run,
        "capability_report.json": capability_report,
        "assumptions.json": assumptions_doc,
        "unsupported_features.json": unsupported_doc,
        "provenance_hashes.json": provenance_hashes,
        "evidence_bundle.json": evidence_bundle,
    }
    files = [
        GeneratedFile(path=path, content=json.dumps(payload, indent=2, sort_keys=True) + "\n")
        for path, payload in sorted(payloads.items())
    ]
    files.append(
        GeneratedFile(path="docs/release_evidence.md", content=_release_evidence_md(payloads))
    )
    return files


def platform_test_files(
    graph: SIRGraph,
    repo_strategy: str,
) -> dict[str, str]:
    workflows = _workflow_specs(graph)
    rules = _rule_specs(graph)
    selected_workflow = workflows[0] if workflows else None
    workflow_name = selected_workflow["name"] if selected_workflow else "DefaultWorkflow"
    action = _first_valid_action(selected_workflow) if selected_workflow else "advance"
    applicable_rule_names = sorted(
        rule["name"]
        for rule in rules
        if selected_workflow is not None and rule["entity"] == selected_workflow["entity"]
    )
    expected_tenant = "tenant-a" if _section_enabled(graph, "Tenant") else "default"
    audit_enabled = _section_enabled(graph, "Audit")
    return {
        "tests/test_evidence_records.py": _evidence_tests_py(),
        "tests/test_platform_primitives.py": _platform_tests_py(
            workflow_name,
            action,
            expected_tenant,
            audit_enabled,
            bool(workflows),
            applicable_rule_names,
            repo_strategy == "sqlalchemy",
        ),
        "tests/test_admin_ui_static.py": _admin_static_tests_py(),
    }


def _project_spec(graph: SIRGraph) -> dict[str, Any]:
    project = next((node for node in graph.by_type("Project")), None)
    if project is None:
        return {"name": "GeneratedApp", "description": ""}
    return {
        "name": project.name,
        "description": str(project.attributes.get("description", "")),
    }


def _stack_spec(graph: SIRGraph) -> dict[str, Any]:
    stack = next((node for node in graph.by_type("Stack")), None)
    if stack is None:
        return {"backend": "FastAPI", "database": "InMemory", "auth": "None"}
    return {
        "backend": str(stack.attributes.get("backend", "FastAPI")),
        "database": str(stack.attributes.get("database", "InMemory")),
        "auth": str(stack.attributes.get("auth", "None")),
    }


def _uses_sqlalchemy(graph: SIRGraph) -> bool:
    database = _stack_spec(graph)["database"].lower()
    return database in {"postgresql", "postgres", "sqlite", "mysql", "mariadb"}


def _entity_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    tenant_enabled = _section_enabled(graph, "Tenant")
    route_entities = {_route_entity(node) for node in graph.by_type("Route")}
    for node in graph.by_type("DataModel"):
        if node.name.endswith(("Create", "Update")):
            continue
        fields = [
            {
                "name": field.get("name"),
                "type": field.get("raw_type") or field.get("python_type"),
                "required": bool(field.get("required")),
                "primary": bool(field.get("primary")),
                "unique": bool(field.get("unique")),
            }
            for field in node.attributes.get("fields", [])
        ]
        entities.append(
            {
                "name": node.name,
                "fields": fields,
                "tenant_scoped": tenant_enabled and node.name in route_entities,
            }
        )
    return sorted(entities, key=lambda item: item["name"])


def _route_entity(node: Any) -> str:
    returns = _none_to_none(node.attributes.get("returns"))
    body = _none_to_none(node.attributes.get("body"))
    if returns:
        return str(returns).removesuffix("Create").removesuffix("Update")
    if body:
        return str(body).removesuffix("Create").removesuffix("Update")
    path = str(node.attributes.get("path", "/")).strip("/").split("/")[0]
    token = path[:-1] if path.endswith("s") else path
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", token) if part)


def _route_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for node in graph.by_type("Route"):
        routes.append(
            {
                "name": node.name,
                "method": str(node.attributes.get("method", "GET")).upper(),
                "path": str(node.attributes.get("path", "/")),
                "auth": str(node.attributes.get("auth", "none")),
                "body": _none_to_none(node.attributes.get("body")),
                "returns": _none_to_none(node.attributes.get("returns")),
                "entity": _route_entity(node),
            }
        )
    return sorted(routes, key=lambda item: (item["path"], item["method"], item["name"]))


def _capability_specs(graph: SIRGraph) -> list[str]:
    return sorted(dict.fromkeys(node.name for node in graph.by_type("Capability")))


def _assumption_specs(graph: SIRGraph) -> list[str]:
    values = []
    for node in graph.by_type("Assumption"):
        value = node.attributes.get("text") or node.attributes.get("value") or node.name
        values.append(str(value))
    return sorted(dict.fromkeys(values))


def _unsupported_features(graph: SIRGraph) -> list[str]:
    values = []
    for node in graph.by_type("Integration"):
        status = str(node.attributes.get("status", "")).lower()
        if status in {"unsupported", "external", "manual"}:
            values.append(node.name)
    return sorted(dict.fromkeys(values))


def _role_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    roles = []
    for node in graph.by_type("Role"):
        permissions = _string_list(node.attributes.get("permissions"))
        roles.append({"name": node.name, "permissions": permissions})
    if not roles:
        roles = [
            {"name": "Admin", "permissions": ["read", "write", "admin"]},
            {"name": "Viewer", "permissions": ["read"]},
        ]
    return sorted(roles, key=lambda item: item["name"])


def _workflow_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for node in graph.by_type("Workflow") + graph.by_type("StateMachine"):
        states = _string_list(node.attributes.get("states")) or ["draft", "done"]
        transitions = _string_list(node.attributes.get("transitions"))
        actions = _string_list(node.attributes.get("actions"))
        transition_specs = _transition_specs(transitions, actions)
        workflows.append(
            {
                "name": node.name,
                "entity": str(node.attributes.get("entity", "Resource")),
                "states": states,
                "transitions": transitions,
                "actions": sorted(dict.fromkeys(item["action"] for item in transition_specs)),
                "transition_map": transition_specs,
            }
        )
    return sorted(workflows, key=lambda item: item["name"])


def _transition_specs(transitions: list[str], actions: list[str]) -> list[dict[str, str]]:
    parsed: list[tuple[str, str]] = []
    for transition in transitions:
        if "->" not in transition:
            continue
        source, target = (part.strip() for part in transition.split("->", 1))
        if source and target:
            parsed.append((source, target))
    result: list[dict[str, str]] = []
    for index, (source, target) in enumerate(parsed):
        action = (
            actions[index] if len(actions) == len(parsed) else _matching_action(actions, target)
        )
        result.append(
            {"action": action or _action_name(f"{source}_{target}"), "from": source, "to": target}
        )
    return result


def _matching_action(actions: list[str], target: str) -> str:
    normalized_target = target.lower().replace("_", "")
    for action in actions:
        normalized_action = action.lower().replace("_", "")
        if normalized_target.startswith(normalized_action) or normalized_action.startswith(
            normalized_target
        ):
            return action
    return ""


def _first_valid_action(workflow: dict[str, Any]) -> str:
    mappings = workflow.get("transition_map") or []
    return str(mappings[0]["action"]) if mappings else "advance"


def _rule_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for node in graph.by_type("BusinessRule") + graph.by_type("Invariant"):
        expression = node.attributes.get("rule") or node.attributes.get("expression")
        if not expression:
            continue
        rules.append(
            {
                "name": node.name,
                "kind": node.node_type,
                "entity": str(node.attributes.get("entity", "Resource")),
                "expression": str(expression),
                "on_violation": str(node.attributes.get("on_violation", "reject")),
            }
        )
    return sorted(rules, key=lambda item: (item["entity"], item["name"]))


def _section_enabled(graph: SIRGraph, section_type: str) -> bool:
    nodes = graph.by_type(section_type)
    if not nodes:
        return False
    value = nodes[0].attributes.get("enabled", True)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "off"}


def _none_to_none(value: Any) -> Any:
    if value is None or str(value).lower() in {"none", "null"}:
        return None
    return normalize_schema_name(str(value))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            stripped = stripped[1:-1]
        return [part.strip() for part in stripped.split(",") if part.strip()]
    return [str(value)]


def _action_name(transition: str) -> str:
    cleaned = transition.replace("->", "_")
    return re.sub(r"[^A-Za-z0-9]+", "_", cleaned).strip("_").lower() or "advance"


def _platform_models_py(
    tenant_enabled: bool,
    audit_enabled: bool,
    workflow_enabled: bool,
    sqlalchemy_enabled: bool,
) -> str:
    if not sqlalchemy_enabled:
        return dedent(f"""
            from __future__ import annotations

            TENANT_MODEL_ENABLED = {tenant_enabled!r}
            AUDIT_MODEL_ENABLED = {audit_enabled!r}
            WORKFLOW_MODEL_ENABLED = {workflow_enabled!r}
        """).lstrip()
    return dedent(f"""
        from __future__ import annotations

        from datetime import UTC, datetime
        from uuid import uuid4

        from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
        from sqlalchemy.orm import Mapped, mapped_column

        from app.db.base import Base

        TENANT_MODEL_ENABLED = {tenant_enabled!r}
        AUDIT_MODEL_ENABLED = {audit_enabled!r}
        WORKFLOW_MODEL_ENABLED = {workflow_enabled!r}


        class TenantRecord(Base):
            __tablename__ = "platform_tenants"

            tenant_id: Mapped[str] = mapped_column(String(120), primary_key=True)
            name: Mapped[str] = mapped_column(String(200), nullable=False)
            active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
            created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
            )


        class AuditEventRecord(Base):
            __tablename__ = "platform_audit_events"

            event_id: Mapped[str] = mapped_column(
                String(36), primary_key=True, default=lambda: str(uuid4())
            )
            event_type: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
            actor: Mapped[str] = mapped_column(String(160), nullable=False)
            tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
            resource_type: Mapped[str] = mapped_column(String(160), nullable=False)
            resource_id: Mapped[str] = mapped_column(String(160), nullable=False)
            payload_json: Mapped[str] = mapped_column(Text(), nullable=False, default="{{}}")
            created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
            )


        class WorkflowStateRecord(Base):
            __tablename__ = "platform_workflow_states"
            __table_args__ = (
                UniqueConstraint(
                    "tenant_id",
                    "workflow_name",
                    "resource_id",
                    name="uq_platform_workflow_resource",
                ),
            )

            state_id: Mapped[str] = mapped_column(
                String(36), primary_key=True, default=lambda: str(uuid4())
            )
            tenant_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
            workflow_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
            resource_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
            state: Mapped[str] = mapped_column(String(120), nullable=False)
            version: Mapped[int] = mapped_column(nullable=False, default=1)
            updated_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
            )
    """).lstrip()


def _tenancy_py(enabled: bool, sqlalchemy_enabled: bool) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Annotated, Any",
        "",
        "from fastapi import Header, HTTPException",
    ]
    if sqlalchemy_enabled:
        lines.extend(
            [
                "from sqlalchemy.orm import Session",
                "",
                "from app.platform.models import TenantRecord",
            ]
        )
    lines.extend(
        [
            "",
            f"TENANCY_ENABLED = {enabled!r}",
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class TenantContext:",
            '    tenant_id: str = "default"',
            "",
            "",
            "def normalize_tenant_id(value: str | None) -> str:",
            '    cleaned = (value or "default").strip()',
            '    return cleaned or "default"',
            "",
            "",
            "def tenant_key(tenant_id: str, item_id: str) -> str:",
            '    return f"{normalize_tenant_id(tenant_id)}:{item_id}"',
            "",
            "",
            "def get_tenant_context(",
            '    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,',
            ") -> TenantContext:",
            "    if not TENANCY_ENABLED:",
            "        return TenantContext()",
            "    tenant_id = normalize_tenant_id(x_tenant_id)",
            "    if len(tenant_id) > 120:",
            '        raise HTTPException(status_code=400, detail="Invalid tenant identifier")',
            "    return TenantContext(tenant_id=tenant_id)",
            "",
            "",
            "def ensure_tenant(db: Any, context: TenantContext) -> Any:",
        ]
    )
    if sqlalchemy_enabled:
        lines.extend(
            [
                "    if not TENANCY_ENABLED:",
                "        return None",
                "    if not isinstance(db, Session):",
                '        raise RuntimeError("A database session is required for tenant persistence")',
                "    row = db.get(TenantRecord, context.tenant_id)",
                "    if row is None:",
                "        row = TenantRecord(tenant_id=context.tenant_id, name=context.tenant_id)",
                "        db.add(row)",
                "        db.flush()",
                "    if not row.active:",
                '        raise HTTPException(status_code=403, detail="Tenant is inactive")',
                "    return row",
            ]
        )
    else:
        lines.extend(["    _ = db, context", "    return None"])
    return "\n".join(lines) + "\n"


def _rbac_py(roles: list[dict[str, Any]]) -> str:
    role_map = {role["name"]: sorted(role.get("permissions", [])) for role in roles}
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import asdict, dataclass",
        "",
        "from fastapi import HTTPException, status",
        "",
        "ROLE_PERMISSIONS: dict[str, set[str]] = {",
    ]
    for name, permissions in sorted(role_map.items()):
        lines.append(f"    {name!r}: {set(permissions)!r},")
    lines.extend(
        [
            "}",
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class RoleDecision:",
            "    role: str",
            "    permission: str",
            "    allowed: bool",
            "",
            "    def model_dump(self) -> dict[str, object]:",
            "        return asdict(self)",
            "",
            "",
            "def permissions_for(role: str) -> set[str]:",
            "    return set(ROLE_PERMISSIONS.get(role, set()))",
            "",
            "",
            "def has_permission(role: str, permission: str) -> bool:",
            "    permissions = permissions_for(role)",
            "    return permission in permissions or 'admin' in permissions",
            "",
            "",
            "def authorize(roles: list[str], scopes: list[str], permission: str) -> None:",
            "    if 'admin' in scopes or permission in scopes:",
            "        return",
            "    if any(has_permission(role, permission) for role in roles):",
            "        return",
            "    raise HTTPException(",
            "        status_code=status.HTTP_403_FORBIDDEN,",
            "        detail=f'Missing permission: {permission}',",
            "    )",
            "",
            "",
            "def decide(role: str, permission: str) -> RoleDecision:",
            "    return RoleDecision(",
            "        role=role,",
            "        permission=permission,",
            "        allowed=has_permission(role, permission),",
            "    )",
        ]
    )
    return "\n".join(lines) + "\n"


def _audit_py(enabled: bool, sqlalchemy_enabled: bool) -> str:
    enabled_literal = repr(enabled)
    if sqlalchemy_enabled:
        # This is a generated Python source template. Keeping it non-interpolated also
        # avoids treating the embedded SQLAlchemy expression as constructed SQL.
        template = dedent("""
            from __future__ import annotations

            import json
            from dataclasses import asdict, dataclass
            from datetime import UTC, datetime
            from typing import Any
            from uuid import uuid4

            from sqlalchemy import select
            from sqlalchemy.orm import Session

            from app.platform.models import AuditEventRecord

            AUDIT_ENABLED = __AUDIT_ENABLED__


            @dataclass(frozen=True, slots=True)
            class AuditEvent:
                event_id: str
                event_type: str
                actor: str
                tenant_id: str
                resource_type: str
                resource_id: str
                payload: dict[str, Any]
                created_at: str

                def model_dump(self) -> dict[str, Any]:
                    return asdict(self)


            class AuditLog:
                def record(
                    self,
                    *,
                    event_type: str,
                    actor: str = "system",
                    tenant_id: str = "default",
                    resource_type: str = "platform",
                    resource_id: str = "-",
                    payload: dict[str, Any] | None = None,
                    db: Session | None = None,
                ) -> AuditEvent:
                    event = AuditEvent(
                        event_id=str(uuid4()),
                        event_type=event_type,
                        actor=actor,
                        tenant_id=tenant_id,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        payload=dict(payload or {}),
                        created_at=datetime.now(UTC).isoformat(),
                    )
                    if AUDIT_ENABLED:
                        if db is None:
                            raise RuntimeError("A database session is required for audit persistence")
                        db.add(
                            AuditEventRecord(
                                event_id=event.event_id,
                                event_type=event.event_type,
                                actor=event.actor,
                                tenant_id=event.tenant_id,
                                resource_type=event.resource_type,
                                resource_id=event.resource_id,
                                payload_json=json.dumps(event.payload, sort_keys=True, default=str),
                                created_at=datetime.fromisoformat(event.created_at),
                            )
                        )
                        db.flush()
                    return event

                def list(
                    self,
                    *,
                    tenant_id: str = "default",
                    db: Session | None = None,
                    limit: int = 500,
                ) -> list[AuditEvent]:
                    if not AUDIT_ENABLED:
                        return []
                    if db is None:
                        raise RuntimeError("A database session is required for audit persistence")
                    stmt = (
                        select(AuditEventRecord)
                        .where(AuditEventRecord.tenant_id == tenant_id)
                        .order_by(AuditEventRecord.created_at.desc())
                        .limit(limit)
                    )
                    rows = db.execute(stmt).scalars().all()
                    return [
                        AuditEvent(
                            event_id=row.event_id,
                            event_type=row.event_type,
                            actor=row.actor,
                            tenant_id=row.tenant_id,
                            resource_type=row.resource_type,
                            resource_id=row.resource_id,
                            payload=json.loads(row.payload_json),
                            created_at=row.created_at.isoformat(),
                        )
                        for row in rows
                    ]

                def clear(self, *, db: Session | None = None) -> None:
                    _ = db


            audit_log = AuditLog()
        """).lstrip()
        return template.replace("__AUDIT_ENABLED__", enabled_literal)

    template = dedent("""
        from __future__ import annotations

        from dataclasses import asdict, dataclass
        from datetime import UTC, datetime
        from threading import RLock
        from typing import Any
        from uuid import uuid4

        AUDIT_ENABLED = __AUDIT_ENABLED__


        @dataclass(frozen=True, slots=True)
        class AuditEvent:
            event_id: str
            event_type: str
            actor: str
            tenant_id: str
            resource_type: str
            resource_id: str
            payload: dict[str, Any]
            created_at: str

            def model_dump(self) -> dict[str, Any]:
                return asdict(self)


        class AuditLog:
            def __init__(self) -> None:
                self._events: list[AuditEvent] = []
                self._lock = RLock()

            def record(
                self,
                *,
                event_type: str,
                actor: str = "system",
                tenant_id: str = "default",
                resource_type: str = "platform",
                resource_id: str = "-",
                payload: dict[str, Any] | None = None,
                db: object | None = None,
            ) -> AuditEvent:
                _ = db
                event = AuditEvent(
                    event_id=str(uuid4()),
                    event_type=event_type,
                    actor=actor,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    payload=dict(payload or {}),
                    created_at=datetime.now(UTC).isoformat(),
                )
                if AUDIT_ENABLED:
                    with self._lock:
                        self._events.append(event)
                return event

            def list(
                self,
                *,
                tenant_id: str = "default",
                db: object | None = None,
                limit: int = 500,
            ) -> list[AuditEvent]:
                _ = db
                with self._lock:
                    events = [event for event in self._events if event.tenant_id == tenant_id]
                    return list(reversed(events[-limit:]))

            def clear(self, *, db: object | None = None) -> None:
                _ = db
                with self._lock:
                    self._events.clear()


        audit_log = AuditLog()
    """).lstrip()
    return template.replace("__AUDIT_ENABLED__", enabled_literal)


def _workflow_py(
    workflows: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    sqlalchemy_enabled: bool,
) -> str:
    if not workflows:
        return dedent("""
            from __future__ import annotations

            from dataclasses import asdict, dataclass
            from typing import Any, Mapping

            WORKFLOWS: list[dict[str, Any]] = []
            BUSINESS_RULES: list[dict[str, Any]] = []


            @dataclass(frozen=True, slots=True)
            class TransitionResult:
                workflow: str
                resource_id: str
                action: str
                from_state: str = "unknown"
                to_state: str = "unknown"
                allowed: bool = False
                version: int = 0
                reason: str = "unknown_workflow"
                rules: list[object] | None = None

                def model_dump(self) -> dict[str, object]:
                    return asdict(self)


            class WorkflowRuntime:
                def list(self) -> list[dict[str, Any]]:
                    return []

                def clear(self, *, db: object | None = None) -> None:
                    _ = db

                def transition(
                    self,
                    workflow_name: str,
                    resource_id: str,
                    action: str,
                    *,
                    tenant_id: str = "default",
                    expected_state: str | None = None,
                    context: Mapping[str, Any] | None = None,
                    actor: str = "system",
                    db: object | None = None,
                ) -> TransitionResult:
                    _ = tenant_id, expected_state, context, actor, db
                    return TransitionResult(
                        workflow=workflow_name,
                        resource_id=resource_id,
                        action=action,
                    )


            workflow_runtime = WorkflowRuntime()


            def list_workflows() -> list[dict[str, Any]]:
                return workflow_runtime.list()
        """).lstrip()
    db_type = "Session | None" if sqlalchemy_enabled else "object | None"
    lines = [
        "from __future__ import annotations",
        "",
        "import ast",
        "from dataclasses import asdict, dataclass",
        "from typing import Any, Mapping",
    ]
    if sqlalchemy_enabled:
        lines.extend(
            [
                "from datetime import UTC, datetime",
                "",
                "from sqlalchemy import select",
                "from sqlalchemy.orm import Session",
            ]
        )
    lines.extend(["", "from app.platform.audit import audit_log"])
    if sqlalchemy_enabled:
        lines.append("from app.platform.models import WorkflowStateRecord")
    lines.extend(
        [
            "",
            f"WORKFLOWS: list[dict[str, Any]] = {pformat(workflows, width=88)}",
            f"BUSINESS_RULES: list[dict[str, Any]] = {pformat(rules, width=88)}",
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class RuleResult:",
            "    name: str",
            "    expression: str",
            "    passed: bool",
            '    detail: str = ""',
            "",
            "",
            "@dataclass(frozen=True, slots=True)",
            "class TransitionResult:",
            "    workflow: str",
            "    resource_id: str",
            "    action: str",
            "    from_state: str",
            "    to_state: str",
            "    allowed: bool",
            "    version: int",
            "    reason: str",
            "    rules: list[RuleResult]",
            "",
            "    def model_dump(self) -> dict[str, object]:",
            "        payload = asdict(self)",
            '        payload["rules"] = [asdict(rule) for rule in self.rules]',
            "        return payload",
            "",
            "",
            "class _ContextResolver:",
            "    def __init__(self, values: Mapping[str, Any]) -> None:",
            "        self.values = values",
            "",
            "    def resolve(self, node: ast.AST) -> Any:",
            "        if isinstance(node, ast.Constant):",
            "            return node.value",
            "        if isinstance(node, ast.Name):",
            "            if node.id not in self.values:",
            "                raise KeyError(node.id)",
            "            return self.values[node.id]",
            "        if isinstance(node, ast.Attribute):",
            "            parent = self.resolve(node.value)",
            "            if isinstance(parent, Mapping):",
            "                if node.attr not in parent:",
            "                    raise KeyError(node.attr)",
            "                return parent[node.attr]",
            "            return getattr(parent, node.attr)",
            "        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):",
            "            return not bool(self.resolve(node.operand))",
            "        if isinstance(node, ast.BoolOp):",
            "            values = [bool(self.resolve(item)) for item in node.values]",
            "            return all(values) if isinstance(node.op, ast.And) else any(values)",
            "        if isinstance(node, ast.BinOp):",
            "            left = self.resolve(node.left)",
            "            right = self.resolve(node.right)",
            "            operations = {",
            "                ast.Add: lambda: left + right,",
            "                ast.Sub: lambda: left - right,",
            "                ast.Mult: lambda: left * right,",
            "                ast.Div: lambda: left / right,",
            "            }",
            "            operation = operations.get(type(node.op))",
            "            if operation is None:",
            '                raise ValueError("Unsupported binary operator")',
            "            return operation()",
            "        if isinstance(node, ast.Compare):",
            "            left = self.resolve(node.left)",
            "            for operator, comparator in zip(node.ops, node.comparators, strict=True):",
            "                right = self.resolve(comparator)",
            "                if isinstance(operator, ast.Eq):",
            "                    passed = left == right",
            "                elif isinstance(operator, ast.NotEq):",
            "                    passed = left != right",
            "                elif isinstance(operator, ast.Lt):",
            "                    passed = left < right",
            "                elif isinstance(operator, ast.LtE):",
            "                    passed = left <= right",
            "                elif isinstance(operator, ast.Gt):",
            "                    passed = left > right",
            "                elif isinstance(operator, ast.GtE):",
            "                    passed = left >= right",
            "                elif isinstance(operator, ast.In):",
            "                    passed = left in right",
            "                elif isinstance(operator, ast.NotIn):",
            "                    passed = left not in right",
            "                else:",
            '                    raise ValueError("Unsupported comparison operator")',
            "                if not passed:",
            "                    return False",
            "                left = right",
            "            return True",
            '        raise ValueError(f"Unsupported rule syntax: {type(node).__name__}")',
            "",
            "",
            "def evaluate_rule(expression: str, context: Mapping[str, Any]) -> tuple[bool, str]:",
            "    try:",
            '        tree = ast.parse(expression, mode="eval")',
            '        return bool(_ContextResolver(context).resolve(tree.body)), ""',
            "    except (KeyError, AttributeError) as exc:",
            '        return False, f"Missing rule context: {exc}"',
            "    except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as exc:",
            '        return False, f"Rule evaluation failed: {exc}"',
            "",
            "",
            "class WorkflowRuntime:",
            "    def __init__(self) -> None:",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("        pass")
    else:
        lines.append("        self._states: dict[tuple[str, str, str], tuple[str, int]] = {}")
    lines.extend(
        [
            "",
            "    def _load_state(",
            "        self,",
            "        workflow_name: str,",
            "        resource_id: str,",
            "        tenant_id: str,",
            "        initial_state: str,",
            f"        db: {db_type},",
            "    ) -> tuple[str, int]:",
        ]
    )
    if sqlalchemy_enabled:
        lines.extend(
            [
                "        if not isinstance(db, Session):",
                '            raise RuntimeError("A database session is required for workflow persistence")',
                "        stmt = select(WorkflowStateRecord).where(",
                "            WorkflowStateRecord.tenant_id == tenant_id,",
                "            WorkflowStateRecord.workflow_name == workflow_name,",
                "            WorkflowStateRecord.resource_id == resource_id,",
                "        )",
                "        row = db.execute(stmt).scalar_one_or_none()",
                "        return (row.state, row.version) if row is not None else (initial_state, 0)",
            ]
        )
    else:
        lines.extend(
            [
                "        _ = db",
                "        return self._states.get(",
                "            (tenant_id, workflow_name, resource_id),",
                "            (initial_state, 0),",
                "        )",
            ]
        )
    lines.extend(
        [
            "",
            "    def _save_state(",
            "        self,",
            "        workflow_name: str,",
            "        resource_id: str,",
            "        tenant_id: str,",
            "        state: str,",
            "        version: int,",
            f"        db: {db_type},",
            "    ) -> None:",
        ]
    )
    if sqlalchemy_enabled:
        lines.extend(
            [
                "        if not isinstance(db, Session):",
                '            raise RuntimeError("A database session is required for workflow persistence")',
                "        stmt = select(WorkflowStateRecord).where(",
                "            WorkflowStateRecord.tenant_id == tenant_id,",
                "            WorkflowStateRecord.workflow_name == workflow_name,",
                "            WorkflowStateRecord.resource_id == resource_id,",
                "        )",
                "        row = db.execute(stmt).scalar_one_or_none()",
                "        if row is None:",
                "            row = WorkflowStateRecord(",
                "                tenant_id=tenant_id,",
                "                workflow_name=workflow_name,",
                "                resource_id=resource_id,",
                "                state=state,",
                "                version=version,",
                "            )",
                "            db.add(row)",
                "        else:",
                "            row.state = state",
                "            row.version = version",
                "            row.updated_at = datetime.now(UTC)",
                "        db.flush()",
            ]
        )
    else:
        lines.extend(
            [
                "        _ = db",
                "        self._states[(tenant_id, workflow_name, resource_id)] = (state, version)",
            ]
        )
    lines.extend(["", f"    def clear(self, *, db: {db_type} = None) -> None:"])
    if sqlalchemy_enabled:
        lines.extend(["        _ = db"])
    else:
        lines.extend(["        _ = db", "        self._states.clear()"])
    lines.extend(
        [
            "",
            "    def list(self) -> list[dict[str, Any]]:",
            "        return WORKFLOWS",
            "",
            "    def transition(",
            "        self,",
            "        workflow_name: str,",
            "        resource_id: str,",
            "        action: str,",
            "        *,",
            '        tenant_id: str = "default",',
            "        expected_state: str | None = None,",
            "        context: Mapping[str, Any] | None = None,",
            '        actor: str = "system",',
            f"        db: {db_type} = None,",
            "    ) -> TransitionResult:",
            "        workflow = next(",
            '            (item for item in WORKFLOWS if item["name"] == workflow_name),',
            "            None,",
            "        )",
            "        if workflow is None:",
            "            return TransitionResult(",
            "                workflow=workflow_name,",
            "                resource_id=resource_id,",
            "                action=action,",
            '                from_state="unknown",',
            '                to_state="unknown",',
            "                allowed=False,",
            "                version=0,",
            '                reason="unknown_workflow",',
            "                rules=[],",
            "            )",
            '        states = list(workflow.get("states") or ["draft", "done"])',
            "        current_state, version = self._load_state(",
            "            workflow_name, resource_id, tenant_id, states[0], db",
            "        )",
            "        if expected_state is not None and expected_state != current_state:",
            "            return TransitionResult(",
            "                workflow=workflow_name,",
            "                resource_id=resource_id,",
            "                action=action,",
            "                from_state=current_state,",
            "                to_state=current_state,",
            "                allowed=False,",
            "                version=version,",
            '                reason="state_conflict",',
            "                rules=[],",
            "            )",
            "        mapping = next(",
            "            (",
            "                item",
            '                for item in workflow.get("transition_map", [])',
            '                if item["action"] == action and item["from"] == current_state',
            "            ),",
            "            None,",
            "        )",
            "        if mapping is None:",
            "            return TransitionResult(",
            "                workflow=workflow_name,",
            "                resource_id=resource_id,",
            "                action=action,",
            "                from_state=current_state,",
            "                to_state=current_state,",
            "                allowed=False,",
            "                version=version,",
            '                reason="transition_not_allowed",',
            "                rules=[],",
            "            )",
            "        rule_results: list[RuleResult] = []",
            "        for rule in BUSINESS_RULES:",
            '            if rule.get("entity") != workflow.get("entity"):',
            "                continue",
            '            passed, detail = evaluate_rule(str(rule["expression"]), context or {})',
            "            rule_results.append(",
            "                RuleResult(",
            '                    name=str(rule["name"]),',
            '                    expression=str(rule["expression"]),',
            "                    passed=passed,",
            "                    detail=detail,",
            "                )",
            "            )",
            "        if any(not rule.passed for rule in rule_results):",
            "            return TransitionResult(",
            "                workflow=workflow_name,",
            "                resource_id=resource_id,",
            "                action=action,",
            "                from_state=current_state,",
            "                to_state=current_state,",
            "                allowed=False,",
            "                version=version,",
            '                reason="business_rule_rejected",',
            "                rules=rule_results,",
            "            )",
            '        next_state = str(mapping["to"])',
            "        next_version = version + 1",
            "        self._save_state(",
            "            workflow_name,",
            "            resource_id,",
            "            tenant_id,",
            "            next_state,",
            "            next_version,",
            "            db,",
            "        )",
            "        audit_log.record(",
            "            db=db,",
            '            event_type="workflow.transition",',
            "            actor=actor,",
            "            tenant_id=tenant_id,",
            '            resource_type=str(workflow.get("entity", "Resource")),',
            "            resource_id=resource_id,",
            "            payload={",
            '                "workflow": workflow_name,',
            '                "action": action,',
            '                "from_state": current_state,',
            '                "to_state": next_state,',
            '                "version": next_version,',
            "            },",
            "        )",
            "        return TransitionResult(",
            "            workflow=workflow_name,",
            "            resource_id=resource_id,",
            "            action=action,",
            "            from_state=current_state,",
            "            to_state=next_state,",
            "            allowed=True,",
            "            version=next_version,",
            '            reason="accepted",',
            "            rules=rule_results,",
            "        )",
            "",
            "",
            "workflow_runtime = WorkflowRuntime()",
            "",
            "",
            "def list_workflows() -> list[dict[str, Any]]:",
            "    return workflow_runtime.list()",
        ]
    )
    return "\n".join(lines) + "\n"


def _readiness_py() -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "import json",
        "from pathlib import Path",
        "from typing import Any",
        "",
        "REQUIRED_EVIDENCE = [",
    ]
    for name in EVIDENCE_RECORD_NAMES:
        lines.append(f"    {name!r},")
    lines.extend(
        [
            "]",
            "",
            "",
            "def platform_readiness(root: Path) -> dict[str, Any]:",
            "    missing = [name for name in REQUIRED_EVIDENCE if not (root / name).exists()]",
            "    invalid: list[str] = []",
            "    for name in REQUIRED_EVIDENCE:",
            "        path = root / name",
            "        if not path.exists():",
            "            continue",
            "        try:",
            '            payload = json.loads(path.read_text(encoding="utf-8"))',
            "        except (OSError, json.JSONDecodeError):",
            "            invalid.append(name)",
            "            continue",
            '        if not isinstance(payload, dict) or not payload.get("kind"):',
            "            invalid.append(name)",
            "    return {",
            '        "ready": not missing and not invalid,',
            '        "missing_evidence": missing,',
            '        "invalid_evidence": invalid,',
            "    }",
        ]
    )
    return "\n".join(lines) + "\n"


def _platform_routes_py(sqlalchemy_enabled: bool) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "import json",
        "from pathlib import Path",
        "from typing import Annotated, Any",
        "",
        "from fastapi import APIRouter, Body, Depends, Query",
    ]
    if sqlalchemy_enabled:
        lines.extend(
            [
                "from sqlalchemy.orm import Session",
                "",
                "from app.db.session import get_db",
            ]
        )
    lines.extend(
        [
            "from app.platform.audit import audit_log",
            "from app.platform.rbac import ROLE_PERMISSIONS, decide",
            "from app.platform.tenancy import TenantContext, ensure_tenant, get_tenant_context",
            "from app.platform.workflow import list_workflows, workflow_runtime",
            "",
            'router = APIRouter(prefix="/platform", tags=["platform"])',
            "TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("DbSession = Annotated[Session, Depends(get_db)]")
    lines.extend(
        [
            "_ROOT = Path(__file__).resolve().parents[3]",
            "",
            "",
            "def _json_record(name: str) -> dict[str, Any]:",
            '    payload = json.loads((_ROOT / name).read_text(encoding="utf-8"))',
            "    if not isinstance(payload, dict):",
            '        raise ValueError(f"Evidence record {name} must be a JSON object")',
            "    return dict(payload)",
            "",
            "",
            '@router.get("/manifest", response_model=dict[str, Any])',
            "def generated_manifest() -> dict[str, Any]:",
            '    return _json_record("generated_app_manifest.json")',
            "",
            "",
            '@router.get("/contract", response_model=dict[str, Any])',
            "def app_contract() -> dict[str, Any]:",
            '    return _json_record("app_contract.json")',
            "",
            "",
            '@router.get("/capabilities", response_model=dict[str, Any])',
            "def capability_report() -> dict[str, Any]:",
            '    return _json_record("capability_report.json")',
            "",
            "",
            '@router.get("/tenant/current", response_model=dict[str, str])',
            "def current_tenant(",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db: DbSession,")
    lines.extend(["    tenant: TenantDep,", ") -> dict[str, str]:"])
    lines.append(
        "    ensure_tenant(db, tenant)" if sqlalchemy_enabled else "    ensure_tenant(None, tenant)"
    )
    lines.append('    return {"tenant_id": tenant.tenant_id}')
    lines.extend(
        [
            "",
            "",
            '@router.get("/roles", response_model=dict[str, list[str]])',
            "def roles() -> dict[str, list[str]]:",
            "    return {role: sorted(permissions) for role, permissions in ROLE_PERMISSIONS.items()}",
            "",
            "",
            '@router.get("/roles/{role}/permissions/{permission}", response_model=dict[str, object])',
            "def role_decision(role: str, permission: str) -> dict[str, object]:",
            "    return decide(role, permission).model_dump()",
            "",
            "",
            '@router.post("/audit/events", response_model=dict[str, Any])',
            "def record_audit_event(",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db: DbSession,")
    lines.extend(["    tenant: TenantDep,", ") -> dict[str, Any]:"])
    db_expr = "db" if sqlalchemy_enabled else "None"
    lines.extend(
        [
            f"    ensure_tenant({db_expr}, tenant)",
            "    event = audit_log.record(",
            f"        db={db_expr},",
            '        event_type="manual.platform_probe",',
            '        actor="api",',
            "        tenant_id=tenant.tenant_id,",
            "    )",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db.commit()")
    lines.append("    return event.model_dump()")
    lines.extend(
        [
            "",
            "",
            '@router.get("/audit/events", response_model=list[dict[str, Any]])',
            "def audit_events(",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db: DbSession,")
    lines.extend(
        [
            "    tenant: TenantDep,",
            "    limit: Annotated[int, Query(ge=1, le=500)] = 100,",
            ") -> list[dict[str, Any]]:",
            "    return [",
            "        event.model_dump()",
            f"        for event in audit_log.list(db={db_expr}, tenant_id=tenant.tenant_id, limit=limit)",
            "    ]",
            "",
            "",
            '@router.get("/workflows", response_model=list[dict[str, Any]])',
            "def workflows() -> list[dict[str, Any]]:",
            "    return list_workflows()",
            "",
            "",
            "@router.post(",
            '    "/workflows/{workflow_name}/{resource_id}/{action}",',
            "    response_model=dict[str, object],",
            ")",
            "def transition_workflow(",
            "    workflow_name: str,",
            "    resource_id: str,",
            "    action: str,",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db: DbSession,")
    lines.extend(
        [
            "    tenant: TenantDep,",
            "    expected_state: Annotated[str | None, Query()] = None,",
            "    context: Annotated[dict[str, Any] | None, Body()] = None,",
            ") -> dict[str, object]:",
            f"    ensure_tenant({db_expr}, tenant)",
            "    result = workflow_runtime.transition(",
            "        workflow_name,",
            "        resource_id,",
            "        action,",
            "        tenant_id=tenant.tenant_id,",
            "        expected_state=expected_state,",
            "        context=context,",
            '        actor="api",',
            f"        db={db_expr},",
            "    )",
        ]
    )
    if sqlalchemy_enabled:
        lines.append("    db.commit()")
    lines.append("    return result.model_dump()")
    return "\n".join(lines) + "\n"


def _seed_admin_py(sqlalchemy_enabled: bool) -> str:
    if not sqlalchemy_enabled:
        return dedent("""
            from __future__ import annotations

            import json
            import os

            from app.core.security import create_access_token
            from app.platform.rbac import ROLE_PERMISSIONS


            def main() -> int:
                subject = os.getenv("SEED_ADMIN_SUBJECT", "admin")
                token = create_access_token(
                    subject=subject,
                    scopes=["read", "write", "admin"],
                    roles=["Admin"],
                )
                print(
                    json.dumps(
                        {
                            "status": "ok",
                            "subject": subject,
                            "seeded_roles": sorted(ROLE_PERMISSIONS),
                            "access_token": token,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
        """).lstrip()
    return dedent("""
        from __future__ import annotations

        import json
        import os

        from app.core.security import create_access_token
        from app.db.session import SessionLocal
        from app.platform.models import TenantRecord
        from app.platform.rbac import ROLE_PERMISSIONS


        def main() -> int:
            tenant_id = os.getenv("SEED_TENANT_ID", "default")
            tenant_name = os.getenv("SEED_TENANT_NAME", "Default Tenant")
            subject = os.getenv("SEED_ADMIN_SUBJECT", "admin")
            with SessionLocal() as db:
                tenant = db.get(TenantRecord, tenant_id)
                if tenant is None:
                    db.add(TenantRecord(tenant_id=tenant_id, name=tenant_name))
                    db.commit()
            token = create_access_token(
                subject=subject,
                scopes=["read", "write", "admin"],
                roles=["Admin"],
            )
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "tenant_id": tenant_id,
                        "subject": subject,
                        "seeded_roles": sorted(ROLE_PERMISSIONS),
                        "access_token": token,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    """).lstrip()


def _admin_ui_files(graph: SIRGraph) -> list[GeneratedFile]:
    routes = _route_specs(graph)
    entities = _entity_specs(graph)
    contract_json = json.dumps({"entities": entities, "routes": routes}, indent=2, sort_keys=True)
    package_json = json.dumps(
        {
            "name": "generated-ssm-admin",
            "version": "2.0.0",
            "private": True,
            "type": "module",
            "engines": {"node": ">=20.19"},
            "scripts": {
                "dev": "vite --host 0.0.0.0",
                "typecheck": "tsc --noEmit",
                "build": "tsc --noEmit && vite build",
                "preview": "vite preview --host 0.0.0.0",
            },
            "dependencies": {"react": "19.2.7", "react-dom": "19.2.7"},
            "devDependencies": {
                "@types/react": "19.2.17",
                "@types/react-dom": "19.2.3",
                "@vitejs/plugin-react": "6.0.3",
                "typescript": "7.0.2",
                "vite": "8.1.4",
            },
        },
        indent=2,
        sort_keys=True,
    )
    files = {
        "admin/README.md": dedent("""
            # Generated SSM Admin

            This is a production-buildable React/Vite admin application generated from the app contract.

            ```bash
            npm install
            npm run typecheck
            npm run build
            npm run dev
            ```

            Configure the API URL, bearer token, and tenant identifier in the settings panel. CRUD pages are generated from the contract and use the auth-aware, tenant-aware API client.
        """).lstrip(),
        "admin/package.json": package_json + "\n",
        "admin/tsconfig.json": dedent("""
            {
              "compilerOptions": {
                "target": "ES2022",
                "useDefineForClassFields": true,
                "lib": ["ES2022", "DOM", "DOM.Iterable"],
                "allowJs": false,
                "skipLibCheck": true,
                "esModuleInterop": true,
                "allowSyntheticDefaultImports": true,
                "strict": true,
                "forceConsistentCasingInFileNames": true,
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "resolveJsonModule": true,
                "isolatedModules": true,
                "noEmit": true,
                "jsx": "react-jsx"
              },
              "include": ["src", "vite.config.ts"]
            }
        """).lstrip(),
        "admin/vite.config.ts": dedent("""
            import { defineConfig } from 'vite';
            import react from '@vitejs/plugin-react';

            export default defineConfig({
              plugins: [react()],
              build: { sourcemap: true },
            });
        """).lstrip(),
        "admin/index.html": dedent("""
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Generated SSM Admin</title>
              </head>
              <body>
                <div id="root"></div>
                <script type="module" src="/src/main.tsx"></script>
              </body>
            </html>
        """).lstrip(),
        "admin/src/generatedContract.json": contract_json + "\n",
        "admin/src/vite-env.d.ts": '/// <reference types="vite/client" />\n',
        "admin/src/types.ts": dedent("""
            export type FieldSpec = {
              name: string;
              type: string;
              required: boolean;
              primary: boolean;
              unique: boolean;
            };

            export type EntitySpec = {
              name: string;
              fields: FieldSpec[];
              tenant_scoped: boolean;
            };

            export type RouteSpec = {
              name: string;
              method: string;
              path: string;
              auth: string;
              body: string | null;
              returns: string | null;
              entity: string;
            };

            export type GeneratedContract = {
              entities: EntitySpec[];
              routes: RouteSpec[];
            };
        """).lstrip(),
        "admin/src/apiClient.ts": dedent("""
            export type ApiClientOptions = {
              baseUrl: string;
              token?: string;
              tenantId?: string;
            };

            export class ApiError extends Error {
              constructor(
                message: string,
                public readonly status: number,
                public readonly payload: unknown,
              ) {
                super(message);
              }
            }

            export async function apiRequest<T>(
              options: ApiClientOptions,
              path: string,
              init: RequestInit = {},
            ): Promise<T> {
              const headers = new Headers(init.headers);
              if (init.body !== undefined) headers.set('content-type', 'application/json');
              if (options.token) headers.set('authorization', `Bearer ${options.token}`);
              if (options.tenantId) headers.set('x-tenant-id', options.tenantId);
              const baseUrl = options.baseUrl.replace(/\\/$/, '');
              const response = await fetch(`${baseUrl}${path}`, { ...init, headers });
              const contentType = response.headers.get('content-type') ?? '';
              const payload = contentType.includes('application/json') ? await response.json() : await response.text();
              if (!response.ok) {
                throw new ApiError(`API request failed: ${response.status}`, response.status, payload);
              }
              return payload as T;
            }
        """).lstrip(),
        "admin/src/openapiClient.ts": dedent("""
            import { apiRequest, type ApiClientOptions } from './apiClient';

            export type OpenApiDocument = {
              openapi: string;
              info: { title: string; version: string };
              paths: Record<string, unknown>;
            };

            let cached: OpenApiDocument | null = null;

            export async function loadOpenApi(options: ApiClientOptions): Promise<OpenApiDocument> {
              cached ??= await apiRequest<OpenApiDocument>(options, '/openapi.json');
              return cached;
            }
        """).lstrip(),
        "admin/src/settings.ts": dedent("""
            import type { ApiClientOptions } from './apiClient';

            const STORAGE_KEY = 'ssm-admin-settings';

            export function loadSettings(): ApiClientOptions {
              const fallback: ApiClientOptions = { baseUrl: 'http://127.0.0.1:8000', tenantId: 'default' };
              const raw = localStorage.getItem(STORAGE_KEY);
              if (!raw) return fallback;
              try {
                return { ...fallback, ...(JSON.parse(raw) as ApiClientOptions) };
              } catch {
                return fallback;
              }
            }

            export function saveSettings(settings: ApiClientOptions): void {
              localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
            }
        """).lstrip(),
        "admin/src/ResourcePage.tsx": dedent("""
            import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';

            import { apiRequest, type ApiClientOptions } from './apiClient';
            import type { EntitySpec, RouteSpec } from './types';

            type Props = {
              entity: EntitySpec;
              routes: RouteSpec[];
              options: ApiClientOptions;
            };

            type Item = Record<string, unknown>;

            function routeFor(routes: RouteSpec[], method: string, withId: boolean): RouteSpec | undefined {
              return routes.find((route) => route.method === method && route.path.includes('{') === withId);
            }

            function emptyForm(entity: EntitySpec): Record<string, string> {
              return Object.fromEntries(
                entity.fields
                  .filter((field) => !field.primary && field.name !== 'tenant_id')
                  .map((field) => [field.name, '']),
              );
            }

            function coerce(value: string, type: string): unknown {
              if (type === 'int') return Number.parseInt(value || '0', 10);
              if (type === 'float') return Number.parseFloat(value || '0');
              if (type === 'bool') return value === 'true';
              return value;
            }

            export function ResourcePage({ entity, routes, options }: Props) {
              const [items, setItems] = useState<Item[]>([]);
              const [form, setForm] = useState<Record<string, string>>(() => emptyForm(entity));
              const [editingId, setEditingId] = useState<string | null>(null);
              const [error, setError] = useState('');
              const entityRoutes = useMemo(() => routes.filter((route) => route.entity === entity.name), [entity, routes]);
              const listRoute = routeFor(entityRoutes, 'GET', false);
              const createRoute = routeFor(entityRoutes, 'POST', false);
              const updateRoute = routeFor(entityRoutes, 'PATCH', true) ?? routeFor(entityRoutes, 'PUT', true);
              const deleteRoute = routeFor(entityRoutes, 'DELETE', true);

              const refresh = useCallback(async () => {
                if (!listRoute) return;
                try {
                  setItems(await apiRequest<Item[]>(options, listRoute.path));
                  setError('');
                } catch (caught) {
                  setError(caught instanceof Error ? caught.message : String(caught));
                }
              }, [listRoute, options]);

              useEffect(() => { void refresh(); }, [refresh]);

              async function submit(event: FormEvent) {
                event.preventDefault();
                const route = editingId ? updateRoute : createRoute;
                if (!route) return;
                const fields = entity.fields.filter((field) => !field.primary && field.name !== 'tenant_id');
                const payload = Object.fromEntries(fields.map((field) => [field.name, coerce(form[field.name] ?? '', field.type)]));
                const path = editingId ? route.path.replace('{id}', editingId) : route.path;
                try {
                  await apiRequest(options, path, { method: route.method, body: JSON.stringify(payload) });
                  setEditingId(null);
                  setForm(emptyForm(entity));
                  await refresh();
                } catch (caught) {
                  setError(caught instanceof Error ? caught.message : String(caught));
                }
              }

              async function remove(item: Item) {
                if (!deleteRoute || item.id === undefined) return;
                await apiRequest(options, deleteRoute.path.replace('{id}', String(item.id)), { method: 'DELETE' });
                await refresh();
              }

              function edit(item: Item) {
                setEditingId(String(item.id));
                setForm(Object.fromEntries(Object.keys(form).map((key) => [key, String(item[key] ?? '')])));
              }

              return (
                <section className="resource-page">
                  <h2>{entity.name}</h2>
                  {error && <p className="error">{error}</p>}
                  {createRoute && (
                    <form onSubmit={submit}>
                      {entity.fields.filter((field) => !field.primary && field.name !== 'tenant_id').map((field) => (
                        <label key={field.name}>
                          {field.name}
                          <input
                            required={field.required}
                            value={form[field.name] ?? ''}
                            onChange={(event) => setForm({ ...form, [field.name]: event.target.value })}
                          />
                        </label>
                      ))}
                      <button type="submit">{editingId ? 'Update' : 'Create'}</button>
                      {editingId && <button type="button" onClick={() => setEditingId(null)}>Cancel</button>}
                    </form>
                  )}
                  <table>
                    <thead><tr>{entity.fields.map((field) => <th key={field.name}>{field.name}</th>)}<th>Actions</th></tr></thead>
                    <tbody>
                      {items.map((item) => (
                        <tr key={String(item.id)}>
                          {entity.fields.map((field) => <td key={field.name}>{String(item[field.name] ?? '')}</td>)}
                          <td>
                            {updateRoute && <button onClick={() => edit(item)}>Edit</button>}
                            {deleteRoute && <button onClick={() => void remove(item)}>Delete</button>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              );
            }
        """).lstrip(),
        "admin/src/App.tsx": dedent("""
            import { useMemo, useState } from 'react';

            import contractPayload from './generatedContract.json';
            import { ResourcePage } from './ResourcePage';
            import { loadSettings, saveSettings } from './settings';
            import type { GeneratedContract } from './types';
            import './styles.css';

            const contract = contractPayload as GeneratedContract;

            export default function App() {
              const [settings, setSettings] = useState(loadSettings);
              const [selected, setSelected] = useState(contract.entities[0]?.name ?? '');
              const entity = useMemo(() => contract.entities.find((item) => item.name === selected), [selected]);

              function update(name: 'baseUrl' | 'token' | 'tenantId', value: string) {
                const next = { ...settings, [name]: value };
                setSettings(next);
                saveSettings(next);
              }

              return (
                <main>
                  <header><h1>Generated SSM Admin</h1></header>
                  <section className="settings">
                    <label>API URL<input value={settings.baseUrl} onChange={(event) => update('baseUrl', event.target.value)} /></label>
                    <label>Bearer token<input value={settings.token ?? ''} onChange={(event) => update('token', event.target.value)} /></label>
                    <label>Tenant ID<input value={settings.tenantId ?? ''} onChange={(event) => update('tenantId', event.target.value)} /></label>
                  </section>
                  <nav>
                    {contract.entities.map((item) => <button key={item.name} onClick={() => setSelected(item.name)}>{item.name}</button>)}
                  </nav>
                  {entity ? <ResourcePage entity={entity} routes={contract.routes} options={settings} /> : <p>No entities declared.</p>}
                </main>
              );
            }
        """).lstrip(),
        "admin/src/main.tsx": dedent("""
            import { StrictMode } from 'react';
            import { createRoot } from 'react-dom/client';

            import App from './App';

            const root = document.getElementById('root');
            if (!root) throw new Error('Missing root element');
            createRoot(root).render(<StrictMode><App /></StrictMode>);
        """).lstrip(),
        "admin/src/styles.css": dedent("""
            :root { font-family: Inter, system-ui, sans-serif; color: #18212f; background: #f4f6f8; }
            body { margin: 0; }
            main { max-width: 1200px; margin: auto; padding: 1.5rem; }
            header, .settings, nav, .resource-page { background: white; border-radius: 0.75rem; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 2px 10px rgb(0 0 0 / 8%); }
            .settings, form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; }
            label { display: grid; gap: 0.25rem; }
            input, button { padding: 0.55rem; }
            nav { display: flex; flex-wrap: wrap; gap: 0.5rem; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { text-align: left; border-bottom: 1px solid #d9e0e8; padding: 0.55rem; }
            .error { color: #a40000; }
        """).lstrip(),
    }
    return [GeneratedFile(path=path, content=content) for path, content in sorted(files.items())]


def _platform_migration_py(
    *,
    tenant_enabled: bool,
    audit_enabled: bool,
    workflow_enabled: bool,
) -> str:
    return dedent(f'''\
        """platform runtime persistence

        Revision ID: 0002_platform_runtime
        Revises: 0001_initial
        Create Date: 2026-07-13
        """
        from __future__ import annotations

        import sqlalchemy as sa
        from alembic import op

        revision = "0002_platform_runtime"
        down_revision = "0001_initial"
        branch_labels = None
        depends_on = None

        TENANT_ENABLED = {tenant_enabled!r}
        AUDIT_ENABLED = {audit_enabled!r}
        WORKFLOW_ENABLED = {workflow_enabled!r}


        def upgrade() -> None:
            op.create_table(
                "platform_tenants",
                sa.Column("tenant_id", sa.String(length=120), nullable=False),
                sa.Column("name", sa.String(length=200), nullable=False),
                sa.Column("active", sa.Boolean(), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("tenant_id"),
            )
            op.create_table(
                "platform_audit_events",
                sa.Column("event_id", sa.String(length=36), nullable=False),
                sa.Column("event_type", sa.String(length=160), nullable=False),
                sa.Column("actor", sa.String(length=160), nullable=False),
                sa.Column("tenant_id", sa.String(length=120), nullable=False),
                sa.Column("resource_type", sa.String(length=160), nullable=False),
                sa.Column("resource_id", sa.String(length=160), nullable=False),
                sa.Column("payload_json", sa.Text(), nullable=False),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("event_id"),
            )
            op.create_index(
                "ix_platform_audit_events_tenant_id",
                "platform_audit_events",
                ["tenant_id"],
                unique=False,
            )
            op.create_table(
                "platform_workflow_states",
                sa.Column("state_id", sa.String(length=36), nullable=False),
                sa.Column("tenant_id", sa.String(length=120), nullable=False),
                sa.Column("workflow_name", sa.String(length=160), nullable=False),
                sa.Column("resource_id", sa.String(length=160), nullable=False),
                sa.Column("state", sa.String(length=120), nullable=False),
                sa.Column("version", sa.Integer(), nullable=False),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                sa.PrimaryKeyConstraint("state_id"),
                sa.UniqueConstraint(
                    "tenant_id",
                    "workflow_name",
                    "resource_id",
                    name="uq_platform_workflow_resource",
                ),
            )


        def downgrade() -> None:
            op.drop_table("platform_workflow_states")
            op.drop_index(
                "ix_platform_audit_events_tenant_id",
                table_name="platform_audit_events",
            )
            op.drop_table("platform_audit_events")
            op.drop_table("platform_tenants")
    ''').lstrip()


def _release_evidence_md(payloads: dict[str, dict[str, Any]]) -> str:
    bundle = payloads["evidence_bundle.json"]
    records = "\n".join(f"- `{name}`" for name in bundle["records"])
    return dedent(f"""
        # Release Evidence Bundle

        This generated application is a deterministic SSM V2.0 platform artifact.

        ## Summary

        - Entities: {bundle["summary"]["entity_count"]}
        - Routes: {bundle["summary"]["route_count"]}
        - Workflows: {bundle["summary"]["workflow_count"]}
        - Business rules: {bundle["summary"]["business_rule_count"]}
        - Roles: {bundle["summary"]["role_count"]}
        - Tenant enabled: {bundle["summary"]["tenant_enabled"]}
        - Audit enabled: {bundle["summary"]["audit_enabled"]}
        - Provenance-tracked files: {bundle["summary"]["provenance_file_count"]}

        ## Records

        {records}
    """).lstrip()


def _evidence_tests_py() -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "import hashlib",
        "import json",
        "from pathlib import Path",
        "",
        f"REQUIRED_RECORDS = {pformat(EVIDENCE_RECORD_NAMES, width=88)}",
        "",
        "",
        "def _root() -> Path:",
        "    return Path(__file__).resolve().parents[1]",
        "",
        "",
        "def _load(name: str) -> dict[str, object]:",
        '    return json.loads((_root() / name).read_text(encoding="utf-8"))',
        "",
        "",
        "def test_generated_evidence_records_are_present_and_typed() -> None:",
        "    for record in REQUIRED_RECORDS:",
        "        payload = _load(record)",
        '        assert payload["schema_version"] == "2.0"',
        '        assert payload["kind"]',
        "",
        "",
        "def test_manifest_contract_and_bundle_are_consistent() -> None:",
        '    manifest = _load("generated_app_manifest.json")',
        '    contract = _load("app_contract.json")',
        '    bundle = _load("evidence_bundle.json")',
        '    assert manifest["compiler"]["target"] == "python.fastapi"',
        '    assert isinstance(manifest["generated_files"], list)',
        '    assert contract["project"]["name"]',
        '    assert "generated_app_manifest.json" in bundle["records"]',
        "",
        "",
        "def test_provenance_hashes_match_generated_files() -> None:",
        '    provenance = _load("provenance_hashes.json")',
        '    hashes = provenance["generated_file_sha256"]',
        "    assert isinstance(hashes, dict)",
        "    for relative_path, expected in hashes.items():",
        "        content = (_root() / relative_path).read_bytes()",
        "        assert hashlib.sha256(content).hexdigest() == expected",
    ]
    return "\n".join(lines) + "\n"


def _platform_tests_py(
    workflow_name: str,
    action: str,
    expected_tenant: str,
    audit_enabled: bool,
    workflow_enabled: bool,
    applicable_rule_names: list[str],
    sqlalchemy_enabled: bool,
) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "import json",
        "",
        "from app.cli.seed_admin import main as seed_admin",
        "from app.platform.audit import AuditLog",
    ]
    if sqlalchemy_enabled:
        lines.append("from app.db.session import SessionLocal")
    lines.extend(
        [
            "",
            "",
            "def test_platform_contract_endpoints_are_available(client) -> None:",
            '    manifest = client.get("/platform/manifest")',
            '    contract = client.get("/platform/contract")',
            '    capabilities = client.get("/platform/capabilities")',
            '    ready = client.get("/readyz")',
            "    assert manifest.status_code == 200",
            "    assert contract.status_code == 200",
            "    assert capabilities.status_code == 200",
            "    assert ready.status_code == 200",
            '    assert manifest.json()["kind"] == "GeneratedAppManifest"',
            '    assert contract.json()["kind"] == "AppContract"',
            '    assert ready.json()["checks"]["ready"] is True',
            "",
            "",
            "def test_seed_admin_cli_emits_token_and_seeds_platform(capsys, monkeypatch) -> None:",
            '    monkeypatch.setenv("SEED_TENANT_ID", "seed-tenant")',
            '    monkeypatch.setenv("SEED_TENANT_NAME", "Seed Tenant")',
            '    monkeypatch.setenv("SEED_ADMIN_SUBJECT", "seed-admin")',
            "    assert seed_admin() == 0",
            "    payload = json.loads(capsys.readouterr().out)",
            '    assert payload["status"] == "ok"',
            '    assert payload["subject"] == "seed-admin"',
            '    assert payload["access_token"]',
            "",
            "",
            "def test_tenant_rbac_and_database_backed_audit_primitives(client) -> None:",
            '    headers = {"x-tenant-id": "tenant-a"}',
            '    tenant = client.get("/platform/tenant/current", headers=headers)',
            "    assert tenant.status_code == 200",
            f'    assert tenant.json()["tenant_id"] == {expected_tenant!r}',
            "",
            '    roles = client.get("/platform/roles")',
            "    assert roles.status_code == 200",
            "    assert isinstance(roles.json(), dict)",
            "",
            '    decision = client.get("/platform/roles/Admin/permissions/read")',
            "    assert decision.status_code == 200",
            '    assert "allowed" in decision.json()',
            "",
            '    created = client.post("/platform/audit/events", headers=headers)',
            '    listed = client.get("/platform/audit/events", headers=headers)',
            "    other = client.get(",
            '        "/platform/audit/events",',
            '        headers={"x-tenant-id": "tenant-b"},',
            "    )",
            "    assert created.status_code == 200",
            "    assert listed.status_code == 200",
            "    assert other.status_code == 200",
        ]
    )
    if audit_enabled:
        lines.extend(
            [
                '    assert any(event["event_id"] == created.json()["event_id"] for event in listed.json())',
                "    assert other.json() == []",
            ]
        )
        if sqlalchemy_enabled:
            lines.extend(
                [
                    "    with SessionLocal() as db:",
                    "        persisted = AuditLog().list(db=db, tenant_id=headers['x-tenant-id'])",
                    '    assert any(event.event_id == created.json()["event_id"] for event in persisted)',
                ]
            )
    else:
        lines.append("    assert listed.json() == []")
    lines.extend(
        [
            "",
            "",
            "def test_workflow_runtime_enforces_transitions_rules_and_persists_state(client) -> None:",
        ]
    )
    if not workflow_enabled:
        lines.extend(
            [
                '    assert client.get("/platform/workflows").json() == []',
                "    return",
            ]
        )
    else:
        lines.extend(
            [
                '    headers = {"x-tenant-id": "tenant-a"}',
                "    context = {",
                '        "requested_days": 1,',
                '        "amount": 1,',
                '        "quantity": 1,',
                '        "employee": {"leave_balance": 20},',
                "    }",
                "    response = client.post(",
                f'        "/platform/workflows/{workflow_name}/resource-1/{action}",',
                "        headers=headers,",
                "        json=context,",
                "    )",
                "    assert response.status_code == 200",
                "    payload = response.json()",
                f'    assert payload["workflow"] == {workflow_name!r}',
            ]
        )
        if applicable_rule_names:
            lines.extend(
                [
                    (
                        '    assert sorted(item["name"] for item in payload["rules"]) '
                        f"== {applicable_rule_names!r}"
                    ),
                    '    expected_allowed = all(item["passed"] for item in payload["rules"])',
                    '    assert payload["allowed"] is expected_allowed',
                    '    assert payload["reason"] == (',
                    '        "accepted" if expected_allowed else "business_rule_rejected"',
                    "    )",
                    "    if expected_allowed:",
                    '        assert payload["version"] == 1',
                    "        repeated = client.post(",
                    f'            "/platform/workflows/{workflow_name}/resource-1/{action}",',
                    "            headers=headers,",
                    "            json=context,",
                    "        )",
                    "        assert repeated.status_code == 200",
                    '        assert repeated.json()["allowed"] is False',
                    '        assert repeated.json()["reason"] == "transition_not_allowed"',
                    "    else:",
                    '        assert payload["version"] == 0',
                ]
            )
        else:
            lines.extend(
                [
                    '    assert payload["rules"] == []',
                    '    assert payload["allowed"] is True',
                    '    assert payload["reason"] == "accepted"',
                    '    assert payload["version"] == 1',
                    "    repeated = client.post(",
                    f'        "/platform/workflows/{workflow_name}/resource-1/{action}",',
                    "        headers=headers,",
                    "        json=context,",
                    "    )",
                    "    assert repeated.status_code == 200",
                    '    assert repeated.json()["allowed"] is False',
                    '    assert repeated.json()["reason"] == "transition_not_allowed"',
                ]
            )
    return "\n".join(lines) + "\n"


def _admin_static_tests_py() -> str:
    return dedent("""
        from __future__ import annotations

        import json
        from pathlib import Path


        def test_generated_admin_application_is_complete() -> None:
            root = Path(__file__).resolve().parents[1]
            required = [
                "admin/package.json",
                "admin/tsconfig.json",
                "admin/vite.config.ts",
                "admin/index.html",
                "admin/src/main.tsx",
                "admin/src/vite-env.d.ts",
                "admin/src/App.tsx",
                "admin/src/ResourcePage.tsx",
                "admin/src/apiClient.ts",
                "admin/src/openapiClient.ts",
                "admin/src/generatedContract.json",
            ]
            for relative_path in required:
                assert (root / relative_path).exists(), relative_path
            package = json.loads((root / "admin/package.json").read_text(encoding="utf-8"))
            assert package["scripts"]["typecheck"]
            assert package["scripts"]["build"]
            app = (root / "admin/src/App.tsx").read_text(encoding="utf-8")
            client = (root / "admin/src/apiClient.ts").read_text(encoding="utf-8")
            resource_page = (root / "admin/src/ResourcePage.tsx").read_text(encoding="utf-8")
            assert "ResourcePage" in app
            assert "x-tenant-id" in client
            assert "authorization" in client
            assert "DELETE" in resource_page
    """).lstrip()


def textwrap_indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else "" for line in text.splitlines())
