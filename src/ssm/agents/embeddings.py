from __future__ import annotations

import json
import urllib.parse
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field

from ssm.agents.providers import (
    ProviderAuthError,
    ProviderError,
    ProviderResponseError,
    _HTTPJSONClient,
)
from ssm.agents.settings import OnlineAgentSettings


class EmbeddingResponse(BaseModel):
    vectors: list[list[float]]
    provider: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)


class EmbeddingProvider(Protocol):
    name: str
    model: str

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingResponse: ...


class GeminiEmbeddingProvider:
    name = "gemini"

    def __init__(self, settings: OnlineAgentSettings):
        if not settings.embed_api_key:
            raise ProviderAuthError("Missing API key for Gemini embeddings.")
        self.model = settings.embed_model or "text-embedding-004"
        self.api_key = settings.embed_api_key
        self.base_url = (
            settings.embed_base_url or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self.client = _HTTPJSONClient(settings.llm_timeout_seconds, settings.llm_max_retries)

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingResponse:
        query = urllib.parse.urlencode({"key": self.api_key})
        vectors: list[list[float]] = []
        for text in texts:
            payload = {"model": f"models/{self.model}", "content": {"parts": [{"text": text}]}}
            result = self.client.post_json(
                f"{self.base_url}/models/{self.model}:embedContent?{query}",
                headers={},
                payload=payload,
            )
            embedding = result.payload.get("embedding")
            values = embedding.get("values") if isinstance(embedding, dict) else None
            if not isinstance(values, list) or not all(isinstance(v, int | float) for v in values):
                raise ProviderResponseError("Gemini embedding response is missing numeric values.")
            vectors.append([float(v) for v in values])
        return EmbeddingResponse(vectors=vectors, provider="gemini", model=self.model)


class VoyageAIEmbeddingProvider:
    name = "voyageai"

    def __init__(self, settings: OnlineAgentSettings):
        if not settings.embed_api_key:
            raise ProviderAuthError("Missing API key for VoyageAI embeddings.")
        self.model = settings.embed_model or "voyage-3-large"
        self.api_key = settings.embed_api_key
        self.base_url = (settings.embed_base_url or "https://api.voyageai.com/v1").rstrip("/")
        self.client = _HTTPJSONClient(settings.llm_timeout_seconds, settings.llm_max_retries)

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingResponse:
        result = self.client.post_json(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={"model": self.model, "input": list(texts)},
        )
        data = result.payload.get("data")
        if not isinstance(data, list):
            raise ProviderResponseError("VoyageAI embedding response is missing data.")
        vectors: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list) or not all(
                isinstance(v, int | float) for v in embedding
            ):
                raise ProviderResponseError("VoyageAI embedding item is missing numeric embedding.")
            vectors.append([float(v) for v in embedding])
        usage_payload = result.payload.get("usage")
        usage = (
            {k: v for k, v in usage_payload.items() if isinstance(v, int)}
            if isinstance(usage_payload, dict)
            else {}
        )
        return EmbeddingResponse(
            vectors=vectors, provider="voyageai", model=self.model, usage=usage
        )


class MockEmbeddingProvider:
    name = "mock"
    model = "mock-embedding"

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingResponse:
        vectors = [
            [float((sum(text.encode("utf-8")) + i) % 97) / 97.0 for i in range(8)] for text in texts
        ]
        return EmbeddingResponse(vectors=vectors, provider="mock", model=self.model)


def make_embedding_provider(settings: OnlineAgentSettings) -> EmbeddingProvider:
    if settings.embed_provider == "mock":
        return MockEmbeddingProvider()
    if settings.embed_provider == "gemini":
        return GeminiEmbeddingProvider(settings)
    if settings.embed_provider == "voyageai":
        return VoyageAIEmbeddingProvider(settings)
    raise ProviderError("SSM_EMBED_PROVIDER must be set to gemini, voyageai, or mock.")


def embedding_response_to_json(response: EmbeddingResponse) -> str:
    return json.dumps(response.model_dump(mode="json"), indent=2)
