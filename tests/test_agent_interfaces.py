from __future__ import annotations

from ssm.agents.intent_agent import IntentAgent
from ssm.agents.repair_agent import RepairAgent
from ssm.agents.sml_agent import SMLGeneratorAgent


def test_offline_agent_facade_produces_sml_not_source_code() -> None:
    requirements = IntentAgent().extract(
        "Build a FastAPI inventory API with PostgreSQL database and JWT auth"
    )
    draft = SMLGeneratorAgent().draft(requirements)
    assert "#Project" in draft.text
    assert "#Stack" in draft.text
    assert "PostgreSQL" in draft.text
    assert "def " not in draft.text
    assert draft.provenance == ["agent:SMLGeneratorAgent"]


def test_repair_agent_emits_semantic_patch() -> None:
    patch = RepairAgent().patch_missing_schema("ProductCreate")
    assert patch.target == "sml"
    assert "#DataModel ProductCreate" in patch.patch
    assert "Compiler diagnostics" in patch.rationale
