from __future__ import annotations

import hashlib
import json
from typing import Literal

from ssm.architecture.resolver import ConstrainedArchitectureResolver
from ssm.architecture.schemas import ArchitecturePlan
from ssm.capabilities.composer import CapabilityComposer
from ssm.capabilities.schemas import CapabilityCompositionResult
from ssm.certification.schemas import (
    CertificationCheck,
    CertificationReport,
    SeniorGradeMetrics,
    VariabilityMetrics,
)
from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.renderer import FoundationSMLRenderer
from ssm.foundation.schemas import (
    AppCapabilityContract,
    AppFoundationPlan,
    CapabilityNegotiationResult,
)
from ssm.incremental.engine import FailureClassifier, RepairRouter
from ssm.models import CompileResult
from ssm.pipeline import SSMCompiler
from ssm.requirements.extractor import IntentRequirementsCompiler
from ssm.requirements.schemas import RequirementsIR


class SeniorGradeCertifier:
    """Empirically evaluate the supported compiler profile without overclaiming."""

    def certify(
        self,
        *,
        source_text: str,
        source_name: str,
        requirements: RequirementsIR,
        foundation: AppFoundationPlan,
        architecture: ArchitecturePlan,
        capabilities: CapabilityCompositionResult,
        negotiation: CapabilityNegotiationResult,
        sml_text: str,
        compile_result: CompileResult,
        repetitions: int = 3,
    ) -> CertificationReport:
        variability = self._variability(source_text, source_name, repetitions)
        checks: list[CertificationCheck] = []
        blocking: list[str] = []
        warnings: list[str] = []

        if requirements.contradictions:
            blocking.append("Requirements contain unresolved contradictions.")
            checks.append(
                CertificationCheck(
                    check_id="requirements.contradictions",
                    category="requirements",
                    status="fail",
                    message="Contradictory high-impact requirements remain unresolved.",
                    evidence=[item.id for item in requirements.contradictions],
                )
            )
        else:
            checks.append(
                CertificationCheck(
                    check_id="requirements.contradictions",
                    category="requirements",
                    status="pass",
                    message="No deterministic requirement contradictions were detected.",
                )
            )

        blocking_ambiguities = [item for item in requirements.ambiguities if item.blocking]
        ambiguity_status: Literal["pass", "warning", "fail"]
        if blocking_ambiguities:
            blocking.append("Requirements contain blocking ambiguities.")
            ambiguity_status = "fail"
        elif requirements.ambiguities:
            warnings.append("Non-blocking ambiguities are recorded and defaults remain explicit.")
            ambiguity_status = "warning"
        else:
            ambiguity_status = "pass"
        checks.append(
            CertificationCheck(
                check_id="requirements.ambiguity_register",
                category="requirements",
                status=ambiguity_status,
                message=(
                    "Ambiguities are explicitly registered; none are silently collapsed."
                    if requirements.ambiguities
                    else "No material ambiguities were detected."
                ),
                evidence=[item.id for item in requirements.ambiguities],
            )
        )

        negotiation_status: Literal["pass", "warning", "fail"]
        if negotiation.status == "UNSUPPORTED":
            blocking.append("Foundation capability negotiation rejected the plan.")
            negotiation_status = "fail"
        elif negotiation.status in {"PARTIALLY_SUPPORTED", "SUPPORTED_WITH_ASSUMPTIONS"}:
            warnings.append(f"Foundation negotiation status is {negotiation.status}.")
            negotiation_status = "warning"
        else:
            negotiation_status = "pass"
        checks.append(
            CertificationCheck(
                check_id="foundation.negotiation",
                category="capability",
                status=negotiation_status,
                message=f"Foundation negotiation status: {negotiation.status}.",
                evidence=[issue.code for issue in negotiation.issues],
            )
        )

        partial_packs = [
            item.capability_id
            for item in capabilities.selected
            if item.implementation_status != "production"
        ]
        capability_status: Literal["pass", "warning", "fail"]
        if capabilities.status == "UNSUPPORTED":
            blocking.append("Capability composition contains unsupported selections.")
            capability_status = "fail"
        elif partial_packs:
            warnings.append(
                "Contract-only or scaffold capability packs are visible: "
                + ", ".join(partial_packs)
            )
            capability_status = "warning"
        else:
            capability_status = "pass"
        checks.append(
            CertificationCheck(
                check_id="capability.honesty",
                category="capability",
                status=capability_status,
                message=(
                    "Every non-production capability is explicitly labeled and limited."
                    if partial_packs
                    else "All selected capabilities are production-backed in the current target."
                ),
                evidence=partial_packs,
            )
        )

        selected_candidates = [
            item for item in architecture.candidates if item.status == "selected"
        ]
        rejected_candidates = [
            item for item in architecture.candidates if item.status == "rejected"
        ]
        architecture_ok = len(selected_candidates) == 1 and bool(rejected_candidates)
        checks.append(
            CertificationCheck(
                check_id="architecture.constrained_resolution",
                category="architecture",
                status="pass" if architecture_ok else "fail",
                message=(
                    "Architecture selection records one selected candidate and explicit rejected alternatives."
                    if architecture_ok
                    else "Architecture candidate resolution is incomplete."
                ),
                evidence=[item.id for item in architecture.candidates],
            )
        )
        if not architecture_ok:
            blocking.append("Architecture resolution is not singular and evidence-backed.")

        deterministic = variability.unique_generated_tree_hashes == 1
        checks.append(
            CertificationCheck(
                check_id="generation.determinism",
                category="variability",
                status="pass" if deterministic else "fail",
                message=(
                    "Repeated supported-profile compilation produced one generated tree hash."
                    if deterministic
                    else "Repeated compilation produced divergent generated trees."
                ),
                evidence=[str(variability.unique_generated_tree_hashes)],
            )
        )
        if not deterministic:
            blocking.append("Generated artifact determinism failed.")

        semantic_stable = variability.semantic_variance_score == 0.0
        checks.append(
            CertificationCheck(
                check_id="generation.semantic_stability",
                category="variability",
                status="pass" if semantic_stable else "fail",
                message=(
                    "Requirements, architecture, capabilities, and SML are semantically stable across runs."
                    if semantic_stable
                    else "Semantic collapse artifacts vary across repeated runs."
                ),
            )
        )
        if not semantic_stable:
            blocking.append("Semantic collapse stability failed.")

        repair = RepairRouter().route(FailureClassifier().classify("SEM202"))
        repair_integrity = "generated_app/app/**" in repair.forbidden_paths
        checks.append(
            CertificationCheck(
                check_id="repair.abstraction_boundary",
                category="repair",
                status="pass" if repair_integrity else "fail",
                message="Semantic failures route to SML and forbid direct generated-source repair.",
                evidence=repair.forbidden_paths,
            )
        )
        if not repair_integrity:
            blocking.append("Repair routing permits abstraction-boundary violations.")

        metrics = self._metrics(
            requirements,
            architecture_ok=architecture_ok,
            capabilities=capabilities,
            deterministic=deterministic,
            repair_integrity=repair_integrity,
        )
        final_status: Literal[
            "CERTIFIED_SUPPORTED_PROFILE",
            "CONDITIONAL_SUPPORTED_PROFILE",
            "REJECTED",
        ]
        if blocking:
            final_status = "REJECTED"
            conclusion = (
                "The source cannot be certified because one or more high-impact semantic, "
                "architecture, capability, or determinism gates failed."
            )
        elif warnings:
            final_status = "CONDITIONAL_SUPPORTED_PROFILE"
            conclusion = (
                "The generated application is a senior-engineer-shaped baseline within the declared "
                "FastAPI profile, with explicit assumptions or partially implemented capability packs."
            )
        else:
            final_status = "CERTIFIED_SUPPORTED_PROFILE"
            conclusion = (
                "The supported-profile application passed semantic stability, constrained architecture, "
                "capability honesty, deterministic generation, and repair-boundary checks."
            )
        return CertificationReport(
            status=final_status,
            checks=checks,
            variability=variability,
            metrics=metrics,
            blocking_reasons=blocking,
            warnings=warnings,
            conclusion=conclusion,
        )

    def _variability(
        self, source_text: str, source_name: str, repetitions: int
    ) -> VariabilityMetrics:
        extractor = IntentRequirementsCompiler()
        planner = AppFoundationPlanner()
        renderer = FoundationSMLRenderer()
        compiler = SSMCompiler()
        req_hashes: set[str] = set()
        arch_hashes: set[str] = set()
        capability_hashes: set[str] = set()
        sml_hashes: set[str] = set()
        tree_hashes: set[str] = set()
        for _ in range(max(2, repetitions)):
            requirements = extractor.compile_text(source_text, source_name=source_name)
            foundation = planner.plan(source_text)
            self._apply_requirements(foundation, requirements)
            architecture = ConstrainedArchitectureResolver().resolve(requirements, foundation)
            capabilities = CapabilityComposer().compose(requirements, foundation)
            self._apply_capabilities(foundation, capabilities)
            sml = renderer.render(foundation, architecture_pattern=architecture.selected_pattern)
            result = compiler.compile_text(sml, source_file=f"{source_name}::project.sml.md")
            req_hashes.add(requirements.semantic_fingerprint)
            arch_hashes.add(architecture.semantic_fingerprint)
            capability_hashes.add(capabilities.semantic_fingerprint)
            sml_hashes.add(self._sha256(sml))
            tree_hashes.add(self._tree_hash(result))
        dimensions = [req_hashes, arch_hashes, capability_hashes, sml_hashes, tree_hashes]
        variance = sum(max(0, len(values) - 1) for values in dimensions) / len(dimensions)
        return VariabilityMetrics(
            extraction_runs=max(2, repetitions),
            unique_requirements_fingerprints=len(req_hashes),
            unique_architecture_fingerprints=len(arch_hashes),
            unique_capability_fingerprints=len(capability_hashes),
            unique_sml_hashes=len(sml_hashes),
            unique_generated_tree_hashes=len(tree_hashes),
            semantic_variance_score=variance,
        )

    def _metrics(
        self,
        requirements: RequirementsIR,
        *,
        architecture_ok: bool,
        capabilities: CapabilityCompositionResult,
        deterministic: bool,
        repair_integrity: bool,
    ) -> SeniorGradeMetrics:
        total = max(1, len(requirements.requirements))
        accepted = sum(item.status == "accepted" for item in requirements.requirements)
        explicit = [item for item in requirements.requirements if item.origin == "explicit"]
        explicit_accepted = sum(item.status == "accepted" for item in explicit)
        nonproduction = [
            item for item in capabilities.selected if item.implementation_status != "production"
        ]
        honest = all(item.limitations for item in nonproduction)
        visible_unsupported = bool(requirements.unsupported_features) or not any(
            item.status == "unsupported" for item in requirements.requirements
        )
        return SeniorGradeMetrics(
            requirements_coverage=accepted / total,
            explicit_requirement_coverage=(explicit_accepted / max(1, len(explicit))),
            architecture_consistency=1.0 if architecture_ok else 0.0,
            capability_honesty=1.0 if honest else 0.0,
            deterministic_generation=1.0 if deterministic else 0.0,
            unsupported_visibility=1.0 if visible_unsupported else 0.0,
            repair_boundary_integrity=1.0 if repair_integrity else 0.0,
        )

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

    def _tree_hash(self, result: CompileResult) -> str:
        payload = {
            item.path: hashlib.sha256(item.content.encode("utf-8")).hexdigest()
            for item in sorted(result.files, key=lambda value: value.path)
        }
        return self._sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")))

    def _sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
