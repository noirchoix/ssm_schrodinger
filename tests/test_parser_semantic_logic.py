from __future__ import annotations

from pathlib import Path

import pytest

from ssm.errors import SemanticError
from ssm.logic.engine import LogicEngine
from ssm.logic.rules import builtin_rules
from ssm.models import Fact
from ssm.pipeline import SSMCompiler


def test_todo_compiles_and_is_deterministic() -> None:
    compiler = SSMCompiler()
    text = Path("examples/todo_api/project.sml.md").read_text(encoding="utf-8")
    a = compiler.compile_text(text, "todo.sml.md")
    b = compiler.compile_text(text, "todo.sml.md")
    assert a.success and b.success
    assert [f.path for f in a.files] == [f.path for f in b.files]
    assert [f.content for f in a.files] == [f.content for f in b.files]
    assert a.manifest == b.manifest
    assert any(f.path == "app/main.py" for f in a.files)
    assert any(p.status == "rejected" for p in a.proof_trace)


def test_missing_schema_fails_semantic_validation() -> None:
    compiler = SSMCompiler()
    text = Path("examples/product_missing_schema/project.sml.md").read_text(encoding="utf-8")
    with pytest.raises(SemanticError) as exc:
        compiler.compile_text(text, "missing.sml.md")
    assert "ProductCreate" in str(exc.value)


def test_logic_derives_postgres_env_and_auth_security() -> None:
    compiler = SSMCompiler()
    result = compiler.compile_file("examples/inventory_api/project.sml.md")
    facts = {str(f) for f in result.resolution.facts}
    assert "Requires(EnvVar:DATABASE_URL)" in facts
    assert "Requires(Module:app.core.security)" in facts
    assert "Requires(Dependency:SQLAlchemy)" in facts


def test_broad_exception_candidate_rejected() -> None:
    engine = LogicEngine(builtin_rules())
    ok, proof, closure = engine.check_admissibility(
        [Fact(predicate="Policy", args=("ForbidBroadCatch",))],
        [Fact(predicate="Candidate", args=("BroadCatchException",))],
        "test.broad",
    )
    assert ok is False
    assert proof.status == "rejected"
    assert any(str(f) == "Invalid(Candidate:BroadCatchException)" for f in closure.invalid_facts)


def _runtime_rule_document(rule_section: str) -> str:
    return f"""#Project RuleValidation
name: RuleValidation

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel LeaveRequest
fields:
  id: uuid primary
  requested_days: int required
  start_date: string required
  end_date: string required

{rule_section}
"""


def _semantic_codes(error: SemanticError) -> set[str]:
    return {diagnostic.code for diagnostic in error.diagnostics}


def test_observed_online_runtime_rule_shape_is_rejected_precisely() -> None:
    text = _runtime_rule_document(
        """#BusinessRule LeaveRequestDateValidation
rule: end_date must be after start_date
severity: error"""
    )

    with pytest.raises(SemanticError) as exc:
        SSMCompiler().compile_text(text, "online-rule.sml.md")

    assert {"SEM202", "SEM204", "SEM206"} <= _semantic_codes(exc.value)


def test_runtime_rule_entity_must_reference_an_existing_model() -> None:
    text = _runtime_rule_document(
        """#BusinessRule LeaveRequestDateValidation
entity: MissingModel
rule: end_date > start_date
on_violation: reject"""
    )

    with pytest.raises(SemanticError) as exc:
        SSMCompiler().compile_text(text, "unknown-rule-entity.sml.md")

    assert _semantic_codes(exc.value) == {"SEM203"}


def test_runtime_rule_rejects_unsupported_expression_ast() -> None:
    text = _runtime_rule_document(
        """#Invariant LeaveRequestHasItems
entity: LeaveRequest
rule: len(items) > 0
on_violation: reject"""
    )

    with pytest.raises(SemanticError) as exc:
        SSMCompiler().compile_text(text, "unsupported-rule-expression.sml.md")

    assert _semantic_codes(exc.value) == {"SEM207"}
    assert "Call" in str(exc.value)


def test_runtime_rule_rejects_unsupported_violation_behavior() -> None:
    text = _runtime_rule_document(
        """#BusinessRule LeaveRequestWarning
entity: LeaveRequest
rule: requested_days > 0
on_violation: warn"""
    )

    with pytest.raises(SemanticError) as exc:
        SSMCompiler().compile_text(text, "unsupported-rule-behavior.sml.md")

    assert _semantic_codes(exc.value) == {"SEM205"}


def test_valid_runtime_rule_expression_compiles() -> None:
    text = _runtime_rule_document(
        """#BusinessRule LeaveRequestPositiveDuration
entity: LeaveRequest
rule: requested_days > 0
on_violation: reject"""
    )

    result = SSMCompiler().compile_text(text, "valid-rule.sml.md")

    assert result.success is True
