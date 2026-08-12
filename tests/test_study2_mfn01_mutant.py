from __future__ import annotations

from unittest.mock import patch

from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.schemas import AppRelationship
from ssm.requirements.extractor import IntentRequirementsCompiler


def _relationship(name: str, source: str, target: str) -> AppRelationship:
    return AppRelationship(
        name=name,
        source=source,
        target=target,
        cardinality="many-to-one",
        required=True,
    )


def test_mfn01_drops_exactly_first_relationship() -> None:
    relationships = [
        _relationship("First", "ChildA", "ParentA"),
        _relationship("Second", "ChildB", "ParentB"),
    ]

    mutated = AppFoundationPlanner._drop_first_relationship(relationships)

    assert [item.name for item in mutated] == ["Second"]
    assert relationships[0].name == "First"


def test_mfn01_single_relationship_becomes_empty() -> None:
    relationships = [_relationship("Only", "Child", "Parent")]

    mutated = AppFoundationPlanner._drop_first_relationship(relationships)

    assert mutated == []


def test_mfn01_empty_relationships_remain_empty() -> None:
    relationships: list[AppRelationship] = []

    mutated = AppFoundationPlanner._drop_first_relationship(relationships)

    assert mutated == []


def test_mfn01_changes_only_relationships_in_foundation_plan() -> None:
    prompt = (
        "Build an HR leave application with employees and leave requests, "
        "approval workflow, CRUD, JWT auth."
    )
    planner = AppFoundationPlanner()

    with patch.object(
        AppFoundationPlanner,
        "_drop_first_relationship",
        side_effect=lambda relationships: relationships,
    ):
        control = planner.plan(prompt)

    mutant = planner.plan(prompt)

    assert len(control.relationships) == 1
    assert mutant.relationships == []
    assert mutant.model_copy(update={"relationships": control.relationships}) == control


def test_mfn01_does_not_change_requirements_ir() -> None:
    prompt = (
        "Build an HR leave application with employees and leave requests, "
        "approval workflow, CRUD, JWT auth."
    )
    compiler = IntentRequirementsCompiler()

    mutant = compiler.compile_text(prompt)

    with patch.object(
        AppFoundationPlanner,
        "_drop_first_relationship",
        side_effect=lambda relationships: relationships,
    ):
        control = compiler.compile_text(prompt)

    assert mutant.semantic_fingerprint == control.semantic_fingerprint
    assert mutant.model_dump(mode="json") == control.model_dump(mode="json")
