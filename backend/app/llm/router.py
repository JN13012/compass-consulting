"""Role-based LLM router.

Business code asks for a *role* (reasoning, extraction, local, embedding), never a model.
Confidentiality is enforced here: a confidential mission can only reach roles flagged `local: true`.
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.core.models import Confidentiality

logger = logging.getLogger("compass.llm")

CompletionFn = Callable[..., Any]


class RoleConfig(BaseModel):
    model: str
    local: bool
    api_base: str | None = None
    api_key: str | None = None  # generic key (AI_API_KEY); provider is given by the model prefix
    params: dict[str, Any] = {}  # provider-specific extras, e.g. {"think": false} for Ollama reasoning models


class LlmConfig(BaseModel):
    roles: dict[str, RoleConfig]

    @classmethod
    def from_yaml(cls, path: Path) -> LlmConfig:
        raw = _ENV_VAR.sub(lambda m: os.environ.get(m.group(1)) or m.group(2) or "", path.read_text("utf-8"))
        return cls.model_validate(yaml.safe_load(raw))


_ENV_VAR = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")  # ${VAR} or ${VAR:-default}


class UnknownRoleError(KeyError):
    pass


class ConfidentialityViolationError(PermissionError):
    """Raised when a confidential mission tries to use a non-local model."""


@dataclass(frozen=True)
class LlmResult:
    content: str
    role: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    duration_s: float


def _default_completion(**kwargs: Any) -> Any:
    import litellm

    return litellm.completion(**kwargs)


def _default_embedding(**kwargs: Any) -> Any:
    import litellm

    return litellm.embedding(**kwargs)


class LlmRouter:
    def __init__(
        self,
        config: LlmConfig,
        completion_fn: CompletionFn | None = None,
        embedding_fn: CompletionFn | None = None,
    ) -> None:
        self._config = config
        self._completion = completion_fn or _default_completion
        self._embedding = embedding_fn or _default_embedding

    def embed(
        self, texts: list[str], confidentiality: Confidentiality = Confidentiality.PUBLIC
    ) -> list[list[float]]:
        cfg = self.resolve("embedding", confidentiality)
        params: dict[str, Any] = {"model": cfg.model, "input": texts}
        if cfg.api_base:
            params["api_base"] = cfg.api_base
        response = self._embedding(**params)
        return [list(item["embedding"]) for item in response.data]

    def resolve(self, role: str, confidentiality: Confidentiality) -> RoleConfig:
        try:
            cfg = self._config.roles[role]
        except KeyError as exc:
            raise UnknownRoleError(role) from exc
        if confidentiality is Confidentiality.CONFIDENTIAL and not cfg.local:
            raise ConfidentialityViolationError(
                f"Role '{role}' uses non-local model '{cfg.model}': forbidden for a confidential mission."
            )
        return cfg

    def complete(
        self,
        role: str,
        messages: list[dict[str, str]],
        confidentiality: Confidentiality,
        mission_id: str | None = None,
        **kwargs: Any,
    ) -> LlmResult:
        cfg = self.resolve(role, confidentiality)
        params: dict[str, Any] = {"model": cfg.model, "messages": messages, **cfg.params, **kwargs}
        if cfg.api_base:
            params["api_base"] = cfg.api_base
        if cfg.api_key:
            params["api_key"] = cfg.api_key

        start = time.perf_counter()
        response = self._completion(**params)
        duration = time.perf_counter() - start

        usage = getattr(response, "usage", None)
        result = LlmResult(
            content=response.choices[0].message.content or "",
            role=role,
            model=cfg.model,
            tokens_in=getattr(usage, "prompt_tokens", 0) or 0,
            tokens_out=getattr(usage, "completion_tokens", 0) or 0,
            cost_usd=self._cost(response),
            duration_s=duration,
        )
        # Persisted as LlmCall rows in a later phase; logged for now.
        logger.info(
            "llm_call mission=%s role=%s model=%s in=%d out=%d cost=%s dur=%.2fs",
            mission_id, role, cfg.model, result.tokens_in, result.tokens_out, result.cost_usd, duration,
        )
        return result

    @staticmethod
    def _cost(response: Any) -> float | None:
        try:
            import litellm

            return float(litellm.completion_cost(completion_response=response))
        except Exception:
            return None
