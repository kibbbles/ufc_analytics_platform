"""Matching our cards to UFC.com's event feed, and the archive's integrity flags."""

from datetime import date, datetime, timedelta, timezone

import pytest

from scraper import ufc_live_feed as feed
from scraper.archive_completed_predictions import integrity_flags


def _bout(fid, order, first_a, last_a, first_b, last_b, start="2026-11-21T18:00Z", segment="Main"):
    return {
        "FightId": fid, "FightOrder": order, "CardSegment": segment,
        "CardSegmentStartTime": start, "Status": "Final",
        "Fighters": [
            {"Name": {"FirstName": first_a, "LastName": last_a}},
            {"Name": {"FirstName": first_b, "LastName": last_b}},
        ],
    }


# Shapes taken from the UFC.com feed for UFC Fight Night: Prochazka vs. Stirling
# (event 1348) and UFC 334 (event 1345).
EVENT = {"FightCard": [
    _bout(13197, 1, "Jiří", "Procházka", "Navajo", "Stirling"),
    _bout(13262, 10, "Nikolas", "Motta", "Dom", "Mar Fan", start="2026-11-21T15:00Z", segment="Prelims1"),
    _bout(20001, 11, "Uroš", "Medić", "Kevin", "Holland", start="2026-11-21T15:00Z", segment="Prelims1"),
]}


def test_bouts_parse_section_starts_in_utc():
    bouts = feed.bouts(EVENT)
    assert [b.order for b in bouts] == [1, 10, 11]
    assert bouts[0].segment_start == datetime(2026, 11, 21, 18, 0, tzinfo=timezone.utc)
    assert bouts[1].segment == "Prelims1"


def test_bout_without_an_announced_start_is_kept_with_no_start():
    event = {"FightCard": [_bout(1, 1, "A", "One", "B", "Two", start=None)]}
    assert feed.bouts(event)[0].segment_start is None


def test_accented_names_match_our_ascii_names_in_either_order():
    bouts = feed.bouts(EVENT)
    assert feed.match_bout("Jiri Prochazka", "Navajo Stirling", bouts).fight_id == 13197
    assert feed.match_bout("Navajo Stirling", "Jiri Prochazka", bouts).fight_id == 13197
    assert feed.match_bout("Kevin Holland", "Uros Medic", bouts).fight_id == 20001


def test_multi_word_last_names_match_whole():
    assert feed.match_bout("Nikolas Motta", "Dom Mar Fan", feed.bouts(EVENT)).fight_id == 13262


def test_both_fighters_must_match_not_just_one():
    event = {"FightCard": [_bout(1, 1, "Bruno", "Silva", "Jean", "Matsumoto")]}
    assert feed.match_bout("Bruno Silva", "Jose Aldo", feed.bouts(event)) is None


def test_two_matching_bouts_return_none_rather_than_a_guess():
    event = {"FightCard": [_bout(1, 1, "A", "Silva", "B", "Silva"), _bout(2, 2, "C", "Silva", "D", "Silva")]}
    assert feed.match_bout("Bruno Silva", "Jean Silva", feed.bouts(event)) is None


def test_malformed_bout_raises_feed_error():
    with pytest.raises(feed.FeedError):
        feed.bouts({"FightCard": [{"FightId": 1}]})


SLUGS = ["ufc-334", "ufc-335", "ufc-fight-night-december-05-2026",
         "ufc-fight-night-november-21-2026", "noche-ufc-2026"]


def test_numbered_event_looks_only_at_its_own_page():
    assert feed.candidate_slugs("UFC 335: Oliveira vs. Lopes", date(2026, 12, 12), SLUGS) == ["ufc-335"]


def test_fight_night_looks_at_pages_within_a_day_and_undated_pages():
    got = feed.candidate_slugs("UFC Fight Night: Adesanya vs. Magomedov", date(2026, 12, 5), SLUGS)
    assert got == ["ufc-fight-night-december-05-2026", "noche-ufc-2026"]


# --- archive integrity flags -------------------------------------------------

START = datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc)


def _row(predicted=None, odds_at=None, odds=-150):
    return {"freeze_at": START, "section_start_at": START, "pre_fight_predicted_at": predicted,
            "odds_scraped_at": odds_at, "odds_a": odds}


def test_prediction_and_odds_before_the_start_are_clean():
    f = integrity_flags(_row(START - timedelta(hours=5), START - timedelta(days=1)))
    assert f["prediction_after_start"] is False and f["odds_after_start"] is False


def test_writes_at_or_after_the_start_are_flagged():
    # Nurgozhay vs. Lorenz: rewritten at 20:47, five hours after its section began.
    f = integrity_flags(_row(START + timedelta(hours=5, minutes=47), START + timedelta(hours=5, minutes=48)))
    assert f["prediction_after_start"] is True and f["odds_after_start"] is True
    assert integrity_flags(_row(START))["prediction_after_start"] is True


def test_odds_without_a_capture_time_are_unknown_not_clean():
    assert integrity_flags(_row(START - timedelta(hours=1), odds_at=None))["odds_after_start"] is None


def test_row_with_no_prediction_and_no_odds():
    f = integrity_flags(_row(predicted=None, odds_at=None, odds=None))
    assert f["prediction_after_start"] is False and f["odds_after_start"] is None
