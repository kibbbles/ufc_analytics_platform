"""
The chat assistant runs SQL written by a model from user text. These tests hand
the endpoint hostile SQL as if the model had written it - no Groq call - and
check it runs read-only and time-boxed against the real database.

Every write probe is WHERE false and the session never commits, so even with
the guard gone these tests cannot change data - they fail instead.

Run from backend/:
    pytest tests/test_chat_sql_guard.py -v
"""

import os
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.v1.endpoints import chat as chat_module  # noqa: E402
from api.v1.endpoints.chat import ChatRequest  # noqa: E402
from db.database import SessionLocal, engine  # noqa: E402


def _model_writes(sql):
    """A stand-in client whose first completion is the given SQL."""
    def complete(client, messages, temperature, budget):
        content = sql if len(complete.calls) == 0 else "answer"
        complete.calls.append(messages)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    complete.calls = []
    return complete


@pytest.fixture
def ask(monkeypatch):
    monkeypatch.setattr(chat_module, "_get_groq_client", lambda: object())

    def run(sql):
        monkeypatch.setattr(chat_module, "_complete", _model_writes(sql))
        db = SessionLocal()
        try:
            return chat_module.chat(ChatRequest(question="anything"), db)
        finally:
            db.close()
    return run


def _fight_results_count():
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM fight_results")).scalar()


# Writes wrapped in a SELECT, so they return rows. A bare DELETE errors on
# reading its (absent) result rows whether or not the guard is there, which
# made an earlier version of this test pass with the guard removed. WHERE false
# keeps these harmless even then.
@pytest.mark.parametrize("sql", [
    "WITH d AS (DELETE FROM fight_results WHERE false RETURNING 1) SELECT COUNT(*) FROM d",
    "WITH u AS (UPDATE fight_results SET \"METHOD\" = \"METHOD\" WHERE false RETURNING 1) "
    "SELECT COUNT(*) FROM u",
])
def test_model_written_writes_are_refused(ask, sql):
    before = _fight_results_count()

    resp = ask(sql)

    assert resp.status == "error"
    assert _fight_results_count() == before


def test_slow_model_written_query_is_cut_off(ask):
    resp = ask("SELECT pg_sleep(7)")

    assert resp.status == "error"


def test_ordinary_select_still_answers(ask):
    resp = ask("SELECT COUNT(*) AS fights FROM fight_results")

    assert resp.status == "ok"


def test_prose_instead_of_sql_never_reaches_the_database(ask):
    # gpt-oss-120b once answered a record question with a sentence.
    resp = ask("I'm sorry, but I can't find that fighter.")

    assert resp.status == "error"
    assert resp.sql is None
