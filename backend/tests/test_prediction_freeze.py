"""
Prediction freeze and scoring exclusions (migration 011), checked against the live database.

The trigger tests write throwaway rows inside a transaction that is always
rolled back, so nothing they create is ever committed.

Run from backend/:
    pytest tests/test_prediction_freeze.py -v
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

ENDPOINTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api", "v1", "endpoints")


@pytest.fixture
def tx():
    """A connection whose every change is rolled back when the test ends."""
    with engine.connect() as c:
        trans = c.begin()
        try:
            yield c
        finally:
            trans.rollback()


def _card(conn, section_start, event_date):
    """Insert a one-bout card and return the fight id."""
    conn.execute(text("""
        INSERT INTO upcoming_events (id, event_name, date_proper, ufcstats_url)
        VALUES ('ZZTST1', 'Freeze test event', :d, 'test://freeze-event')
    """), {"d": event_date})
    conn.execute(text("""
        INSERT INTO upcoming_fights (id, event_id, fighter_a_name, fighter_b_name,
                                     fighter_a_url, fighter_b_url, section_start_at, odds_a, odds_b)
        VALUES ('ZZTST2', 'ZZTST1', 'Test A', 'Test B', 'test://a', 'test://b', :s, -150, 130)
    """), {"s": section_start})
    return "ZZTST2"


def _predict(conn, fight_id):
    conn.execute(text("""
        INSERT INTO upcoming_predictions (id, fight_id, model_version, win_prob_a, win_prob_b)
        VALUES ('ZZTST3', :f, 'test', 0.6, 0.4)
    """), {"f": fight_id})


def _now():
    return datetime.now(timezone.utc)


def test_prediction_is_accepted_before_the_section_starts(tx):
    fight = _card(tx, _now() + timedelta(hours=2), _now().date() + timedelta(days=1))
    _predict(tx, fight)


def test_prediction_is_refused_once_the_section_has_started(tx):
    fight = _card(tx, _now() - timedelta(minutes=1), _now().date())
    with pytest.raises(DBAPIError, match="frozen"):
        _predict(tx, fight)


def test_unknown_section_start_freezes_at_noon_utc_the_day_before(tx):
    # No start time and the event is tomorrow: the fallback freeze (12:00 UTC
    # today) may or may not have passed, so compare against it directly.
    event_day = _now().date() + timedelta(days=1)
    fight = _card(tx, None, event_day)
    fallback = datetime.combine(event_day, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=12)
    if _now() >= fallback:
        with pytest.raises(DBAPIError, match="frozen"):
            _predict(tx, fight)
    else:
        _predict(tx, fight)


def test_odds_change_is_refused_once_the_section_has_started(tx):
    fight = _card(tx, _now() - timedelta(minutes=1), _now().date())
    with pytest.raises(DBAPIError, match="frozen"):
        tx.execute(text("UPDATE upcoming_fights SET odds_a = 179, odds_b = -212 WHERE id = :f"), {"f": fight})


def test_other_updates_to_a_started_fight_still_work(tx):
    # The archive marks started fights archived; only odds are frozen.
    fight = _card(tx, _now() - timedelta(minutes=1), _now().date())
    tx.execute(text("UPDATE upcoming_fights SET archived = TRUE WHERE id = :f"), {"f": fight})


def test_scored_predictions_drops_only_the_flagged_rows():
    with engine.connect() as c:
        total, flagged = c.execute(text(
            "SELECT COUNT(*), COUNT(*) FILTER (WHERE prediction_after_start) FROM past_predictions")).one()
        scored = c.execute(text("SELECT COUNT(*) FROM scored_predictions")).scalar()
    assert scored == total - flagged


def test_scored_predictions_shows_odds_only_when_captured_before_the_start():
    with engine.connect() as c:
        leaked = c.execute(text("""
            SELECT COUNT(*)
            FROM scored_predictions s
            JOIN past_predictions p ON p.id = s.id
            WHERE s.odds_a IS NOT NULL AND p.odds_after_start IS NOT FALSE
        """)).scalar()
    assert leaked == 0


# The one deliberate exception: the past event page lists fights whose late
# prediction is excluded, so it must read them from the table. It nulls every
# prediction field on those rows (see get_past_prediction_event).
_ALLOWED_FILE = "past_predictions.py"
_ALLOWED_FUNCTION = "def get_past_prediction_event("


def _without_allowed_function(name, src):
    if name != _ALLOWED_FILE:
        return src
    start = src.index(_ALLOWED_FUNCTION)
    end = src.find("\n@router.", start)
    return src[:start] + (src[end:] if end != -1 else "")


def test_no_endpoint_reads_past_predictions_directly():
    # Every scorecard, ROI and Vegas figure must come from scored_predictions,
    # or flagged rows count again.
    offenders = []
    for name in os.listdir(ENDPOINTS):
        if name.endswith(".py"):
            src = open(os.path.join(ENDPOINTS, name), encoding="utf-8").read()
            src = _without_allowed_function(name, src)
            if re.search(r"\b(FROM|JOIN)\s+past_predictions\b", src):
                offenders.append(name)
    assert offenders == []
