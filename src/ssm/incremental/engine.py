from __future__ import annotations

import contextlib
import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from ssm.architecture.schemas import ArchitecturePlan
from ssm.capabilities.schemas import CapabilityCompositionResult
from ssm.foundation.schemas import AppFoundationPlan
from ssm.incremental.schemas import (
    ArtifactChange,
    ArtifactDiff,
    DependencyEdge,
    DependencyNode,
    FailureClassification,
    RepairDirective,
    SemanticDependencyGraph,
)
from ssm.models import CompileResult, GeneratedFile
from ssm.requirements.schemas import RequirementsIR


class SemanticDependencyGraphBuilder:
    def build(
        self,
        requirements: RequirementsIR,
        foundation: AppFoundationPlan,
        architecture: ArchitecturePlan,
        capabilities: CapabilityCompositionResult,
        sml_text: str,
        compile_result: CompileResult,
    ) -> SemanticDependencyGraph:
        nodes: list[DependencyNode] = []
        edges: list[DependencyEdge] = []
        for item in requirements.requirements:
            nodes.append(
                DependencyNode(
                    id=item.id,
                    layer="requirements",
                    label=f"{item.kind}:{item.name}",
                    content_hash=self._hash_json(item.model_dump()),
                )
            )
        foundation_node = DependencyNode(
            id="foundation.plan",
            layer="foundation",
            label=foundation.app_name,
            content_hash=self._hash_json(foundation.model_dump()),
        )
        architecture_node = DependencyNode(
            id="architecture.plan",
            layer="architecture",
            label=architecture.selected_pattern,
            content_hash=architecture.semantic_fingerprint,
        )
        capability_node = DependencyNode(
            id="capability.composition",
            layer="capability",
            label=capabilities.status,
            content_hash=capabilities.semantic_fingerprint,
        )
        sml_node = DependencyNode(
            id="sml.project",
            layer="sml",
            label="project.sml.md",
            content_hash=self._sha256(sml_text),
        )
        nodes.extend([foundation_node, architecture_node, capability_node, sml_node])
        for item in requirements.requirements:
            edges.append(
                DependencyEdge(source=item.id, target="foundation.plan", relation="normalizes_into")
            )
        edges.extend(
            [
                DependencyEdge(
                    source="foundation.plan", target="architecture.plan", relation="constrains"
                ),
                DependencyEdge(
                    source="foundation.plan", target="capability.composition", relation="requests"
                ),
                DependencyEdge(
                    source="architecture.plan", target="sml.project", relation="governs_rendering"
                ),
                DependencyEdge(
                    source="capability.composition",
                    target="sml.project",
                    relation="bounds_features",
                ),
            ]
        )
        if compile_result.sir is not None:
            for node in compile_result.sir.nodes:
                node_id = f"sir.{node.id}"
                nodes.append(
                    DependencyNode(
                        id=node_id,
                        layer="sir",
                        label=f"{node.node_type}:{node.name}",
                        content_hash=self._hash_json(node.model_dump(mode="json")),
                    )
                )
                edges.append(
                    DependencyEdge(source="sml.project", target=node_id, relation="parses_to")
                )
        for generated in compile_result.files:
            artifact_id = f"artifact.{self._safe_id(generated.path)}"
            nodes.append(
                DependencyNode(
                    id=artifact_id,
                    layer="artifact",
                    label=generated.path,
                    content_hash=self._sha256(generated.content),
                )
            )
            edges.append(
                DependencyEdge(source="sml.project", target=artifact_id, relation="generates")
            )
            for sir_node in self._matching_sir_nodes(generated.path, compile_result):
                edges.append(
                    DependencyEdge(
                        source=f"sir.{sir_node}", target=artifact_id, relation="materializes"
                    )
                )
        return SemanticDependencyGraph(
            nodes=sorted({item.id: item for item in nodes}.values(), key=lambda item: item.id),
            edges=sorted(
                {(item.source, item.target, item.relation): item for item in edges}.values(),
                key=lambda item: (item.source, item.target, item.relation),
            ),
        )

    def _matching_sir_nodes(self, path: str, compile_result: CompileResult) -> list[str]:
        if compile_result.sir is None:
            return []
        lower_path = path.lower()
        matches = [
            node.id
            for node in compile_result.sir.nodes
            if node.name.lower().replace("_", "") in lower_path.replace("_", "")
        ]
        if not matches and path.startswith("app/platform/"):
            matches = [
                node.id
                for node in compile_result.sir.nodes
                if node.node_type in {"Tenant", "Audit", "Role", "Workflow", "BusinessRule"}
            ]
        return matches[:20]

    def _hash_json(self, payload: object) -> str:
        return self._sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))

    def _sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _safe_id(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", ".", value.lower()).strip(".")


class IncrementalArtifactWriter:
    """Write only changed generated artifacts and prove unchanged content."""

    INDEX_NAME = ".ssm_artifact_hashes.json"

    def write(self, files: list[GeneratedFile], out_dir: str | Path) -> ArtifactDiff:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        index_path = out / self.INDEX_NAME
        indexed_before = self._load_index(index_path)
        before = self._actual_hashes(out, indexed_before)
        after = {item.path: self._sha256(item.content) for item in files}
        changes: list[ArtifactChange] = []
        file_map = {item.path: item for item in files}
        for path in sorted(set(before) | set(after)):
            old_hash = before.get(path)
            new_hash = after.get(path)
            status: Literal["added", "modified", "removed", "unchanged"]
            if old_hash is None:
                status = "added"
            elif new_hash is None:
                status = "removed"
            elif old_hash != new_hash:
                status = "modified"
            else:
                status = "unchanged"
            changes.append(
                ArtifactChange(
                    path=path,
                    status=status,
                    before_sha256=old_hash,
                    after_sha256=new_hash,
                    cause_layers=self._cause_layers(path),
                )
            )
            target = out / path
            if status in {"added", "modified"}:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(file_map[path].content.encode("utf-8"))
            elif status == "removed" and target.exists():
                target.unlink()
        self._remove_empty_directories(out)
        index_path.write_text(json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        unchanged_payload = {
            item.path: item.after_sha256 for item in changes if item.status == "unchanged"
        }
        return ArtifactDiff(
            changes=changes,
            added=sum(item.status == "added" for item in changes),
            modified=sum(item.status == "modified" for item in changes),
            removed=sum(item.status == "removed" for item in changes),
            unchanged=sum(item.status == "unchanged" for item in changes),
            unchanged_proof_sha256=self._sha256(
                json.dumps(unchanged_payload, sort_keys=True, separators=(",", ":"))
            ),
        )

    def _actual_hashes(self, root: Path, indexed: dict[str, str]) -> dict[str, str]:
        actual: dict[str, str] = {}
        for relative_path in indexed:
            path = root / relative_path
            if path.is_file():
                actual[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
        return actual

    def _load_index(self, path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return (
            {str(key): str(value) for key, value in payload.items()}
            if isinstance(payload, dict)
            else {}
        )

    def _remove_empty_directories(self, root: Path) -> None:
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir() and path != root:
                with contextlib.suppress(OSError):
                    path.rmdir()

    def _cause_layers(self, path: str) -> list[str]:
        if path.startswith("tests/"):
            return ["sml", "target_pack", "generated_test"]
        if path.startswith("app/platform/"):
            return ["foundation", "capability", "sml", "target_pack"]
        if path.startswith("app/"):
            return ["foundation", "architecture", "sml", "target_pack"]
        if path.endswith(".json") or "evidence" in path:
            return ["requirements", "foundation", "architecture", "capability", "evidence"]
        return ["sml", "target_pack"]

    def _sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FailureClassifier:
    def classify(self, failure_code: str, source: str = "compiler") -> FailureClassification:
        code = failure_code.upper()
        layer: Literal[
            "requirements",
            "foundation",
            "architecture",
            "capability",
            "sml",
            "target_pack",
            "generated_test",
            "environment",
        ]
        if code.startswith(("REQ", "INTENT")):
            layer = "requirements"
        elif code.startswith("ARCH"):
            layer = "architecture"
        elif code.startswith("CAP"):
            layer = "capability"
        elif code.startswith(("SEM", "SML")):
            layer = "sml"
        elif "TEST" in code or "PYTEST" in code:
            layer = "generated_test"
        elif any(token in code for token in ["RUFF", "MYPY", "IMPORT", "CODEGEN"]):
            layer = "target_pack"
        elif any(token in code for token in ["ALEMBIC", "DATABASE", "DOCKER", "TIMEOUT"]):
            layer = "environment"
        else:
            layer = "foundation"
        retryable = layer in {"requirements", "foundation", "architecture", "capability", "sml"}
        return FailureClassification(
            source=source,
            failure_code=failure_code,
            target_layer=layer,
            retryable=retryable,
            rationale=f"Failure {failure_code} is owned by the {layer} abstraction boundary.",
        )


class RepairRouter:
    def route(self, classification: FailureClassification) -> RepairDirective:
        permitted = {
            "requirements": ["requirements_ir.json"],
            "foundation": ["foundation_plan.json"],
            "architecture": ["architecture_plan.json"],
            "capability": ["capability_composition.json"],
            "sml": ["project.sml.md"],
            "target_pack": ["src/ssm/backends/**"],
            "generated_test": ["src/ssm/backends/**/test*", "tests/**"],
            "environment": ["scripts/**", "Dockerfile", "docker-compose.yml"],
        }
        forbidden = []
        if classification.target_layer in {
            "requirements",
            "foundation",
            "architecture",
            "capability",
            "sml",
        }:
            forbidden = ["generated_app/app/**"]
        return RepairDirective(
            target_layer=classification.target_layer,
            failure_code=classification.failure_code,
            permitted_paths=permitted[classification.target_layer],
            forbidden_paths=forbidden,
            requires_full_regeneration=classification.target_layer
            in {"target_pack", "environment"},
            rationale=(
                "Repair the highest owning abstraction and regenerate downstream artifacts; "
                "do not patch compiler-owned generated source directly."
            ),
        )
