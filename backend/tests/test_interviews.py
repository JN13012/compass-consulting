import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_engine
from app.core.models import Confidentiality, Mission
from app.interviews.guide import Interview, compile_notes, load_guide, render_blank, sections_for
from app.main import app

GUIDE = Path(__file__).resolve().parents[2] / "config" / "interview_guide.yaml"


def test_guide_loads_with_unique_ids_and_filters_by_focus() -> None:
    guide = load_guide(GUIDE)
    assert [s.key for s in sections_for(guide, [])] == ["commun"]
    assert [s.key for s in sections_for(guide, ["cyber", "ia"])] == ["commun", "ia", "cyber"]


def test_compile_notes_keeps_only_answers_in_client_words() -> None:
    sections = sections_for(load_guide(GUIDE), ["ia"])
    notes = compile_notes(sections, Interview(answers={"C6": "900 commandes par mois", "IA2": "  ", "IA1": "Saisie"},
                                              checked=["Organigramme et interlocuteurs clés"]))
    assert "[Tronc commun]" in notes and "900 commandes par mois" in notes
    assert "Saisie" in notes and "IA2" not in notes
    assert "Éléments consultés : Organigramme" in notes
    assert compile_notes(sections, Interview()) == ""


def test_blank_grid_is_escaped() -> None:
    m = Mission(client="<A&B>", sector="s", context="c", confidentiality=Confidentiality.PUBLIC, focus=[])
    html = render_blank(sections_for(load_guide(GUIDE), []), m)
    assert "&lt;A&amp;B&gt;" in html and "C5." in html and "Ce qu'on cherche" in html


@pytest.fixture
def session() -> Iterator[Session]:
    try:
        s = sessionmaker(bind=get_engine())()
        s.execute(select(1))
    except OperationalError:
        pytest.skip("database unreachable")
    yield s
    s.execute(delete(Mission).where(Mission.client == "Test Interview SA"))
    s.commit()
    s.close()


@pytest.mark.db
def test_api_save_and_send_to_notes(session: Session) -> None:
    client = TestClient(app)
    m = client.post("/missions", json={"client": "Test Interview SA", "sector": "Industrie", "focus": ["cyber"]}).json()
    base = f"/missions/{m['id']}/interview"
    got = client.get(base).json()
    assert [s["key"] for s in got["sections"]] == ["commun", "cyber"]
    assert client.post(f"{base}/notes").status_code == 422
    client.put(base, json={"answers": {"S3": "VPN sans MFA"}, "checked": []})
    mission = session.get(Mission, uuid.UUID(m["id"]))
    assert mission is not None
    mission.diagnostic = {"synthese": "ancien"}
    session.commit()
    out = client.post(f"{base}/notes").json()
    assert "VPN sans MFA" in out["notes"] and out["diagnostic"] is None
    assert client.get(f"{base}/print").status_code == 200
