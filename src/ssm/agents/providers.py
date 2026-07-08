from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from ssm.agents.settings import OnlineAgentSettings


class ChatMessage(BaseModel):
    role: str
    content: str


class ProviderUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ProviderResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse: ...


class ProviderError(RuntimeError):
    pass


class ProviderAuthError(ProviderError):
    pass


class ProviderRetryableError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


@dataclass(frozen=True)
class _HTTPResult:
    status: int
    payload: dict[str, Any]


class _HTTPJSONClient:
    def __init__(self, timeout_seconds: int, max_retries: int):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> _HTTPResult:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        _validate_https_url(url)
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", **headers},
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                    response_body = response.read().decode("utf-8")
                    parsed = json.loads(response_body) if response_body else {}
                    if not isinstance(parsed, dict):
                        raise ProviderResponseError("Provider returned non-object JSON payload.")
                    return _HTTPResult(status=response.status, payload=parsed)
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                if exc.code in {401, 403}:
                    raise ProviderAuthError(
                        f"Provider authentication failed with HTTP {exc.code}."
                    ) from exc
                if exc.code in {408, 409, 425, 429, 500, 502, 503, 504}:
                    last_error = ProviderRetryableError(
                        f"Provider retryable HTTP {exc.code}: {error_body[:500]}"
                    )
                else:
                    raise ProviderError(f"Provider HTTP {exc.code}: {error_body[:500]}") from exc
            except (TimeoutError, urllib.error.URLError) as exc:
                last_error = ProviderRetryableError(f"Provider request failed: {exc}")
            except json.JSONDecodeError as exc:
                raise ProviderResponseError("Provider returned invalid JSON.") from exc
            if attempt < self.max_retries:
                time.sleep(min(2.0, 0.25 * (2**attempt)))
        if last_error is not None:
            raise last_error
        raise ProviderRetryableError("Provider request failed without a response.")


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, settings: OnlineAgentSettings, *, provider_name: str, base_url: str):
        if settings.llm_provider != "mock" and not settings.llm_api_key:
            raise ProviderAuthError(f"Missing API key for provider '{provider_name}'.")
        self.provider_name = provider_name
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key or ""
        self.base_url = (settings.llm_base_url or base_url).rstrip("/")
        self.temperature = settings.llm_temperature
        self.max_output_tokens = settings.llm_max_output_tokens
        self.json_mode = settings.llm_json_mode
        self.client = _HTTPJSONClient(settings.llm_timeout_seconds, settings.llm_max_retries)

    def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [message.model_dump() for message in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        result = self.client.post_json(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload=payload,
        )
        choices = result.payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("Provider response is missing choices.")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("Provider response is missing message content.")
        usage_payload = result.payload.get("usage") or {}
        usage = ProviderUsage(
            input_tokens=_optional_int(usage_payload.get("prompt_tokens")),
            output_tokens=_optional_int(usage_payload.get("completion_tokens")),
            total_tokens=_optional_int(usage_payload.get("total_tokens")),
        )
        return ProviderResponse(
            text=content,
            provider=self.provider_name,
            model=self.model,
            usage=usage,
            raw={"status": result.status},
        )


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: OnlineAgentSettings):
        if not settings.llm_api_key:
            raise ProviderAuthError("Missing API key for provider 'gemini'.")
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.base_url = (
            settings.llm_base_url or "https://generativelanguage.googleapis.com/v1beta"
        ).rstrip("/")
        self.temperature = settings.llm_temperature
        self.max_output_tokens = settings.llm_max_output_tokens
        self.client = _HTTPJSONClient(settings.llm_timeout_seconds, settings.llm_max_retries)

    def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        system_text = "\n\n".join(m.content for m in messages if m.role == "system")
        user_text = "\n\n".join(m.content for m in messages if m.role != "system")
        query = urllib.parse.urlencode({"key": self.api_key})
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        result = self.client.post_json(
            f"{self.base_url}/models/{self.model}:generateContent?{query}",
            headers={},
            payload=payload,
        )
        candidates = result.payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProviderResponseError("Gemini response is missing candidates.")
        content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise ProviderResponseError("Gemini response is missing content parts.")
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise ProviderResponseError("Gemini response is missing text content.")
        usage_payload = result.payload.get("usageMetadata") or {}
        usage = ProviderUsage(
            input_tokens=_optional_int(usage_payload.get("promptTokenCount")),
            output_tokens=_optional_int(usage_payload.get("candidatesTokenCount")),
            total_tokens=_optional_int(usage_payload.get("totalTokenCount")),
        )
        return ProviderResponse(
            text=text,
            provider="gemini",
            model=self.model,
            usage=usage,
            raw={"status": result.status},
        )


class MockProvider:
    name = "mock"
    model = "mock"

    def generate(self, messages: Sequence[ChatMessage]) -> ProviderResponse:
        prompt = "\n".join(message.content for message in messages if message.role == "user")
        text = _mock_sml_for_prompt(prompt)
        return ProviderResponse(
            text=json.dumps(
                {
                    "text": text,
                    "assumptions": [
                        "mock provider generated deterministic SML for offline online-mode tests"
                    ],
                    "unresolved_questions": [],
                    "provenance": ["provider:mock"],
                }
            ),
            provider="mock",
            model="mock",
        )


def make_generation_provider(settings: OnlineAgentSettings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockProvider()
    if settings.llm_provider == "openai":
        return OpenAICompatibleProvider(
            settings, provider_name="openai", base_url="https://api.openai.com/v1"
        )
    if settings.llm_provider == "deepseek":
        return OpenAICompatibleProvider(
            settings, provider_name="deepseek", base_url="https://api.deepseek.com/v1"
        )
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    raise ProviderError(f"Unsupported generation provider: {settings.llm_provider}")


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = [line for line in stripped.splitlines() if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProviderResponseError("Model response did not contain a JSON object.")
    try:
        parsed = json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("Model response JSON could not be parsed.") from exc
    if not isinstance(parsed, dict):
        raise ProviderResponseError("Model response JSON must be an object.")
    return parsed


def _validate_https_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ProviderError("Provider URL must be an absolute HTTPS URL.")


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _mock_sml_for_prompt(prompt: str) -> str:
    lower = prompt.lower()
    is_todo = "todo" in lower and "inventory" not in lower and "product" not in lower
    if is_todo:
        return """#Project
name: Todo API
description: Online drafted Todo API with JWT authentication.

#Stack
backend: FastAPI
database: InMemory
auth: JWT

#DataModel Todo
fields:
  id: uuid primary
  title: string required max=120
  completed: bool default=false

#DataModel TodoCreate
fields:
  title: string required max=120
  completed: bool default=false

#Route ListTodos
method: GET
path: /todos
auth: required
returns: Todo[]

#Route CreateTodo
method: POST
path: /todos
auth: required
body: TodoCreate
returns: Todo

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
"""
    return """#Project
name: Inventory API
description: Online drafted inventory backend with PostgreSQL, JWT, SKU uniqueness, pagination, OpenAPI contract tests, and Docker support.

#Stack
backend: FastAPI
database: PostgreSQL
auth: JWT

#DataModel Product
fields:
  id: uuid primary
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#DataModel ProductCreate
fields:
  name: string required max=120
  sku: string unique required
  quantity: int default=0

#Route ListProducts
method: GET
path: /products
auth: required
returns: Product[]

#Route CreateProduct
method: POST
path: /products
auth: required
body: ProductCreate
returns: Product

#Policy ErrorHandling
broad_catch: forbidden

#Constraint Architecture
architecture: layered
"""


def assert_no_source_code(text: str) -> None:
    suspicious = [
        "from fastapi import",
        "import sqlalchemy",
        "def ",
        "class ",
        "```python",
        "uvicorn.run",
    ]
    lowered = text.lower()
    matched = [pattern for pattern in suspicious if pattern in lowered]
    if matched:
        raise ProviderResponseError(
            "Model attempted to emit source code instead of SML: " + ", ".join(matched)
        )


def messages_to_text(messages: Iterable[ChatMessage]) -> str:
    return "\n\n".join(f"[{message.role}]\n{message.content}" for message in messages)
