from __future__ import annotations

import json
import re
from pprint import pformat
from textwrap import dedent
from typing import Any

from ssm.models import CompileManifest, GeneratedFile, ResolutionResult, SIRGraph
from ssm.semantic.field_parser import normalize_schema_name


def platform_source_files(graph: SIRGraph) -> list[GeneratedFile]:
    workflows = _workflow_specs(graph)
    roles = _role_specs(graph)
    tenant_enabled = _section_enabled(graph, "Tenant")
    audit_enabled = _section_enabled(graph, "Audit")
    files = [
        GeneratedFile(path="app/platform/__init__.py", content=""),
        GeneratedFile(path="app/platform/tenancy.py", content=_tenancy_py(tenant_enabled)),
        GeneratedFile(path="app/platform/rbac.py", content=_rbac_py(roles)),
        GeneratedFile(path="app/platform/audit.py", content=_audit_py(audit_enabled)),
        GeneratedFile(path="app/platform/workflow.py", content=_workflow_py(workflows)),
        GeneratedFile(path="app/api/routes/platform.py", content=_platform_routes_py(workflows)),
        GeneratedFile(path="app/cli/__init__.py", content=""),
        GeneratedFile(path="app/cli/seed_admin.py", content=_seed_admin_py()),
    ]
    files.extend(_admin_ui_files(graph))
    return files


def evidence_record_files(
    graph: SIRGraph,
    resolution: ResolutionResult,
    manifest: CompileManifest,
    generated_files: list[str],
) -> list[GeneratedFile]:
    del resolution
    capabilities = _capability_specs(graph)
    assumptions = _assumption_specs(graph)
    unsupported = _unsupported_features(graph)
    roles = _role_specs(graph)
    workflows = _workflow_specs(graph)
    tenant_enabled = _section_enabled(graph, "Tenant")
    audit_enabled = _section_enabled(graph, "Audit")
    route_specs = _route_specs(graph)
    entity_specs = _entity_specs(graph)

    generated_app_manifest = {
        "schema_version": "1.0",
        "kind": "GeneratedAppManifest",
        "platform_release": "1.5.0-dev",
        "compiler": {
            "version": manifest.compiler_version,
            "target": manifest.target,
        },
        "hashes": {
            "sml_sha256": manifest.sml_hash,
            "sir_sha256": manifest.sir_hash,
            "resolved_ir_sha256": manifest.resolved_ir_hash,
        },
        "generated_files": generated_files,
        "selected_candidates": manifest.selected_candidates,
        "proof_count": manifest.proof_count,
    }
    app_contract = {
        "schema_version": "1.0",
        "kind": "AppContract",
        "project": _project_spec(graph),
        "stack": _stack_spec(graph),
        "entities": entity_specs,
        "routes": route_specs,
        "tenant_enabled": tenant_enabled,
        "audit_enabled": audit_enabled,
        "roles": roles,
        "workflows": workflows,
        "acceptance_gates": [
            "pytest",
            "coverage",
            "ruff",
            "ruff_format",
            "mypy",
            "compileall",
            "bandit",
            "pip_audit",
            "alembic_cycle",
            "secret_scan",
        ],
    }
    capability_report = {
        "schema_version": "1.0",
        "kind": "CapabilityReport",
        "requested_capabilities": capabilities,
        "supported_features": [
            "crud",
            "basic_relationship_metadata",
            "tenant_context_propagation",
            "rbac_role_permission_model",
            "audit_event_capture",
            "workflow_transition_runtime",
            "generated_admin_ui_shell",
            "evidence_records",
        ],
        "partially_supported_features": [
            "tenant_scoped_repository_contracts",
            "workflow_business_rule_enforcement",
            "live_provider_repair_loop",
        ],
        "unsupported_features": unsupported,
    }
    eval_run = {
        "schema_version": "1.0",
        "kind": "EvalRunRecord",
        "status": "ACCEPTANCE_GATES_REQUIRED",
        "deterministic_compile": True,
        "expected_gates": app_contract["acceptance_gates"],
        "notes": [
            "This record is emitted at compile time. Runtime E2E scripts append external gate evidence.",
            "Generated source is deterministic; online model output is limited to SML drafts.",
        ],
    }
    assumptions_doc = {
        "schema_version": "1.0",
        "kind": "Assumptions",
        "items": assumptions,
    }
    unsupported_doc = {
        "schema_version": "1.0",
        "kind": "UnsupportedFeatures",
        "items": unsupported,
    }
    provenance_hashes = {
        "schema_version": "1.0",
        "kind": "ProvenanceHashes",
        "hashes": generated_app_manifest["hashes"],
        "selected_candidates": manifest.selected_candidates,
    }
    evidence_bundle = {
        "schema_version": "1.0",
        "kind": "ReleaseEvidenceBundle",
        "records": [
            "generated_app_manifest.json",
            "app_contract.json",
            "eval_run.json",
            "capability_report.json",
            "assumptions.json",
            "unsupported_features.json",
            "provenance_hashes.json",
        ],
        "summary": {
            "entity_count": len(entity_specs),
            "route_count": len(route_specs),
            "workflow_count": len(workflows),
            "role_count": len(roles),
            "tenant_enabled": tenant_enabled,
            "audit_enabled": audit_enabled,
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


def platform_test_files(graph: SIRGraph) -> dict[str, str]:
    workflows = _workflow_specs(graph)
    workflow_name = workflows[0]["name"] if workflows else "DefaultWorkflow"
    action = workflows[0]["actions"][0] if workflows and workflows[0].get("actions") else "advance"
    expected_tenant = "tenant-a" if _section_enabled(graph, "Tenant") else "default"
    audit_enabled = _section_enabled(graph, "Audit")
    return {
        "tests/test_evidence_records.py": _evidence_tests_py(),
        "tests/test_platform_primitives.py": _platform_tests_py(
            workflow_name, action, expected_tenant, audit_enabled
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


def _entity_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for node in graph.by_type("DataModel"):
        if node.name.endswith("Create"):
            continue
        fields = []
        for field in node.attributes.get("fields", []):
            fields.append(
                {
                    "name": field.get("name"),
                    "type": field.get("raw_type") or field.get("python_type"),
                    "required": bool(field.get("required")),
                    "primary": bool(field.get("primary")),
                    "unique": bool(field.get("unique")),
                }
            )
        entities.append({"name": node.name, "fields": fields})
    return sorted(entities, key=lambda item: item["name"])


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
            }
        )
    return sorted(routes, key=lambda item: (item["path"], item["method"], item["name"]))


def _capability_specs(graph: SIRGraph) -> list[str]:
    values = [node.name for node in graph.by_type("Capability")]
    return sorted(dict.fromkeys(values))


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
        permissions = node.attributes.get("permissions", [])
        if isinstance(permissions, str):
            permissions = [part.strip() for part in permissions.split(",") if part.strip()]
        roles.append({"name": node.name, "permissions": list(permissions or [])})
    if not roles:
        roles = [
            {"name": "Admin", "permissions": ["read", "write", "admin"]},
            {"name": "Viewer", "permissions": ["read"]},
        ]
    return sorted(roles, key=lambda item: item["name"])


def _workflow_specs(graph: SIRGraph) -> list[dict[str, Any]]:
    workflows: list[dict[str, Any]] = []
    for node in graph.by_type("Workflow"):
        states = _string_list(node.attributes.get("states")) or ["draft", "done"]
        transitions = _string_list(node.attributes.get("transitions"))
        actions = _string_list(node.attributes.get("actions"))
        if not actions and transitions:
            actions = [_action_name(transition) for transition in transitions]
        workflows.append(
            {
                "name": node.name,
                "entity": str(node.attributes.get("entity", "Resource")),
                "states": states,
                "transitions": transitions,
                "actions": actions or ["advance"],
            }
        )
    return sorted(workflows, key=lambda item: item["name"])


def _section_enabled(graph: SIRGraph, section_type: str) -> bool:
    nodes = graph.by_type(section_type)
    if not nodes:
        return False
    value = nodes[0].attributes.get("enabled", True)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"false", "0", "no", "off"}


def _none_to_none(value: Any) -> Any:
    if value is None:
        return None
    if str(value).lower() in {"none", "null"}:
        return None
    return normalize_schema_name(str(value))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(value)]


def _action_name(transition: str) -> str:
    cleaned = transition.replace("->", "_")
    return re.sub(r"[^A-Za-z0-9]+", "_", cleaned).strip("_").lower() or "advance"


def _tenancy_py(enabled: bool) -> str:
    return dedent(f"""
        from __future__ import annotations

        from dataclasses import dataclass
        from typing import Annotated

        from fastapi import Header

        TENANCY_ENABLED = {enabled!r}


        @dataclass(frozen=True, slots=True)
        class TenantContext:
            tenant_id: str = "default"


        def normalize_tenant_id(value: str | None) -> str:
            cleaned = (value or "default").strip()
            return cleaned or "default"


        def tenant_key(tenant_id: str, item_id: str) -> str:
            return f"{{normalize_tenant_id(tenant_id)}}:{{item_id}}"


        def get_tenant_context(
            x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
        ) -> TenantContext:
            if not TENANCY_ENABLED:
                return TenantContext()
            return TenantContext(tenant_id=normalize_tenant_id(x_tenant_id))
    """).lstrip()


def _rbac_py(roles: list[dict[str, Any]]) -> str:
    role_map = {role["name"]: sorted(role.get("permissions", [])) for role in roles}
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import asdict, dataclass",
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
            "def decide(role: str, permission: str) -> RoleDecision:",
            "    return RoleDecision(role=role, permission=permission, allowed=has_permission(role, permission))",
        ]
    )
    return "\n".join(lines) + "\n"


def _audit_py(enabled: bool) -> str:
    return dedent(f"""
        from __future__ import annotations

        from dataclasses import asdict, dataclass
        from datetime import UTC, datetime
        from threading import RLock
        from uuid import uuid4

        AUDIT_ENABLED = {enabled!r}


        @dataclass(frozen=True, slots=True)
        class AuditEvent:
            event_id: str
            event_type: str
            actor: str
            tenant_id: str
            resource_type: str
            resource_id: str
            created_at: str

            def model_dump(self) -> dict[str, str]:
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
            ) -> AuditEvent:
                event = AuditEvent(
                    event_id=str(uuid4()),
                    event_type=event_type,
                    actor=actor,
                    tenant_id=tenant_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    created_at=datetime.now(UTC).isoformat(),
                )
                if AUDIT_ENABLED:
                    with self._lock:
                        self._events.append(event)
                return event

            def list(self) -> list[AuditEvent]:
                with self._lock:
                    return list(self._events)

            def clear(self) -> None:
                with self._lock:
                    self._events.clear()


        audit_log = AuditLog()
    """).lstrip()


def _workflow_py(workflows: list[dict[str, Any]]) -> str:
    payload = pformat(workflows, width=88)
    lines = [
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "from typing import Any",
        "",
        "WORKFLOWS: list[dict[str, Any]] = (",
    ]
    lines.extend(f"    {line}" for line in payload.splitlines())
    lines.extend(
        [
            ")",
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
            "",
            "    def model_dump(self) -> dict[str, object]:",
            "        return {",
            "            'workflow': self.workflow,",
            "            'resource_id': self.resource_id,",
            "            'action': self.action,",
            "            'from_state': self.from_state,",
            "            'to_state': self.to_state,",
            "            'allowed': self.allowed,",
            "        }",
            "",
            "",
            "def list_workflows() -> list[dict[str, Any]]:",
            "    return WORKFLOWS",
            "",
            "",
            "def transition(",
            "    workflow_name: str,",
            "    resource_id: str,",
            "    action: str,",
            "    current_state: str | None = None,",
            ") -> TransitionResult:",
            "    workflow = next((item for item in WORKFLOWS if item['name'] == workflow_name), None)",
            "    if workflow is None:",
            "        return TransitionResult(",
            "            workflow=workflow_name,",
            "            resource_id=resource_id,",
            "            action=action,",
            "            from_state=current_state or 'unknown',",
            "            to_state=current_state or 'unknown',",
            "            allowed=False,",
            "        )",
            "    states = list(workflow.get('states') or ['draft', 'done'])",
            "    actions = list(workflow.get('actions') or ['advance'])",
            "    from_state = current_state or states[0]",
            "    if action not in actions:",
            "        return TransitionResult(",
            "            workflow=workflow_name,",
            "            resource_id=resource_id,",
            "            action=action,",
            "            from_state=from_state,",
            "            to_state=from_state,",
            "            allowed=False,",
            "        )",
            "    try:",
            "        index = states.index(from_state)",
            "    except ValueError:",
            "        index = 0",
            "        from_state = states[0]",
            "    to_state = states[min(index + 1, len(states) - 1)]",
            "    return TransitionResult(",
            "        workflow=workflow_name,",
            "        resource_id=resource_id,",
            "        action=action,",
            "        from_state=from_state,",
            "        to_state=to_state,",
            "        allowed=True,",
            "    )",
        ]
    )
    return "\n".join(lines) + "\n"


def _platform_routes_py(workflows: list[dict[str, Any]]) -> str:
    del workflows
    return dedent("""
        from __future__ import annotations

        import json
        from pathlib import Path
        from typing import Annotated, Any

        from fastapi import APIRouter, Depends, Query

        from app.platform.audit import audit_log
        from app.platform.rbac import ROLE_PERMISSIONS, decide
        from app.platform.tenancy import TenantContext, get_tenant_context
        from app.platform.workflow import list_workflows, transition

        router = APIRouter(prefix="/platform", tags=["platform"])
        TenantDep = Annotated[TenantContext, Depends(get_tenant_context)]
        _ROOT = Path(__file__).resolve().parents[3]


        def _json_record(name: str) -> dict[str, Any]:
            path = _ROOT / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Evidence record {name} must be a JSON object")
            return dict(payload)


        @router.get("/manifest", response_model=dict[str, Any])
        def generated_manifest() -> dict[str, Any]:
            return _json_record("generated_app_manifest.json")


        @router.get("/contract", response_model=dict[str, Any])
        def app_contract() -> dict[str, Any]:
            return _json_record("app_contract.json")


        @router.get("/capabilities", response_model=dict[str, Any])
        def capability_report() -> dict[str, Any]:
            return _json_record("capability_report.json")


        @router.get("/tenant/current", response_model=dict[str, str])
        def current_tenant(tenant: TenantDep) -> dict[str, str]:
            return {"tenant_id": tenant.tenant_id}


        @router.get("/roles", response_model=dict[str, list[str]])
        def roles() -> dict[str, list[str]]:
            return {role: sorted(permissions) for role, permissions in ROLE_PERMISSIONS.items()}


        @router.get("/roles/{role}/permissions/{permission}", response_model=dict[str, object])
        def role_decision(role: str, permission: str) -> dict[str, object]:
            return decide(role, permission).model_dump()


        @router.post("/audit/events", response_model=dict[str, str])
        def record_audit_event(tenant: TenantDep) -> dict[str, str]:
            event = audit_log.record(
                event_type="manual.platform_probe",
                actor="api",
                tenant_id=tenant.tenant_id,
            )
            return event.model_dump()


        @router.get("/audit/events", response_model=list[dict[str, str]])
        def audit_events() -> list[dict[str, str]]:
            return [event.model_dump() for event in audit_log.list()]


        @router.get("/workflows", response_model=list[dict[str, Any]])
        def workflows() -> list[dict[str, Any]]:
            return list_workflows()


        @router.post("/workflows/{workflow_name}/{resource_id}/{action}", response_model=dict[str, object])
        def transition_workflow(
            workflow_name: str,
            resource_id: str,
            action: str,
            current_state: Annotated[str | None, Query()] = None,
        ) -> dict[str, object]:
            return transition(workflow_name, resource_id, action, current_state).model_dump()
    """).lstrip()


def _seed_admin_py() -> str:
    return dedent("""
        from __future__ import annotations

        import json

        from app.platform.rbac import ROLE_PERMISSIONS


        def main() -> int:
            payload = {
                "status": "ok",
                "seeded_roles": sorted(ROLE_PERMISSIONS),
                "admin_hint": "Create an operator token with the admin scope in your identity provider.",
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
    """).lstrip()


def _admin_ui_files(graph: SIRGraph) -> list[GeneratedFile]:
    routes = _route_specs(graph)
    entities = _entity_specs(graph)
    entity_cards = (
        "\n".join(
            f"        <li><strong>{entity['name']}</strong> — {len(entity['fields'])} fields</li>"
            for entity in entities
        )
        or "        <li>No domain entities declared.</li>"
    )
    route_cards = (
        "\n".join(f"        <li>{route['method']} {route['path']}</li>" for route in routes)
        or "        <li>No routes declared.</li>"
    )
    package_json = json.dumps(
        {
            "name": "generated-ssm-admin",
            "version": "0.1.0",
            "private": True,
            "scripts": {"typecheck": "tsc --noEmit", "build": "vite build"},
            "dependencies": {
                "@vitejs/plugin-react": "latest",
                "react": "latest",
                "react-dom": "latest",
                "typescript": "latest",
                "vite": "latest",
            },
            "devDependencies": {},
        },
        indent=2,
        sort_keys=True,
    )
    files = {
        "admin/README.md": "# Generated Admin UI Shell\n\nThis static shell is generated from the SML app contract. Wire it to any frontend build stack while retaining the OpenAPI client and auth-aware request wrapper.\n",
        "admin/package.json": package_json + "\n",
        "admin/index.html": f"""<!doctype html>
<html lang="en">
  <head><meta charset="UTF-8"><title>Generated Admin</title></head>
  <body>
    <main>
      <h1>Generated Admin Shell</h1>
      <h2>Entities</h2>
      <ul>
{entity_cards}
      </ul>
      <h2>Routes</h2>
      <ul>
{route_cards}
      </ul>
    </main>
    <script type="module" src="/src/App.tsx"></script>
  </body>
</html>
""",
        "admin/src/apiClient.ts": """export type ApiClientOptions = {
  baseUrl: string;
  token?: string;
  tenantId?: string;
};

export async function apiRequest<T>(options: ApiClientOptions, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('content-type', 'application/json');
  if (options.token) headers.set('authorization', `Bearer ${options.token}`);
  if (options.tenantId) headers.set('x-tenant-id', options.tenantId);
  const response = await fetch(`${options.baseUrl}${path}`, { ...init, headers });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json() as Promise<T>;
}
""",
        "admin/src/App.tsx": """import React from 'react';

export function App() {
  return (
    <section>
      <h1>Generated SSM Admin</h1>
      <p>This shell is generated from the app contract. Connect authentication and route-specific pages during product hardening.</p>
    </section>
  );
}
""",
    }
    return [GeneratedFile(path=path, content=content) for path, content in sorted(files.items())]


def _release_evidence_md(payloads: dict[str, dict[str, Any]]) -> str:
    bundle = payloads["evidence_bundle.json"]
    records = "\n".join(f"- `{name}`" for name in bundle["records"])
    return dedent(f"""
        # Release Evidence Bundle

        This generated backend includes Auto-inspired evidence records without adopting a cognition-runtime architecture.

        ## Summary

        - Entities: {bundle["summary"]["entity_count"]}
        - Routes: {bundle["summary"]["route_count"]}
        - Workflows: {bundle["summary"]["workflow_count"]}
        - Roles: {bundle["summary"]["role_count"]}
        - Tenant enabled: {bundle["summary"]["tenant_enabled"]}
        - Audit enabled: {bundle["summary"]["audit_enabled"]}

        ## Records

        {records}
    """).lstrip()


def _evidence_tests_py() -> str:
    return dedent("""
        from __future__ import annotations

        import json
        from pathlib import Path

        REQUIRED_RECORDS = [
            "generated_app_manifest.json",
            "app_contract.json",
            "eval_run.json",
            "capability_report.json",
            "assumptions.json",
            "unsupported_features.json",
            "provenance_hashes.json",
            "evidence_bundle.json",
        ]


        def _root() -> Path:
            return Path(__file__).resolve().parents[1]


        def _load(name: str) -> dict[str, object]:
            return json.loads((_root() / name).read_text(encoding="utf-8"))


        def test_generated_evidence_records_are_present_and_typed() -> None:
            for record in REQUIRED_RECORDS:
                payload = _load(record)
                assert payload["schema_version"] == "1.0"
                assert payload["kind"]


        def test_manifest_contract_and_bundle_are_consistent() -> None:
            manifest = _load("generated_app_manifest.json")
            contract = _load("app_contract.json")
            bundle = _load("evidence_bundle.json")
            assert manifest["compiler"]["target"] == "python.fastapi"
            assert isinstance(manifest["generated_files"], list)
            assert contract["project"]["name"]
            assert "generated_app_manifest.json" in bundle["records"]
    """).lstrip()


def _platform_tests_py(
    workflow_name: str, action: str, expected_tenant: str, audit_enabled: bool
) -> str:
    return dedent(f"""
        from __future__ import annotations


        def test_platform_contract_endpoints_are_available(client) -> None:
            manifest = client.get("/platform/manifest")
            contract = client.get("/platform/contract")
            capabilities = client.get("/platform/capabilities")
            assert manifest.status_code == 200
            assert contract.status_code == 200
            assert capabilities.status_code == 200
            assert manifest.json()["kind"] == "GeneratedAppManifest"
            assert contract.json()["kind"] == "AppContract"


        def test_tenant_rbac_and_audit_platform_primitives(client) -> None:
            tenant = client.get("/platform/tenant/current", headers={{"x-tenant-id": "tenant-a"}})
            assert tenant.status_code == 200
            assert tenant.json()["tenant_id"] == {expected_tenant!r}

            roles = client.get("/platform/roles")
            assert roles.status_code == 200
            assert isinstance(roles.json(), dict)

            decision = client.get("/platform/roles/Admin/permissions/read")
            assert decision.status_code == 200
            assert "allowed" in decision.json()

            created = client.post("/platform/audit/events", headers={{"x-tenant-id": "tenant-a"}})
            listed = client.get("/platform/audit/events")
            assert created.status_code == 200
            assert listed.status_code == 200
            if {audit_enabled!r}:
                assert any(event["event_id"] == created.json()["event_id"] for event in listed.json())
            else:
                assert listed.json() == []


        def test_workflow_runtime_endpoint(client) -> None:
            workflows = client.get("/platform/workflows")
            assert workflows.status_code == 200
            transition = client.post("/platform/workflows/{workflow_name}/resource-1/{action}")
            assert transition.status_code == 200
            assert transition.json()["workflow"] == {workflow_name!r}
            assert "allowed" in transition.json()
    """).lstrip()


def _admin_static_tests_py() -> str:
    return dedent("""
        from __future__ import annotations

        from pathlib import Path


        def test_generated_admin_shell_files_exist() -> None:
            root = Path(__file__).resolve().parents[1]
            assert (root / "admin" / "index.html").exists()
            assert (root / "admin" / "src" / "apiClient.ts").exists()
            assert (root / "admin" / "src" / "App.tsx").exists()
            client = (root / "admin" / "src" / "apiClient.ts").read_text(encoding="utf-8")
            assert "apiRequest" in client
            assert "x-tenant-id" in client
    """).lstrip()
