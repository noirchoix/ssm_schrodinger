from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypeVar

from ssm.architecture.resolver import ConstrainedArchitectureResolver
from ssm.auto_research.hashing import sha256_value
from ssm.auto_research.records import build_generation_run_record, write_generation_run_record
from ssm.auto_research.schemas import MetricObservation
from ssm.auto_research.trace import TraceRecorder
from ssm.capabilities.composer import CapabilityComposer
from ssm.capabilities.schemas import CapabilityCompositionResult
from ssm.certification.evaluator import SeniorGradeCertifier
from ssm.errors import SSMError
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.renderer import FoundationSMLRenderer
from ssm.foundation.schemas import AppCapabilityContract, AppFoundationPlan
from ssm.incremental.engine import IncrementalArtifactWriter, SemanticDependencyGraphBuilder
from ssm.pipeline import SSMCompiler
from ssm.product.schemas import CollapsePlan, ProductBuildResult
from ssm.requirements.extractor import IntentRequirementsCompiler
from ssm.requirements.schemas import RequirementsIR


class IntentCompilationError(SSMError):
    pass


T = TypeVar("T")


class SchrodingerProductCompiler:
    """High-level uncertainty-collapse pipeline above the deterministic SSM compiler."""

    def __init__(self) -> None:
        self.requirements_compiler = IntentRequirementsCompiler()
        self.foundation_planner = AppFoundationPlanner()
        self.architecture_resolver = ConstrainedArchitectureResolver()
        self.capability_composer = CapabilityComposer()
        self.negotiator = CapabilityNegotiator()
        self.renderer = FoundationSMLRenderer()
        self.compiler = SSMCompiler()
        self.graph_builder = SemanticDependencyGraphBuilder()
        self.writer = IncrementalArtifactWriter()
        self.certifier = SeniorGradeCertifier()

    def collapse_file(self, path: str | Path) -> CollapsePlan:
        source = Path(path)
        return self.collapse_text(source.read_text(encoding="utf-8"), source_name=str(source))

    def collapse_text(
        self,
        text: str,
        source_name: str = "<memory>",
        *,
        trace_recorder: TraceRecorder | None = None,
    ) -> CollapsePlan:
        requirements = self._run_stage(
            trace_recorder,
            "requirements",
            {"source_name": source_name, "source_sha256": sha256_value(text)},
            lambda: self.requirements_compiler.compile_text(text, source_name=source_name),
        )
        foundation = self._run_stage(
            trace_recorder,
            "foundation",
            {"requirements": requirements.semantic_fingerprint},
            lambda: self.foundation_planner.plan(text),
        )
        self._apply_requirements(foundation, requirements)
        architecture = self._run_stage(
            trace_recorder,
            "architecture",
            {
                "requirements": requirements.semantic_fingerprint,
                "foundation": sha256_value(foundation.model_dump(mode="json")),
            },
            lambda: self.architecture_resolver.resolve(requirements, foundation),
        )
        capabilities = self._run_stage(
            trace_recorder,
            "capabilities",
            {"architecture": architecture.semantic_fingerprint},
            lambda: self.capability_composer.compose(requirements, foundation),
        )
        self._apply_capabilities(foundation, capabilities)
        negotiation = self._run_stage(
            trace_recorder,
            "negotiation",
            {"capabilities": capabilities.semantic_fingerprint},
            lambda: self.negotiator.negotiate_plan(foundation),
        )
        sml_text = self._run_stage(
            trace_recorder,
            "sml",
            {"architecture_pattern": architecture.selected_pattern},
            lambda: self.renderer.render(
                foundation, architecture_pattern=architecture.selected_pattern
            ),
        )
        return CollapsePlan(
            requirements=requirements,
            foundation=foundation,
            architecture=architecture,
            capabilities=capabilities,
            negotiation=negotiation,
            sml_text=sml_text,
        )

    def build_file(
        self,
        path: str | Path,
        *,
        out_dir: str | Path,
        allow_partial: bool = False,
        certification_repetitions: int = 3,
    ) -> ProductBuildResult:
        source = Path(path)
        return self.build_text(
            source.read_text(encoding="utf-8"),
            source_name=str(source),
            out_dir=out_dir,
            allow_partial=allow_partial,
            certification_repetitions=certification_repetitions,
        )

    def build_text(
        self,
        text: str,
        *,
        source_name: str = "<memory>",
        out_dir: str | Path | None = None,
        allow_partial: bool = False,
        certification_repetitions: int = 3,
        task_id: str | None = None,
        benchmark_case_id: str | None = None,
        replicate_id: str = "0",
        provider: str | None = None,
        model: str | None = None,
        scaffold_version: str | None = None,
        prompt_version: str | None = None,
        slices: dict[str, str] | None = None,
    ) -> ProductBuildResult:
        started_at = datetime.now(UTC)
        started_monotonic = time.monotonic()
        output = Path(out_dir) if out_dir is not None else None
        trace_recorder = None
        if output is not None:
            output.mkdir(parents=True, exist_ok=True)
            trace_recorder = TraceRecorder(
                output / "generation_trace.jsonl",
                task=task_id or source_name,
                task_input={"source_sha256": sha256_value(text)},
                attrs={
                    "benchmark_case_id": benchmark_case_id or "",
                    "replicate_id": replicate_id,
                },
            )
        collapse = self.collapse_text(text, source_name=source_name, trace_recorder=trace_recorder)
        blocking = self._blocking_reasons(collapse)
        if blocking and not allow_partial:
            if trace_recorder is not None:
                trace_recorder.set_task_output({"status": "REJECTED", "blocking": blocking})
            raise IntentCompilationError("\n".join(blocking))
        compile_result = self._run_stage(
            trace_recorder,
            "sir_and_target_generation",
            {"sml_sha256": sha256_value(collapse.sml_text)},
            lambda: self.compiler.compile_text(
                collapse.sml_text, source_file=f"{source_name}::project.sml.md"
            ),
        )
        dependency_graph = self._run_stage(
            trace_recorder,
            "dependency_graph",
            {"generated_file_count": len(compile_result.files)},
            lambda: self.graph_builder.build(
                collapse.requirements,
                collapse.foundation,
                collapse.architecture,
                collapse.capabilities,
                collapse.sml_text,
                compile_result,
            ),
        )
        certification = self._run_stage(
            trace_recorder,
            "certification",
            {"repetitions": certification_repetitions},
            lambda: self.certifier.certify(
                source_text=text,
                source_name=source_name,
                requirements=collapse.requirements,
                foundation=collapse.foundation,
                architecture=collapse.architecture,
                capabilities=collapse.capabilities,
                negotiation=collapse.negotiation,
                sml_text=collapse.sml_text,
                compile_result=compile_result,
                repetitions=certification_repetitions,
            ),
        )
        warnings = sorted(
            set(certification.warnings)
            | set(collapse.capabilities.limitations)
            | {item.description for item in collapse.requirements.ambiguities if not item.blocking}
        )
        status: Literal["ACCEPTED", "CONDITIONAL", "REJECTED"] = (
            "REJECTED"
            if certification.status == "REJECTED"
            else "CONDITIONAL"
            if certification.status == "CONDITIONAL_SUPPORTED_PROFILE"
            else "ACCEPTED"
        )
        artifact_diff = None
        if output is not None:
            generated_dir = output / "generated_app"
            artifact_diff = self.writer.write(compile_result.files, generated_dir)
            self._write_json(output / "requirements_ir.json", collapse.requirements.model_dump())
            self._write_json(output / "foundation_plan.json", collapse.foundation.model_dump())
            self._write_json(output / "architecture_plan.json", collapse.architecture.model_dump())
            self._write_json(
                output / "capability_composition.json", collapse.capabilities.model_dump()
            )
            self._write_json(
                output / "capability_negotiation.json", collapse.negotiation.model_dump()
            )
            (output / "project.sml.md").write_text(collapse.sml_text, encoding="utf-8")
            self._write_json(output / "dependency_graph.json", dependency_graph.model_dump())
            self._write_json(output / "artifact_diff.json", artifact_diff.model_dump())
            self._write_json(output / "certification_report.json", certification.model_dump())
            stage_fingerprints = self._stage_fingerprints(collapse, compile_result, certification)
            duration_ms = int((time.monotonic() - started_monotonic) * 1000)
            metrics = {
                "compile_success": MetricObservation(
                    name="compile_success", value=status != "REJECTED", source="compiler_status"
                ),
                "generated_file_count": MetricObservation(
                    name="generated_file_count",
                    value=len(compile_result.files),
                    unit="files",
                    source="compile_result",
                ),
                "semantic_variance_score": MetricObservation(
                    name="semantic_variance_score",
                    value=certification.variability.semantic_variance_score,
                    source="certification_report",
                ),
                "repair_attempts": MetricObservation(
                    name="repair_attempts", value=0, unit="attempts", source="offline_compiler"
                ),
                "requirements_coverage": MetricObservation(
                    name="requirements_coverage",
                    value=certification.metrics.requirements_coverage,
                    source="certification_report",
                ),
                "capability_honesty": MetricObservation(
                    name="capability_honesty",
                    value=certification.metrics.capability_honesty,
                    source="certification_report",
                ),
            }
            inferred_slices = self._research_slices(collapse)
            inferred_slices.update(slices or {})
            if trace_recorder is not None:
                trace_recorder.set_task_output(
                    {
                        "status": status,
                        "generated_file_count": len(compile_result.files),
                        "generated_tree_sha256": stage_fingerprints["generated_tree"],
                    }
                )
            run_record = build_generation_run_record(
                output=output,
                source_text=text,
                source_name=source_name,
                status=status,
                started_at=started_at,
                duration_ms=duration_ms,
                task_id=task_id,
                benchmark_case_id=benchmark_case_id,
                replicate_id=replicate_id,
                stage_fingerprints=stage_fingerprints,
                metrics=metrics,
                trace_ids=[trace_recorder.trace_id] if trace_recorder is not None else [],
                slices=inferred_slices,
                warnings=warnings,
                errors=blocking,
                provider=provider,
                model=model,
                scaffold_version=scaffold_version,
                prompt_version=prompt_version,
            )
            write_generation_run_record(output / "generation_run.json", run_record)
            self._write_build_manifest(output)
        return ProductBuildResult(
            status=status,
            out_dir=str(output) if output is not None else None,
            generated_app_dir=str(output / "generated_app") if output is not None else None,
            generated_file_count=len(compile_result.files),
            requirements_fingerprint=collapse.requirements.semantic_fingerprint,
            architecture_fingerprint=collapse.architecture.semantic_fingerprint,
            capability_fingerprint=collapse.capabilities.semantic_fingerprint,
            selected_architecture=collapse.architecture.selected_pattern,
            negotiation_status=collapse.negotiation.status,
            capability_status=collapse.capabilities.status,
            artifact_diff=artifact_diff,
            dependency_graph=dependency_graph,
            certification=certification,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    def _run_stage(
        self,
        recorder: TraceRecorder | None,
        name: str,
        input_value: object,
        operation: Callable[[], T],
    ) -> T:
        if recorder is None:
            return operation()
        with recorder.span("memory_op", name, input_value=input_value) as span:
            result = operation()
            span.set_output(self._stage_output(result))
            return result

    def _stage_output(self, value: object) -> dict[str, object]:
        if hasattr(value, "model_dump"):
            payload = value.model_dump(mode="json")
        elif isinstance(value, str):
            payload = value
        elif hasattr(value, "files"):
            payload = {
                "files": [
                    {"path": item.path, "sha256": sha256_value(item.content)}
                    for item in value.files
                ]
            }
        else:
            payload = str(value)
        return {"sha256": sha256_value(payload)}

    def _stage_fingerprints(
        self, collapse: CollapsePlan, compile_result: object, certification: object
    ) -> dict[str, str]:
        sir = getattr(compile_result, "sir", None)
        files = getattr(compile_result, "files", [])
        return {
            "requirements": collapse.requirements.semantic_fingerprint,
            "foundation": sha256_value(collapse.foundation.model_dump(mode="json")),
            "architecture": collapse.architecture.semantic_fingerprint,
            "capabilities": collapse.capabilities.semantic_fingerprint,
            "negotiation": sha256_value(collapse.negotiation.model_dump(mode="json")),
            "sml": sha256_value(collapse.sml_text),
            "sir": sha256_value(sir.model_dump(mode="json") if sir is not None else {}),
            "generated_tree": sha256_value(
                {item.path: sha256_value(item.content) for item in files}
            ),
            "quality_gates": sha256_value(certification.model_dump(mode="json")),  # type: ignore[attr-defined]
        }

    def _research_slices(self, collapse: CollapsePlan) -> dict[str, str]:
        capability_ids = sorted(item.capability_id for item in collapse.capabilities.selected)
        return {
            "domain_pack": "+".join(sorted(collapse.negotiation.selected_domain_packs))
            or "generic",
            "database": collapse.foundation.database,
            "tenancy": "enabled" if collapse.foundation.tenant_enabled else "disabled",
            "workflow": "enabled" if collapse.foundation.workflows else "disabled",
            "update_model": "present"
            if any(entity.name.endswith("Update") for entity in collapse.foundation.entities)
            else "absent",
            "rule_complexity": "contextual_or_multi"
            if collapse.foundation.business_rules
            else "none",
            "capabilities": "+".join(capability_ids),
        }

    def _apply_requirements(
        self, foundation: AppFoundationPlan, requirements: RequirementsIR
    ) -> None:
        foundation.requirement_trace_ids = [item.id for item in requirements.requirements]
        foundation.requirement_trace = self._requirement_trace(foundation, requirements)
        foundation.unsupported_features = sorted(
            set(foundation.unsupported_features) | set(requirements.unsupported_features)
        )
        foundation.assumptions = sorted(
            set(foundation.assumptions) | {item.statement for item in requirements.assumptions}
        )
        foundation.questions = sorted(
            set(foundation.questions) | {item.description for item in requirements.ambiguities}
        )
        for key, value in requirements.stack_hints.items():
            if key == "backend":
                foundation.backend = value
            elif key == "database":
                foundation.database = value
            elif key == "auth":
                foundation.auth = value
        explicit_names = {
            item.name for item in requirements.requirements if item.origin == "explicit"
        }
        if "MultiTenant" in explicit_names:
            foundation.tenant_enabled = True
        if "Audit" in explicit_names:
            foundation.audit_enabled = True

    def _apply_capabilities(
        self,
        foundation: AppFoundationPlan,
        capabilities: CapabilityCompositionResult,
    ) -> None:
        foundation.capabilities = [
            AppCapabilityContract(
                capability_id=item.capability_id,
                support_status=item.support_status,
                implementation_status=item.implementation_status,
                guarantees=item.guarantees,
                limitations=item.limitations,
                requirement_ids=item.requirement_ids,
            )
            for item in capabilities.selected
        ]
        for item in foundation.capabilities:
            foundation.requirement_trace[f"capability.{item.capability_id}"] = list(
                item.requirement_ids
            )

    def _requirement_trace(
        self, foundation: AppFoundationPlan, requirements: RequirementsIR
    ) -> dict[str, list[str]]:
        trace: dict[str, list[str]] = {
            "plan": sorted(item.id for item in requirements.requirements)
        }
        for entity in foundation.entities:
            trace[f"entity.{entity.name}"] = self._matching_requirement_ids(
                requirements, "entity", entity.name
            )
        for role in foundation.roles:
            trace[f"role.{role.name}"] = self._matching_requirement_ids(
                requirements, "actor", role.name
            )
        for workflow in foundation.workflows:
            trace[f"workflow.{workflow.name}"] = self._matching_requirement_ids(
                requirements, "workflow", workflow.name
            )
        return trace

    def _matching_requirement_ids(
        self, requirements: RequirementsIR, kind: str, name: str
    ) -> list[str]:
        normalized_name = self._normalize_name(name)
        return sorted(
            item.id
            for item in requirements.requirements
            if item.kind == kind and self._normalize_name(item.name) == normalized_name
        )

    def _normalize_name(self, value: str) -> str:
        return "".join(character.lower() for character in value if character.isalnum())

    def _blocking_reasons(self, collapse: CollapsePlan) -> list[str]:
        reasons = [
            f"Contradiction {item.id}: {item.description}"
            for item in collapse.requirements.contradictions
        ]
        reasons.extend(
            f"Blocking ambiguity {item.id}: {item.description}"
            for item in collapse.requirements.ambiguities
            if item.blocking
        )
        if collapse.negotiation.status == "UNSUPPORTED":
            reasons.append("Foundation capability negotiation is UNSUPPORTED.")
        if collapse.capabilities.status == "UNSUPPORTED":
            reasons.append("Capability composition is UNSUPPORTED.")
        return reasons

    def _write_build_manifest(self, output: Path) -> None:
        files: dict[str, str] = {}
        for path in sorted(output.rglob("*")):
            if not path.is_file() or path.name == "build_manifest.json":
                continue
            relative = path.relative_to(output).as_posix()
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        payload = {
            "schema_version": "2.6",
            "kind": "SchrodingerBuildManifest",
            "hash_algorithm": "sha256",
            "files": files,
            "root_hash": hashlib.sha256(
                json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }
        self._write_json(output / "build_manifest.json", payload)

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
