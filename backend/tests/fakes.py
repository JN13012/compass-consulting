import re
from types import SimpleNamespace
from typing import Any

from app.llm.router import LlmConfig, LlmRouter, RoleConfig

CONFIG = LlmConfig(
    roles={
        "reasoning": RoleConfig(model="fake/cloud", local=False),
        "local": RoleConfig(model="fake/local", local=True),
        "embedding": RoleConfig(model="fake/embed", local=True),
    }
)


def response(content: str) -> Any:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


class ScriptedCompletion:
    """Returns scripted outputs in order; '{first}' is replaced by the first passage ref in the prompt."""

    def __init__(self, *outputs: str) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        user = kwargs["messages"][-1]["content"]
        first = re.search(r"^\[([A-Z0-9-]+)\]", user, re.M)
        out = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        return response(out.replace("{first}", first.group(1) if first else ""))


def fake_router(*outputs: str) -> tuple[LlmRouter, ScriptedCompletion]:
    completion = ScriptedCompletion(*outputs)
    return LlmRouter(CONFIG, completion_fn=completion), completion
