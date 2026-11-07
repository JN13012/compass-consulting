from types import SimpleNamespace
from typing import Any

import pytest

from app.core.models import Confidentiality
from app.llm.router import (
    ConfidentialityViolationError,
    LlmConfig,
    LlmRouter,
    RoleConfig,
    UnknownRoleError,
)

CONFIG = LlmConfig(
    roles={
        "reasoning": RoleConfig(model="anthropic/claude-opus-5-5", local=False),
        "local": RoleConfig(model="ollama/mistral-small", local=True, api_base="http://ollama:11434"),
    }
)


class FakeCompletion:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="réponse"))],
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=3),
        )


MSG = [{"role": "user", "content": "bonjour"}]


def test_role_selects_configured_model() -> None:
    fake = FakeCompletion()
    result = LlmRouter(CONFIG, fake).complete("reasoning", MSG, Confidentiality.PUBLIC)
    assert fake.calls[0]["model"] == "anthropic/claude-opus-5-5"
    assert result.content == "réponse"
    assert (result.tokens_in, result.tokens_out) == (12, 3)


def test_local_role_passes_api_base() -> None:
    fake = FakeCompletion()
    LlmRouter(CONFIG, fake).complete("local", MSG, Confidentiality.CONFIDENTIAL)
    assert fake.calls[0]["api_base"] == "http://ollama:11434"


def test_confidential_mission_cannot_reach_cloud_model() -> None:
    fake = FakeCompletion()
    with pytest.raises(ConfidentialityViolationError):
        LlmRouter(CONFIG, fake).complete("reasoning", MSG, Confidentiality.CONFIDENTIAL)
    assert fake.calls == [], "no request may leave the machine"


def test_unknown_role_rejected() -> None:
    with pytest.raises(UnknownRoleError):
        LlmRouter(CONFIG, FakeCompletion()).complete("nope", MSG, Confidentiality.PUBLIC)


def test_shipped_config_is_valid() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "config" / "llm.yaml"
    if not path.exists():
        path = Path("/srv/config/llm.yaml")
    cfg = LlmConfig.from_yaml(path)
    assert {"reasoning", "extraction", "local", "embedding"} <= cfg.roles.keys()
    assert cfg.roles["local"].local and cfg.roles["embedding"].local
