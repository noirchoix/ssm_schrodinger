from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from ssm.agents.online import OnlineDraftService
from ssm.agents.providers import ChatMessage, MockProvider, ProviderResponse
from ssm.agents.settings import OnlineAgentSettings
from ssm.foundation.builder import OnlineBuildService
from ssm.pipeline import SSMCompiler
from ssm.product.compiler import SchrodingerProductCompiler
from ssm.product.semantic_context import (
    SemanticConformanceVerifier,
    canonical_context_prompt,
)

TODO_INTENT = "Build a todo API with CRUD."
HR_INTENT = (
    "Build a multi-tenant HR leave approval API with PostgreSQL, JWT auth, Employee and "
    "LeaveRequest CRUD, manager approval workflow, and audit logging."
)


class RecordingMockProvider:
    name = "mock-recording"
    model = "mock-recording"

    def __init__(self) -> None:
        self.messages: list[ChatMessage] = []
        self.delegate = MockProvider()

    def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        self.messages = list(messages)
        response = self.delegate.generate(messages)
        return response.model_copy(update={"provider": self.name, "model": self.model})


def _online_settings() -> OnlineAgentSettings:
    return OnlineAgentSettings(
        run_online_ai=True,
        agent_mode="online",
        llm_provider="mock",
        llm_model="mock",
        llm_max_retries=0,
        agent_audit_log=None,
    )


def test_canonical_semantic_context_is_deterministic_and_source_addressed() -> None:
    compiler = SchrodingerProductCompiler()
    first = compiler.prepare_semantic_context(HR_INTENT, source_name="input.md")
    second = compiler.prepare_semantic_context(HR_INTENT, source_name="input.md")

    assert first.semantic_fingerprint == second.semantic_fingerprint
    assert first.source_sha256 == second.source_sha256
    assert first.foundation.tenant_enabled is True
    assert first.foundation.audit_enabled is True
    assert first.negotiation.status in {"SUPPORTED", "SUPPORTED_WITH_ASSUMPTIONS"}
    assert first.context_issues == []


def test_offline_renderer_passes_the_same_semantic_conformance_gate() -> None:
    collapse = SchrodingerProductCompiler().collapse_text(HR_INTENT, source_name="input.md")

    assert collapse.semantic_conformance.status == "PASS"
    assert collapse.semantic_conformance.context_fingerprint == (
        collapse.canonical_context.semantic_fingerprint
    )
    assert collapse.semantic_conformance.checks > 0


def test_semantic_conformance_rejects_candidate_that_drops_canonical_semantics() -> None:
    compiler = SchrodingerProductCompiler()
    context = compiler.prepare_semantic_context(TODO_INTENT, source_name="input.md")
    invalid = """#Project
name: Bad Todo

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
"""

    report = SemanticConformanceVerifier().verify(context, invalid)

    assert report.status == "FAIL"
    codes = {item.code for item in report.diagnostics}
    assert "SCV030" in codes
    assert "SCV080" in codes


def test_semantic_conformance_rejects_tenant_drift() -> None:
    compiler = SchrodingerProductCompiler()
    collapse = compiler.collapse_text(HR_INTENT, source_name="input.md")
    candidate = collapse.sml_text.replace("#Tenant\nenabled: true", "#Tenant\nenabled: false")

    report = SemanticConformanceVerifier().verify(collapse.canonical_context, candidate)

    assert report.status == "FAIL"
    assert any(item.code == "SCV010" for item in report.diagnostics)


def test_direct_online_draft_is_conditioned_on_canonical_context_not_raw_request() -> None:
    provider = RecordingMockProvider()
    service = OnlineDraftService(_online_settings(), provider=provider)
    raw = "Build a todo API with CRUD and keep this literal marker ZEBRA-RAW-INTENT-991."

    draft = service.draft(raw)

    assert draft.text.startswith("#Project")
    user_message = "\n".join(item.content for item in provider.messages if item.role == "user")
    assert "CANONICAL SEMANTIC CONTEXT:" in user_message
    assert "USER REQUEST:" not in user_message
    assert "ZEBRA-RAW-INTENT-991" not in user_message


def test_online_build_persists_canonical_front_end_and_conformance_evidence(tmp_path: Path) -> None:
    result = OnlineBuildService(_online_settings()).build(
        prompt=HR_INTENT,
        out_dir=tmp_path,
        repair_attempts=1,
    )

    assert result.status == "ACCEPTED"
    assert result.semantic_conformance_status == "PASS"
    assert (tmp_path / "input.md").read_text(encoding="utf-8") == HR_INTENT
    assert (tmp_path / "requirements_ir.json").exists()
    assert (tmp_path / "foundation_plan.json").exists()
    assert (tmp_path / "architecture_plan.json").exists()
    assert (tmp_path / "capability_composition.json").exists()
    assert (tmp_path / "capability_negotiation.json").exists()
    assert (tmp_path / "canonical_semantic_context.json").exists()
    assert (tmp_path / "semantic_conformance.json").exists()
    assert (tmp_path / "sir.json").exists()
    assert (tmp_path / "generated_app" / "app" / "main.py").exists()

    run = json.loads((tmp_path / "generation_run.json").read_text(encoding="utf-8"))
    assert run["stage_fingerprints"]["requirements"]
    assert run["stage_fingerprints"]["canonical_semantic_context"]
    assert run["stage_fingerprints"]["semantic_conformance"]
    assert run["stage_fingerprints"]["sir"]
    assert run["metrics"]["semantic_conformance_pass"]["value"] is True


def test_online_build_rejects_contradictory_context_before_provider_invocation(
    tmp_path: Path, monkeypatch
) -> None:
    class ExplodingDraftService:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("provider path must not be constructed for a blocked context")

    monkeypatch.setattr("ssm.foundation.builder.OnlineDraftService", ExplodingDraftService)
    result = OnlineBuildService(_online_settings()).build(
        prompt="Build a todo API using both PostgreSQL and InMemory storage with CRUD.",
        out_dir=tmp_path,
        repair_attempts=1,
    )

    assert result.status == "REJECTED"
    assert result.attempts == 0
    trace = json.loads((tmp_path / "repair_trace.json").read_text(encoding="utf-8"))
    assert trace["events"][0]["stage"] == "canonical_semantic_context"
    assert trace["events"][0]["status"] == "rejected"
    assert "Contradiction" in trace["events"][0]["message"]


def test_online_build_cli_file_input_is_persisted_as_exact_input_document(
    tmp_path: Path, monkeypatch
) -> None:
    from ssm.cli.main import main

    monkeypatch.setenv("RUN_ONLINE_AI", "1")
    monkeypatch.setenv("SSM_AGENT_MODE", "online")
    monkeypatch.setenv("SSM_LLM_PROVIDER", "mock")
    monkeypatch.setenv("SSM_LLM_MODEL", "mock")

    source = tmp_path / "case-input.md"
    source.write_text(HR_INTENT, encoding="utf-8")
    out = tmp_path / "build"

    status = main(
        [
            "online-build",
            "--agent-mode",
            "online",
            "--provider",
            "mock",
            "--file",
            str(source),
            "--out",
            str(out),
        ]
    )

    assert status == 0
    assert (out / "input.md").read_bytes() == source.read_bytes()
    assert (out / "canonical_semantic_context.json").exists()
    assert (out / "semantic_conformance.json").exists()
    result = json.loads((out / "canonical_semantic_context.json").read_text(encoding="utf-8"))
    assert result["source_sha256"]


def test_inventory_intent_with_docker_support_keeps_product_domain_entity() -> None:
    context = SchrodingerProductCompiler().prepare_semantic_context(
        "Build a FastAPI inventory API with PostgreSQL, JWT auth, CRUD, and Docker support.",
        source_name="input.md",
    )

    entity_names = {item.name for item in context.foundation.entities}
    assert "Product" in entity_names
    assert "Ticket" not in entity_names
    assert context.context_issues == []


def test_direct_online_draft_context_fails_closed_before_provider_when_context_is_blocked() -> None:
    from ssm.agents.online import OnlineDraftValidationError

    class ExplodingProvider:
        name = "must-not-run"
        model = "must-not-run"

        def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
            raise AssertionError("blocked canonical context reached provider")

    context = SchrodingerProductCompiler().prepare_semantic_context(
        "Build a todo API using both PostgreSQL and InMemory storage with CRUD.",
        source_name="input.md",
    )
    service = OnlineDraftService(_online_settings(), provider=ExplodingProvider())

    try:
        service.draft_context(context)
    except OnlineDraftValidationError as exc:
        assert "blocked before online synthesis" in str(exc)
        assert "Contradiction" in str(exc)
    else:
        raise AssertionError("blocked canonical semantic context was not rejected")


def test_online_canonical_context_identity_is_independent_of_output_directory(
    tmp_path: Path,
) -> None:
    first = OnlineBuildService(_online_settings()).build(
        prompt=HR_INTENT,
        out_dir=tmp_path / "run-a",
        repair_attempts=1,
    )
    second = OnlineBuildService(_online_settings()).build(
        prompt=HR_INTENT,
        out_dir=tmp_path / "nested" / "run-b",
        repair_attempts=1,
    )

    assert first.status == "ACCEPTED"
    assert second.status == "ACCEPTED"
    assert first.canonical_context_sha256 == second.canonical_context_sha256
    first_context = json.loads(
        (tmp_path / "run-a" / "canonical_semantic_context.json").read_text(encoding="utf-8")
    )
    second_context = json.loads(
        (tmp_path / "nested" / "run-b" / "canonical_semantic_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert first_context["source_name"] == "input.md"
    assert second_context["source_name"] == "input.md"


def test_semantic_conformance_rejects_noncanonical_model_and_route_invention() -> None:
    compiler = SchrodingerProductCompiler()
    collapse = compiler.collapse_text(TODO_INTENT, source_name="input.md")
    candidate = (
        collapse.sml_text
        + """
#DataModel ShadowAdmin
fields:
  id: uuid primary

#Route ShadowAdminList
method: GET
path: /shadow-admins
auth: required
body: none
returns: ShadowAdmin[]
"""
    )

    report = SemanticConformanceVerifier().verify(collapse.canonical_context, candidate)
    codes = {item.code for item in report.diagnostics}
    assert report.status == "FAIL"
    assert "SCV032" in codes
    assert "SCV084" in codes


def test_semantic_conformance_rejects_architecture_policy_drift() -> None:
    compiler = SchrodingerProductCompiler()
    collapse = compiler.collapse_text(TODO_INTENT, source_name="input.md")
    candidate = collapse.sml_text.replace("broad_catch: forbidden", "broad_catch: allowed").replace(
        "architecture: layered", "architecture: event_driven"
    )

    report = SemanticConformanceVerifier().verify(collapse.canonical_context, candidate)
    codes = {item.code for item in report.diagnostics}
    assert report.status == "FAIL"
    assert "SCV102" in codes
    assert "SCV103" in codes


def test_foundation_planner_never_emits_dangling_workflow_or_relationship_refs() -> None:
    prompts = [
        "Build a procurement platform with Supplier, Requisition and PurchaseOrder CRUD and approval workflow.",
        "Build a multi-tenant asset transfer service with approval workflow for receiving employees.",
        "Build a PostgreSQL document approval workflow with Author, Reviewer and Approver roles.",
    ]
    compiler = SchrodingerProductCompiler()
    for prompt in prompts:
        context = compiler.prepare_semantic_context(prompt, source_name="input.md")
        assert context.context_issues == []


def test_frozen_ssm_bench_v1_all_cases_cross_the_canonical_boundary_and_compile() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = sorted((root / "benchmarks" / "ssm_bench_v1" / "intents").glob("*.md"))
    assert len(cases) == 30

    product = SchrodingerProductCompiler()
    compiler = SSMCompiler()
    for case in cases:
        collapse = product.collapse_file(case)
        assert collapse.canonical_context.context_issues == [], case.name
        assert collapse.semantic_conformance.status == "PASS", case.name
        compiled = compiler.compile_text(collapse.sml_text, source_file=f"{case}::project.sml.md")
        assert compiled.success is True, case.name


def test_canonical_online_prompt_emits_exact_representation_envelope() -> None:
    context = SchrodingerProductCompiler().prepare_semantic_context(
        HR_INTENT, source_name="input.md"
    )

    prompt = canonical_context_prompt(context)

    for capability in context.foundation.domain_pack_candidates:
        assert f"#Capability {capability}\nstatus: requested" in prompt
    assert "#Policy ErrorHandling\nbroad_catch: forbidden" in prompt
    assert "#Constraint Architecture\narchitecture: layered" in prompt
    assert "Do not replace `architecture:` with `pattern:`" in prompt


def test_semantic_conformance_accepts_equivalent_architecture_pattern_alias() -> None:
    collapse = SchrodingerProductCompiler().collapse_text(HR_INTENT, source_name="input.md")
    candidate = collapse.sml_text.replace(
        "#Constraint Architecture\narchitecture: layered",
        "#Constraint Architecture\npattern: layered_modular_monolith",
    )

    report = SemanticConformanceVerifier().verify(collapse.canonical_context, candidate)

    assert report.status == "PASS"


def test_repair_diagnostics_expose_expected_and_actual_values() -> None:
    collapse = SchrodingerProductCompiler().collapse_text(HR_INTENT, source_name="input.md")
    candidate = collapse.sml_text.replace("#Capability hr\nstatus: requested\n", "")

    verifier = SemanticConformanceVerifier()
    report = verifier.verify(collapse.canonical_context, candidate)
    message = verifier.format_diagnostics(report)

    assert report.status == "FAIL"
    assert "SCV020" in message
    assert 'Expected="hr"' in message
    assert "actual=" in message
