from __future__ import annotations

import re

from ssm.errors import CompilerDiagnostic, SemanticError
from ssm.models import EvidenceRef, Fact, SIRGraph, SIRNode, SMLDocument, SMLSection
from ssm.semantic.field_parser import is_primitive_type, normalize_schema_name, parse_fields

_ALLOWED_SECTIONS = {
    "project",
    "stack",
    "module",
    "datamodel",
    "route",
    "service",
    "repository",
    "component",
    "state",
    "event",
    "policy",
    "constraint",
    "rule",
    "invariant",
    "test",
    "deploy",
    "assumption",
    "decision",
    "import",
    "capability",
    "profile",
    "actor",
    "role",
    "permission",
    "relationship",
    "workflow",
    "statemachine",
    "businessrule",
    "tenant",
    "audit",
    "notification",
    "report",
    "integration",
}


class SemanticAnalyzer:
    """Converts SML AST into the compiler's Semantic Intermediate Representation."""

    def analyze(self, document: SMLDocument) -> SIRGraph:
        diagnostics: list[CompilerDiagnostic] = []
        nodes: list[SIRNode] = []
        facts: set[Fact] = set()
        models: set[str] = set()

        for section in document.sections:
            stype = section.section_type.lower()
            if stype not in _ALLOWED_SECTIONS:
                diagnostics.append(
                    self._diag("SEM001", f"Unknown section type #{section.section_type}.", section)
                )

        # First pass: nodes and model symbol table.
        for section in document.sections:
            node = self._node_from_section(section)
            nodes.append(node)
            if node.node_type == "DataModel":
                models.add(node.name)

        # Second pass: normalize data models.
        for node in nodes:
            if node.node_type == "DataModel":
                try:
                    fields = parse_fields(node.attributes.get("fields", {}))
                    node.attributes["fields"] = [f.__dict__ for f in fields]
                except Exception as exc:
                    diagnostics.append(
                        CompilerDiagnostic(
                            code="SEM002",
                            message=f"Invalid fields block for DataModel {node.name}: {exc}",
                            file=node.source_range.file if node.source_range else None,
                            start_line=node.source_range.start_line if node.source_range else None,
                            end_line=node.source_range.end_line if node.source_range else None,
                            node_id=node.id,
                        )
                    )

        # Facts from project/stack/models/routes/policies.
        for node in nodes:
            facts.update(self._facts_for_node(node))

        # Route reference validation.
        for node in nodes:
            if node.node_type != "Route":
                continue
            body = node.attributes.get("body")
            returns = node.attributes.get("returns")
            if body:
                b = normalize_schema_name(str(body))
                if not is_primitive_type(b) and b not in models:
                    diagnostics.append(
                        CompilerDiagnostic(
                            code="SEM104",
                            message=f"Route {node.name} references body schema {b}, but no #DataModel {b} exists.",
                            severity="error",
                            file=node.source_range.file if node.source_range else None,
                            start_line=node.source_range.start_line if node.source_range else None,
                            end_line=node.source_range.end_line if node.source_range else None,
                            node_id=node.id,
                            suggested_fix=f"Define #DataModel {b} or change the route body type.",
                        )
                    )
            if returns:
                r = normalize_schema_name(str(returns))
                if not is_primitive_type(r) and r not in models:
                    diagnostics.append(
                        CompilerDiagnostic(
                            code="SEM105",
                            message=f"Route {node.name} returns schema {r}, but no #DataModel {r} exists.",
                            severity="error",
                            file=node.source_range.file if node.source_range else None,
                            start_line=node.source_range.start_line if node.source_range else None,
                            end_line=node.source_range.end_line if node.source_range else None,
                            node_id=node.id,
                            suggested_fix=f"Define #DataModel {r} or change the route return type.",
                        )
                    )

        # Domain-neutral relationship validation. Relationship sections are semantic
        # foundation metadata; target packs may choose how deeply to materialize them.
        for node in nodes:
            if node.node_type != "Relationship":
                continue
            source = str(node.attributes.get("source", "")).strip()
            target = str(node.attributes.get("target", "")).strip()
            for label, value in [("source", source), ("target", target)]:
                if value and value not in models:
                    diagnostics.append(
                        CompilerDiagnostic(
                            code="SEM201",
                            message=(
                                f"Relationship {node.name} references {label} model {value}, "
                                "but no matching #DataModel exists."
                            ),
                            severity="error",
                            file=node.source_range.file if node.source_range else None,
                            start_line=node.source_range.start_line if node.source_range else None,
                            end_line=node.source_range.end_line if node.source_range else None,
                            node_id=node.id,
                            suggested_fix=f"Define #DataModel {value} or change the relationship {label}.",
                        )
                    )

        if diagnostics:
            raise SemanticError(diagnostics)
        return SIRGraph(nodes=nodes, facts=sorted(facts, key=lambda f: str(f)))

    def _node_from_section(self, section: SMLSection) -> SIRNode:
        stype = self._canonical_type(section.section_type)
        name = section.name or self._default_name(stype, section)
        node_id = f"{stype.lower()}.{self._safe_id(name)}"
        return SIRNode(
            id=node_id,
            node_type=stype,
            name=name,
            attributes=dict(section.fields),
            source_range=section.source_range,
            provenance=[
                EvidenceRef(
                    source_type="sml",
                    source_id=f"{section.source_range.file}:{section.source_range.start_line}",
                    summary=f"#{section.section_type} {section.name or ''}".strip(),
                )
            ],
        )

    def _canonical_type(self, section_type: str) -> str:
        lookup = {
            "datamodel": "DataModel",
            "project": "Project",
            "stack": "Stack",
            "module": "Module",
            "route": "Route",
            "policy": "Policy",
            "constraint": "Constraint",
            "rule": "Rule",
            "invariant": "Invariant",
            "test": "Test",
            "assumption": "Assumption",
            "decision": "Decision",
            "service": "Service",
            "repository": "Repository",
            "component": "Component",
            "state": "State",
            "event": "Event",
            "deploy": "Deploy",
            "import": "Import",
            "capability": "Capability",
            "profile": "Profile",
            "actor": "Actor",
            "role": "Role",
            "permission": "Permission",
            "relationship": "Relationship",
            "workflow": "Workflow",
            "statemachine": "StateMachine",
            "businessrule": "BusinessRule",
            "tenant": "Tenant",
            "audit": "Audit",
            "notification": "Notification",
            "report": "Report",
            "integration": "Integration",
        }
        return lookup.get(section_type.lower(), section_type)

    def _default_name(self, stype: str, section: SMLSection) -> str:
        if stype == "Project":
            return str(section.fields.get("name") or "Project")
        if stype == "Stack":
            return "Stack"
        return stype

    def _safe_id(self, name: str) -> str:
        s = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip())
        return s.strip("_") or "unnamed"

    def _facts_for_node(self, node: SIRNode) -> set[Fact]:
        facts: set[Fact] = set()
        if node.node_type == "Project":
            facts.add(Fact(predicate="Project", args=(node.name,)))
        elif node.node_type == "Stack":
            backend = str(node.attributes.get("backend", "")).strip().lower()
            if backend == "fastapi":
                facts.add(Fact(predicate="Target", args=("PythonFastAPI",)))
            elif backend:
                facts.add(Fact(predicate="Target", args=(backend,)))
            database = str(node.attributes.get("database", "")).strip()
            if database:
                facts.add(Fact(predicate="Database", args=(self._symbol(database),)))
            auth = str(node.attributes.get("auth", "")).strip()
            if auth:
                facts.add(Fact(predicate="AuthStrategy", args=(self._symbol(auth),)))
        elif node.node_type == "DataModel":
            facts.add(Fact(predicate="Model", args=(node.name,)))
            facts.add(Fact(predicate="Artifact", args=(f"Schema:{node.name}",)))
            for field in node.attributes.get("fields", []):
                fname = field["name"]
                facts.add(Fact(predicate="Field", args=(node.name, fname)))
                if field.get("unique"):
                    facts.add(Fact(predicate="Unique", args=(node.name, fname)))
                if field.get("primary"):
                    facts.add(Fact(predicate="PrimaryKey", args=(node.name, fname)))
        elif node.node_type == "Route":
            facts.add(Fact(predicate="Route", args=(node.name,)))
            method = str(node.attributes.get("method", "GET")).upper()
            facts.add(Fact(predicate="Method", args=(node.name, method)))
            if path := node.attributes.get("path"):
                facts.add(Fact(predicate="Path", args=(node.name, str(path))))
            auth = str(node.attributes.get("auth", "")).lower()
            if auth in {"required", "admin", "user", "authenticated", "true"}:
                facts.add(Fact(predicate="AuthRequired", args=(node.name,)))
            if body := node.attributes.get("body"):
                facts.add(
                    Fact(predicate="Body", args=(node.name, normalize_schema_name(str(body))))
                )
            if returns := node.attributes.get("returns"):
                facts.add(
                    Fact(predicate="Returns", args=(node.name, normalize_schema_name(str(returns))))
                )
        elif node.node_type == "Policy":
            facts.add(Fact(predicate="Policy", args=(node.name,)))
            broad = str(node.attributes.get("broad_catch", "")).lower()
            if (
                broad in {"forbidden", "deny", "false", "no"}
                or "BroadCatch" in node.name
                or "ErrorHandling" in node.name
            ):
                facts.add(Fact(predicate="Policy", args=("ForbidBroadCatch",)))
        elif node.node_type == "Constraint":
            arch = str(node.attributes.get("architecture", "")).lower()
            if arch in {"layered", "router_service_repository", "clean"}:
                facts.add(Fact(predicate="Policy", args=("LayeredArchitecture",)))
            for value in (
                node.attributes.get("avoid", [])
                if isinstance(node.attributes.get("avoid"), list)
                else []
            ):
                if str(value).lower() in {
                    "broad_exception_handlers",
                    "broad_catch",
                    "broad_exception",
                }:
                    facts.add(Fact(predicate="Policy", args=("ForbidBroadCatch",)))
        elif node.node_type == "Invariant":
            facts.add(Fact(predicate="Invariant", args=(node.name,)))
            if entity := node.attributes.get("entity"):
                facts.add(Fact(predicate="InvariantEntity", args=(node.name, str(entity))))
            name = node.name.lower()
            if "broad" in name:
                facts.add(Fact(predicate="Policy", args=("ForbidBroadCatch",)))
        elif node.node_type == "Capability":
            facts.add(Fact(predicate="Capability", args=(node.name,)))
        elif node.node_type == "Role":
            facts.add(Fact(predicate="Role", args=(node.name,)))
            permissions = node.attributes.get("permissions", [])
            if isinstance(permissions, list):
                for permission in permissions:
                    facts.add(Fact(predicate="Permission", args=(node.name, str(permission))))
        elif node.node_type == "Relationship":
            facts.add(Fact(predicate="Relationship", args=(node.name,)))
            if source := node.attributes.get("source"):
                facts.add(Fact(predicate="RelationshipSource", args=(node.name, str(source))))
            if target := node.attributes.get("target"):
                facts.add(Fact(predicate="RelationshipTarget", args=(node.name, str(target))))
            if cardinality := node.attributes.get("cardinality"):
                facts.add(Fact(predicate="Cardinality", args=(node.name, str(cardinality))))
        elif node.node_type == "Workflow":
            facts.add(Fact(predicate="Workflow", args=(node.name,)))
            if entity := node.attributes.get("entity"):
                facts.add(Fact(predicate="WorkflowEntity", args=(node.name, str(entity))))
            actions = node.attributes.get("actions", [])
            if isinstance(actions, list):
                for action in actions:
                    facts.add(Fact(predicate="WorkflowAction", args=(node.name, str(action))))
        elif node.node_type == "BusinessRule":
            facts.add(Fact(predicate="BusinessRule", args=(node.name,)))
            if entity := node.attributes.get("entity"):
                facts.add(Fact(predicate="BusinessRuleEntity", args=(node.name, str(entity))))
        elif node.node_type == "Tenant":
            if str(node.attributes.get("enabled", "")).lower() in {"true", "yes", "1"}:
                facts.add(Fact(predicate="SaaSPrimitive", args=("TenantIsolation",)))
        elif node.node_type == "Audit":
            if str(node.attributes.get("enabled", "")).lower() in {"true", "yes", "1"}:
                facts.add(Fact(predicate="SaaSPrimitive", args=("AuditLog",)))
        elif node.node_type == "Report":
            facts.add(Fact(predicate="Report", args=(node.name,)))
        return facts

    def _symbol(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "", value.title()) or value

    def _diag(self, code: str, message: str, section: SMLSection) -> CompilerDiagnostic:
        return CompilerDiagnostic(
            code=code,
            message=message,
            file=section.source_range.file,
            start_line=section.source_range.start_line,
            end_line=section.source_range.end_line,
        )
