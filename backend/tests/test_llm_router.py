from pathlib import Path
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


def test_role_params_are_forwarded() -> None:
    fake = FakeCompletion()
    cfg = LlmConfig(roles={"local": RoleConfig(model="ollama_chat/m", local=True, params={"think": False})})
    LlmRouter(cfg, fake).complete("local", MSG, Confidentiality.PUBLIC, temperature=0)
    assert fake.calls[0]["think"] is False and fake.calls[0]["temperature"] == 0


def test_generic_api_key_is_forwarded_only_when_set() -> None:
    fake = FakeCompletion()
    cfg = LlmConfig(roles={
        "reasoning": RoleConfig(model="openai/gpt-x", local=False, api_key="sk-test"),
        "local": RoleConfig(model="ollama_chat/m", local=True, api_key=""),
    })
    router = LlmRouter(cfg, fake)
    router.complete("reasoning", MSG, Confidentiality.PUBLIC)
    router.complete("local", MSG, Confidentiality.PUBLIC)
    assert fake.calls[0]["api_key"] == "sk-test"
    assert "api_key" not in fake.calls[1]


def test_env_vars_in_config(tmp_path: "Path", monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "llm.yaml"
    path.write_text("roles:\n  local:\n    model: ${M:-ollama/default}\n    local: true\n    api_base: ${URL}\n")
    monkeypatch.setenv("URL", "http://h:1")
    monkeypatch.delenv("M", raising=False)
    cfg = LlmConfig.from_yaml(path)
    assert cfg.roles["local"].model == "ollama/default" and cfg.roles["local"].api_base == "http://h:1"


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
