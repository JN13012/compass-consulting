from collections.abc import Iterator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.db import get_session
from app.main import app


def _session(fail: bool) -> Iterator[MagicMock]:
    session = MagicMock()
    if fail:
        session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("down"))
    yield session


def test_health_ok() -> None:
    app.dependency_overrides[get_session] = lambda: next(_session(fail=False))
    response = TestClient(app).get("/health")
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert {k: body[k] for k in ("status", "database", "version")} == {"status": "ok", "database": "ok",
                                                                    "version": "0.1.0"}
    assert "key" not in body["ai_model"].lower() and body["ai_model"]


def test_health_degraded_when_db_down() -> None:
    app.dependency_overrides[get_session] = lambda: next(_session(fail=True))
    response = TestClient(app).get("/health")
    app.dependency_overrides.clear()
    assert response.json()["database"] == "unreachable"
    assert response.json()["status"] == "degraded"
