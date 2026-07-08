from __future__ import annotations

import json
from pathlib import Path

from ssm.cli.main import main
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.renderer import FoundationSMLRenderer
from ssm.pipeline import SSMCompiler


def test_hr_leave_prompt_maps_to_domain_foundation_and_compiles() -> None:
    prompt = (
        "Build an HR leave approval SaaS with employees, leave requests, "
        "manager approval, leave balance rules, tenant isolation, audit logs, and CRUD."
    )
    plan = AppFoundationPlanner().plan(prompt)

    assert "hr" in plan.domain_pack_candidates
    assert any(entity.name == "LeaveRequest" for entity in plan.entities)
    assert plan.workflows
    assert plan.tenant_enabled is True
    assert plan.audit_enabled is True

    negotiation = CapabilityNegotiator().negotiate_plan(plan)
    assert negotiation.status == "SUPPORTED_WITH_ASSUMPTIONS"
    assert "workflow-foundation" in negotiation.supported_features

    sml = FoundationSMLRenderer().render(plan)
    assert "#Workflow LeaveRequestApproval" in sml
    assert "#Tenant" in sml
    result = SSMCompiler().compile_text(sml, source_file="hr_leave.sml.md")
    assert result.success is True
    facts = {str(fact) for fact in result.resolution.facts} if result.resolution else set()
    assert "SaaSPrimitive(TenantIsolation)" in facts
    assert "Workflow(LeaveRequestApproval)" in facts


def test_capability_negotiator_rejects_unsupported_integration() -> None:
    sml = """#Project
name: Payments Test

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#DataModel Invoice
fields:
  id: uuid primary
  amount: float required

#DataModel InvoiceCreate
fields:
  amount: float required

#Integration payment
provider: stripe

#Route CreateInvoice
method: POST
path: /invoices
auth: required
body: InvoiceCreate
returns: Invoice

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
"""
    result = CapabilityNegotiator().negotiate_sml_text(sml)

    assert result.status == "UNSUPPORTED"
    assert any(issue.code == "CAP_UNSUPPORTED_INTEGRATION" for issue in result.issues)


def test_plan_cli_can_emit_sml_and_negotiate_cli_accepts_it(tmp_path: Path) -> None:
    out = tmp_path / "project.sml.md"
    status = main(
        [
            "plan",
            "--emit-sml",
            "--prompt",
            "Build a ticketing helpdesk SaaS with ticket assignment workflow and audit logs.",
            "--out",
            str(out),
        ]
    )
    assert status == 0
    assert "#Workflow TicketLifecycle" in out.read_text(encoding="utf-8")

    status = main(["negotiate", "--file", str(out)])
    assert status == 0


def test_online_build_mock_creates_foundation_and_generated_app(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("RUN_ONLINE_AI", "1")
    monkeypatch.setenv("SSM_AGENT_MODE", "online")
    monkeypatch.setenv("SSM_LLM_PROVIDER", "mock")
    monkeypatch.setenv("SSM_LLM_MODEL", "mock")
    monkeypatch.setenv("SSM_AGENT_AUDIT_LOG", str(tmp_path / "audit" / "runs.jsonl"))
    out = tmp_path / "build"

    status = main(
        [
            "online-build",
            "--agent-mode",
            "online",
            "--provider",
            "mock",
            "--prompt",
            "Build a FastAPI inventory API with PostgreSQL, JWT auth, and CRUD.",
            "--out",
            str(out),
        ]
    )

    assert status == 0
    assert (out / "foundation" / "project.sml.md").exists()
    assert (out / "generated_app" / "app" / "main.py").exists()
    audit_payload = json.loads((tmp_path / "audit" / "runs.jsonl").read_text().splitlines()[0])
    assert audit_payload["event"] == "online_draft_success"
