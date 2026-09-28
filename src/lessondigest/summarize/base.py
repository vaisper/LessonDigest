from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from lessondigest.config import LlmConfig, Secrets
from lessondigest.errors import LlmError


class LlmOptions(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = "GigaChat-2-Pro"
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout_sec: float = 120.0

    @classmethod
    def from_config(cls, config: LlmConfig) -> "LlmOptions":
        return cls(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_sec=config.timeout_sec,
        )


class LlmResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    model: str = ""
    tokens_in: int | None = None
    tokens_out: int | None = None
    elapsed_sec: float = 0.0


@runtime_checkable
class LlmProvider(Protocol):
    name: str

    def complete(self, prompt: str, options: LlmOptions) -> LlmResult: ...


def build_llm(config: LlmConfig, secrets: Secrets) -> LlmProvider:
    provider = (config.provider or "").strip().lower()
    if provider in {"gigachat", "giga"}:
        from lessondigest.summarize.gigachat import GigaChatLlm

        return GigaChatLlm(config, secrets)
    if provider in {"fake", "stub", "none"}:
        from lessondigest.summarize.fake import FakeLlm

        return FakeLlm()
    raise LlmError(f"Неизвестный LLM provider: {config.provider!r}")
