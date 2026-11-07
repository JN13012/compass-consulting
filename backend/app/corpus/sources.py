from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Source(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9]+$")
    celex: str = Field(pattern=r"^3\d{4}[A-Z]\d{4}$")
    short: str
    title: str
    domain: str


class SourceList(BaseModel):
    sources: list[Source]


def load_sources(path: Path) -> list[Source]:
    data = SourceList.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    codes = [s.code for s in data.sources]
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate source codes in sources.yaml")
    return data.sources
