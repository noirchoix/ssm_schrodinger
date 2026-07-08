from __future__ import annotations

import json
from pathlib import Path

import pytest

from ssm.agents.embeddings import MockEmbeddingProvider
from ssm.agents.online import OnlineDraftService
from ssm.agents.providers import (
    ChatMessage,
    ProviderResponse,
    ProviderResponseError,
    extract_json_object,
)
from ssm.agents.settings import OnlineAgentSettings, SecretRedactor
from ssm.cli.main import main
from ssm.pipeline import SSMCompiler


class SequenceProvider:
    name = "sequence"
    model = "test-sequence"

    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls = 0

    def generate(self, messages: list[ChatMessage]) -> ProviderResponse:
        del messages
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return ProviderResponse(text=response, provider=self.name, model=self.model)


def test_online_draft_cli_with_mock_provider_generates_compilable_sml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "online_inventory" / "project.sml.md"
    monkeypatch.setenv("RUN_ONLINE_AI", "1")
    monkeypatch.setenv("SSM_AGENT_MODE", "online")
    monkeypatch.setenv("SSM_LLM_PROVIDER", "mock")
    monkeypatch.setenv("SSM_LLM_MODEL", "mock")
    monkeypatch.setenv("SSM_AGENT_AUDIT_LOG", str(tmp_path / "audit" / "runs.jsonl"))

    status = main(
        [
            "draft",
            "--agent-mode",
            "online",
            "--prompt",
            "Build a FastAPI inventory API with PostgreSQL, JWT auth, product CRUD, SKU uniqueness, pagination, OpenAPI contract tests, and Docker support.",
            "--out",
            str(out),
        ]
    )

    assert status == 0
    text = out.read_text(encoding="utf-8")
    assert "#DataModel Product" in text
    result = SSMCompiler().compile_text(text)
    assert result.success is True
    audit = tmp_path / "audit" / "runs.jsonl"
    assert audit.exists()
    payload = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])
    assert payload["event"] == "online_draft_success"
    assert "prompt" not in payload


def test_online_draft_retries_after_invalid_sml() -> None:
    invalid = json.dumps(
        {
            "text": "#Project\nname: Bad\n\n#Stack\nbackend: FastAPI\ndatabase: PostgreSQL\nauth: JWT\n\n#Route CreateProduct\nmethod: POST\npath: /products\nauth: required\nbody: ProductCreate\nreturns: Product\n",
            "assumptions": [],
            "unresolved_questions": [],
            "provenance": ["test"],
        }
    )
    valid = json.dumps(
        {
            "text": "#Project\nname: Inventory API\ndescription: test\n\n#Stack\nbackend: FastAPI\ndatabase: PostgreSQL\nauth: JWT\n\n#DataModel Product\nfields:\n  id: uuid primary\n  name: string required max=120\n  sku: string unique required\n  quantity: int default=0\n\n#DataModel ProductCreate\nfields:\n  name: string required max=120\n  sku: string unique required\n  quantity: int default=0\n\n#Route ListProducts\nmethod: GET\npath: /products\nauth: required\nreturns: Product[]\n\n#Route CreateProduct\nmethod: POST\npath: /products\nauth: required\nbody: ProductCreate\nreturns: Product\n\n#Policy ErrorHandling\nbroad_catch: forbidden\n\n#Constraint Architecture\narchitecture: layered\n",
            "assumptions": [],
            "unresolved_questions": [],
            "provenance": ["test"],
        }
    )
    settings = OnlineAgentSettings(
        run_online_ai=True,
        agent_mode="online",
        llm_provider="mock",
        llm_model="mock",
        llm_max_retries=1,
        agent_audit_log=None,
    )
    provider = SequenceProvider([invalid, valid])

    draft = OnlineDraftService(settings, provider=provider).draft("inventory api")

    assert "#DataModel ProductCreate" in draft.text
    assert provider.calls == 2


def test_online_draft_rejects_source_code() -> None:
    provider = SequenceProvider(
        [
            json.dumps(
                {
                    "text": "from fastapi import FastAPI\napp = FastAPI()",
                    "assumptions": [],
                    "unresolved_questions": [],
                    "provenance": ["test"],
                }
            )
        ]
    )
    settings = OnlineAgentSettings(
        run_online_ai=True,
        agent_mode="online",
        llm_provider="mock",
        llm_model="mock",
        llm_max_retries=0,
        agent_audit_log=None,
    )

    with pytest.raises(ProviderResponseError):
        OnlineDraftService(settings, provider=provider).draft("bad")


def test_extract_json_object_handles_fenced_json() -> None:
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_secret_redactor_masks_known_keys() -> None:
    redactor = SecretRedactor.from_env({"OPENAI_API_KEY": "sk-secret"})
    assert redactor.redact("token=sk-secret") == "token=***redacted***"


def test_mock_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()
    first = provider.embed_texts(["abc"])
    second = provider.embed_texts(["abc"])
    assert first.vectors == second.vectors
    assert len(first.vectors[0]) == 8


def test_embed_text_cli_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "embeddings.json"
    monkeypatch.setenv("SSM_EMBED_PROVIDER", "mock")

    status = main(["embed-text", "--provider", "mock", "--text", "hello", "--out", str(out)])

    assert status == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["provider"] == "mock"
