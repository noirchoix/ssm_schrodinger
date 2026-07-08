from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field, field_validator

AgentMode = Literal["offline", "online"]
GenerationProviderName = Literal["openai", "deepseek", "gemini", "mock"]
EmbeddingProviderName = Literal["gemini", "voyageai", "mock"]

_TRUE_VALUES = {"1", "true", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "no", "n", "off", ""}
_SECRET_NAMES = {
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "VOYAGEAI_API_KEY",
    "SSM_LLM_API_KEY",
    "SSM_OPENAI_API_KEY",
    "SSM_EMBED_API_KEY",
}


class OnlineAgentSettings(BaseModel):
    """Runtime configuration for online agent execution.

    The deterministic compiler does not read these settings. They are used only
    when an explicit online agent command is requested.
    """

    run_online_ai: bool = False
    agent_mode: AgentMode = "offline"
    llm_provider: GenerationProviderName = "mock"
    llm_model: str = "mock"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_temperature: float = 0.0
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_max_output_tokens: int = 3000
    llm_json_mode: bool = True
    agent_audit_log: str | None = "build/agent_audit/online_agent_runs.jsonl"
    agent_log_prompts: bool = False
    embed_provider: EmbeddingProviderName | None = None
    embed_model: str | None = None
    embed_api_key: str | None = None
    embed_base_url: str | None = None

    @field_validator("llm_temperature")
    @classmethod
    def _temperature_range(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("SSM_LLM_TEMPERATURE must be between 0 and 2")
        return value

    @field_validator("llm_timeout_seconds", "llm_max_retries", "llm_max_output_tokens")
    @classmethod
    def _positive_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("integer online-agent settings must be non-negative")
        return value

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> OnlineAgentSettings:
        data = dict(os.environ if env is None else env)
        provider = data.get("SSM_LLM_PROVIDER", "mock").strip().lower() or "mock"
        embed_provider = data.get("SSM_EMBED_PROVIDER", "").strip().lower() or None
        api_key = _first_present(
            data,
            [
                "SSM_LLM_API_KEY",
                _provider_specific_key(provider),
                "SSM_OPENAI_API_KEY" if provider == "openai" else "",
            ],
        )
        embed_api_key = _first_present(
            data,
            [
                "SSM_EMBED_API_KEY",
                "GEMINI_API_KEY" if embed_provider == "gemini" else "",
                "GOOGLE_API_KEY" if embed_provider == "gemini" else "",
                "VOYAGEAI_API_KEY" if embed_provider == "voyageai" else "",
            ],
        )
        return cls(
            run_online_ai=_bool(data.get("RUN_ONLINE_AI", "0")),
            agent_mode=_agent_mode(data.get("SSM_AGENT_MODE", "offline")),
            llm_provider=_generation_provider(provider),
            llm_model=data.get("SSM_LLM_MODEL", "mock").strip() or "mock",
            llm_api_key=api_key,
            llm_base_url=data.get("SSM_LLM_BASE_URL") or None,
            llm_temperature=_float(data.get("SSM_LLM_TEMPERATURE"), 0.0),
            llm_timeout_seconds=_int(data.get("SSM_LLM_TIMEOUT_SECONDS"), 60),
            llm_max_retries=_int(data.get("SSM_LLM_MAX_RETRIES"), 2),
            llm_max_output_tokens=_int(data.get("SSM_LLM_MAX_OUTPUT_TOKENS"), 3000),
            llm_json_mode=_bool(data.get("SSM_LLM_JSON_MODE", "1")),
            agent_audit_log=data.get(
                "SSM_AGENT_AUDIT_LOG", "build/agent_audit/online_agent_runs.jsonl"
            )
            or None,
            agent_log_prompts=_bool(data.get("SSM_AGENT_LOG_PROMPTS", "0")),
            embed_provider=_embedding_provider(embed_provider) if embed_provider else None,
            embed_model=data.get("SSM_EMBED_MODEL") or None,
            embed_api_key=embed_api_key,
            embed_base_url=data.get("SSM_EMBED_BASE_URL") or None,
        )

    def with_overrides(
        self,
        *,
        agent_mode: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        timeout_seconds: int | None = None,
        max_retries: int | None = None,
        max_output_tokens: int | None = None,
    ) -> OnlineAgentSettings:
        values = self.model_dump()
        if agent_mode is not None:
            values["agent_mode"] = _agent_mode(agent_mode)
        if provider is not None:
            values["llm_provider"] = _generation_provider(provider)
        if model is not None:
            values["llm_model"] = model
        if temperature is not None:
            values["llm_temperature"] = temperature
        if timeout_seconds is not None:
            values["llm_timeout_seconds"] = timeout_seconds
        if max_retries is not None:
            values["llm_max_retries"] = max_retries
        if max_output_tokens is not None:
            values["llm_max_output_tokens"] = max_output_tokens
        return OnlineAgentSettings.model_validate(values)

    def redacted(self) -> dict[str, str | int | float | bool | None]:
        payload = self.model_dump()
        for key in ["llm_api_key", "embed_api_key"]:
            if payload.get(key):
                payload[key] = "***redacted***"
        return payload


class SecretRedactor(BaseModel):
    secrets: list[str] = Field(default_factory=list)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> SecretRedactor:
        data = dict(os.environ if env is None else env)
        return cls(secrets=[value for key, value in data.items() if key in _SECRET_NAMES and value])

    def redact(self, text: str) -> str:
        redacted = text
        for secret in self.secrets:
            if secret:
                redacted = redacted.replace(secret, "***redacted***")
        return redacted


def _provider_specific_key(provider: str) -> str:
    return {
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider, "")


def _first_present(data: Mapping[str, str], keys: list[str]) -> str | None:
    for key in keys:
        if key and data.get(key):
            return data[key]
    return None


def _bool(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _float(value: str | None, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _agent_mode(value: str) -> AgentMode:
    normalized = value.strip().lower()
    if normalized not in {"offline", "online"}:
        raise ValueError("agent mode must be 'offline' or 'online'")
    return normalized  # type: ignore[return-value]


def _generation_provider(value: str) -> GenerationProviderName:
    normalized = value.strip().lower()
    aliases = {"google": "gemini", "google-gemini": "gemini", "mock": "mock", "fake": "mock"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"openai", "deepseek", "gemini", "mock"}:
        raise ValueError("SSM_LLM_PROVIDER must be one of: openai, deepseek, gemini, mock")
    return normalized  # type: ignore[return-value]


def _embedding_provider(value: str) -> EmbeddingProviderName:
    normalized = value.strip().lower()
    aliases = {"google": "gemini", "google-gemini": "gemini", "voyage": "voyageai"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"gemini", "voyageai", "mock"}:
        raise ValueError("SSM_EMBED_PROVIDER must be one of: gemini, voyageai, mock")
    return normalized  # type: ignore[return-value]
