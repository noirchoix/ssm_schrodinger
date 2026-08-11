from __future__ import annotations

from ssm.requirements import IntentRequirementsCompiler


def _explicit_business_rules(text: str) -> list[str]:
    requirements = IntentRequirementsCompiler().compile_text(text, source_name="M-RQ-01.md")
    return [
        item.description
        for item in requirements.requirements
        if item.kind == "business_rule" and item.origin == "explicit"
    ]


def test_mrq01_drops_exactly_first_explicit_business_rule() -> None:
    text = """# Mutation Probe

## Business Rules
- Quantity must be greater than zero.
- Closed records must remain immutable.
"""

    assert _explicit_business_rules(text) == ["Closed records must remain immutable."]


def test_mrq01_drops_single_explicit_business_rule() -> None:
    text = """# Mutation Probe

## Business Rules
- Quantity must be greater than zero.
"""

    assert _explicit_business_rules(text) == []


def test_mrq01_leaves_non_business_rule_requirements_present() -> None:
    text = """# Mutation Probe

## Entities
- Widget

## Features
- CRUD for widgets
"""
    requirements = IntentRequirementsCompiler().compile_text(text, source_name="M-RQ-01.md")

    assert any(
        item.kind == "entity" and item.name == "Widget" for item in requirements.requirements
    )
    assert any(item.kind == "capability" for item in requirements.requirements)
    assert not any(item.kind == "business_rule" for item in requirements.requirements)
