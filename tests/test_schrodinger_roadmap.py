from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssm.architecture import ConstrainedArchitectureResolver
from ssm.capabilities import CapabilityComposer
from ssm.cli.main import main
from ssm.foundation.planner import AppFoundationPlanner
from ssm.incremental import FailureClassifier, RepairRouter
from ssm.product import IntentCompilationError, SchrodingerProductCompiler
from ssm.requirements import IntentRequirementsCompiler

HR_README = """# Workforce Leave Platform

Build a multi-tenant HR leave management application using FastAPI, PostgreSQL, and JWT.

## Actors
- Employee
- Manager
- HR Admin

## Entities
- Employee
- Leave Request

## Features
- CRUD for employees and leave requests
- Manager approval workflow
- Audit trail
- Structured logging
"""


def test_requirements_ir_is_stable_and_traceable() -> None:
    compiler = IntentRequirementsCompiler()
    first = compiler.compile_text(HR_README, source_name="README.md")
    second = compiler.compile_text(HR_README, source_name="README.md")

    assert first.semantic_fingerprint == second.semantic_fingerprint
    assert first.source_sha256 == second.source_sha256
    assert first.requirements
    assert len({item.id for item in first.requirements}) == len(first.requirements)
    assert any(item.origin == "explicit" for item in first.requirements)
    assert any(item.name == "LeaveRequest" for item in first.requirements)
    assert first.contradictions == []
    collapse = SchrodingerProductCompiler().collapse_text(HR_README)
    assert collapse.foundation.requirement_trace["entity.Employee"]
    assert "#Decision ArchitecturePattern" in collapse.sml_text
    assert "#Capability observability" in collapse.sml_text


def test_vague_generic_readme_is_not_silently_mapped_to_product() -> None:
    text = "# New Platform\nBuild a scalable application that is easy to use."
    requirements = IntentRequirementsCompiler().compile_text(text)

    assert any(item.blocking for item in requirements.ambiguities)
    with pytest.raises(IntentCompilationError):
        SchrodingerProductCompiler().build_text(text, out_dir=None)


def test_requirements_compiler_exposes_high_impact_contradictions() -> None:
    text = """# Conflicted App
Use PostgreSQL and in-memory persistence.
Require JWT authentication but expose a public API with no authentication.
"""
    requirements = IntentRequirementsCompiler().compile_text(text)

    assert {item.topic for item in requirements.contradictions} == {
        "Authentication strategy",
        "Database strategy",
    }
    with pytest.raises(IntentCompilationError):
        SchrodingerProductCompiler().build_text(text, out_dir=None)


def test_architecture_resolution_is_candidate_based_and_singular() -> None:
    requirements = IntentRequirementsCompiler().compile_text(HR_README)
    foundation = AppFoundationPlanner().plan(HR_README)
    architecture = ConstrainedArchitectureResolver().resolve(requirements, foundation)

    selected = [item for item in architecture.candidates if item.status == "selected"]
    rejected = [item for item in architecture.candidates if item.status == "rejected"]
    assert [item.id for item in selected] == ["arch.layered_modular_monolith"]
    assert {item.id for item in rejected} >= {
        "arch.direct_route_repository",
        "arch.microservices",
    }
    assert architecture.transaction_boundaries
    assert architecture.use_cases
    assert architecture.proof.selected_candidate_id == selected[0].id


def test_capability_composition_never_promotes_scaffolds_to_supported() -> None:
    text = HR_README + "\nDeliver signed webhooks with retries and idempotency.\n"
    requirements = IntentRequirementsCompiler().compile_text(text)
    foundation = AppFoundationPlanner().plan(text)
    composition = CapabilityComposer().compose(requirements, foundation)
    selections = {item.capability_id: item for item in composition.selected}

    assert composition.status == "PARTIALLY_SUPPORTED"
    assert selections["webhooks"].implementation_status == "scaffold"
    assert selections["webhooks"].support_status == "PARTIALLY_SUPPORTED"
    assert selections["webhooks"].limitations
    assert selections["idempotency"].implementation_status == "contract_only"


def test_failure_routing_preserves_compiler_owned_source_boundary() -> None:
    classification = FailureClassifier().classify("SEM202")
    directive = RepairRouter().route(classification)

    assert classification.target_layer == "sml"
    assert directive.permitted_paths == ["project.sml.md"]
    assert "generated_app/app/**" in directive.forbidden_paths
    assert directive.requires_full_regeneration is False


def test_product_build_emits_all_collapse_and_certification_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "product"
    product = SchrodingerProductCompiler()
    first = product.build_text(
        HR_README,
        source_name="README.md",
        out_dir=output,
        certification_repetitions=2,
    )
    generated_main = output / "generated_app" / "app" / "main.py"
    generated_main.write_text("# manual drift\n", encoding="utf-8")
    second = product.build_text(
        HR_README,
        source_name="README.md",
        out_dir=output,
        certification_repetitions=2,
    )

    assert first.status in {"ACCEPTED", "CONDITIONAL"}
    assert first.certification is not None
    assert first.certification.variability.semantic_variance_score == 0.0
    assert first.certification.variability.unique_generated_tree_hashes == 1
    assert second.artifact_diff is not None
    assert second.artifact_diff.modified == 1
    assert second.artifact_diff.removed == 0
    assert second.artifact_diff.unchanged > 0
    assert generated_main.read_text(encoding="utf-8") != "# manual drift\n"
    assert second.artifact_diff.unchanged_proof_sha256

    required = [
        "requirements_ir.json",
        "foundation_plan.json",
        "architecture_plan.json",
        "capability_composition.json",
        "capability_negotiation.json",
        "project.sml.md",
        "dependency_graph.json",
        "artifact_diff.json",
        "certification_report.json",
        "build_manifest.json",
        "generated_app/app/main.py",
    ]
    for relative in required:
        assert (output / relative).exists(), relative

    manifest = json.loads((output / "build_manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "SchrodingerBuildManifest"
    assert manifest["root_hash"]


def test_new_cli_commands_accept_readme_input(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(HR_README, encoding="utf-8")
    requirements_out = tmp_path / "requirements.json"
    collapse_out = tmp_path / "collapse.json"
    product_out = tmp_path / "product"

    assert main(["requirements", "--file", str(readme), "--out", str(requirements_out)]) == 0
    assert main(["collapse-plan", "--file", str(readme), "--out", str(collapse_out)]) == 0
    assert (
        main(
            [
                "compile-intent",
                "--file",
                str(readme),
                "--out",
                str(product_out),
                "--certification-runs",
                "2",
            ]
        )
        == 0
    )
    assert requirements_out.exists()
    assert collapse_out.exists()
    assert (product_out / "certification_report.json").exists()
