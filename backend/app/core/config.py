from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://compass:compass@db:5432/compass"
    llm_config_path: Path = Path("/srv/config/llm.yaml")
    corpus_dir: Path = Path("/srv/corpus")
    # Role used by the knowledge base ("reasoning" = cloud model, "local" = Ollama).
    kb_role: str = "reasoning"
    kb_min_score: float = 0.30
    kb_min_similarity: float = 0.45  # frozen on the dev set (config/eval_frozen.yaml)
    poc_examples_dir: Path = Path("/srv/poc_examples")
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
