from app.corpus.embed import MAX_CHARS, embedding_input
from app.llm.router import LlmRouter

from .fakes import CONFIG


class FakeEmbedding:
    def __call__(self, **kwargs):  # type: ignore[no-untyped-def]
        from types import SimpleNamespace

        self.kwargs = kwargs
        return SimpleNamespace(data=[{"embedding": [0.1, 0.2]} for _ in kwargs["input"]])


def test_embedding_input_includes_heading_and_is_bounded() -> None:
    assert embedding_input("Article 3 - Définitions", "texte") == "Article 3 - Définitions\ntexte"
    assert len(embedding_input("h", "x" * 10_000)) == MAX_CHARS


def test_router_embed_uses_embedding_role() -> None:
    fake = FakeEmbedding()
    vectors = LlmRouter(CONFIG, embedding_fn=fake).embed(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.1, 0.2]]
    assert fake.kwargs["model"] == "fake/embed"
