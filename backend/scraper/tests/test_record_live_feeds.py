"""The fight-night recorder: what it saves, when it stops, and when it reports failure."""

import gzip
import json
from datetime import datetime, timedelta, timezone

from scraper.record_live_feeds import Fetch, Recorder, summarize

T0 = datetime(2026, 12, 5, 15, 0, tzinfo=timezone.utc)


def ufc_doc(statuses, event_status="Live"):
    return {"LiveEventDetail": {
        "Status": event_status, "LiveFightId": None, "LiveRoundNumber": None,
        "FightCard": [{"Status": s, "Result": {"Method": "KO/TKO" if s == "Final" else None}} for s in statuses],
    }}


def espn_doc(states):
    return {"events": [{"competitions": [
        {"status": {"type": {"state": st, "name": f"STATUS_{st.upper()}"}}, "competitors": []} for st in states
    ]}]}


class Clock:
    def __init__(self):
        self.t = T0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += timedelta(seconds=seconds)


def scripted(clock, script):
    """fetch() that answers from script[source](minute) -> (status, doc|None)."""
    def fetch(source, url):
        minute = int((clock.t - T0).total_seconds() // 60)
        status, doc = script[source](minute)
        f = Fetch(source, clock.t, http_status=status, latency_ms=40)
        if status == 200:
            f.body = json.dumps(doc).encode()
        elif status is None:
            f.error = "ConnectionError: boom"
        elif status != 304:
            f.error = f"HTTP {status}"
        return f
    return fetch


def recorder(clock, script, store=None, grace_min=5):
    rows = []
    rec = Recorder(recording="ufc-test", urls={"ufc_feed": "u", "espn_scoreboard": "e"},
                   fetch=scripted(clock, script), store=store or rows.append,
                   grace=timedelta(minutes=grace_min), now=clock.now, sleep=clock.sleep)
    return rec, rows


def card_finishing_at(minute):
    return {
        "ufc_feed": lambda m: (200, ufc_doc(["Final", "Final"], "Final") if m >= minute else ufc_doc(["Final", "Live"])),
        "espn_scoreboard": lambda m: (200, espn_doc(["post", "post"] if m >= minute else ["post", "in"])),
    }


def test_records_until_the_card_is_final_then_through_the_grace_period():
    clock = Clock()
    rec, rows = recorder(clock, card_finishing_at(10), grace_min=5)
    assert rec.run(T0, T0 + timedelta(hours=10)) is True
    # minutes 0..15: final at 10, stays final through 5 minutes of grace
    assert len(rows) == 2 * 16
    assert clock.t < T0 + timedelta(minutes=17)


def test_body_is_saved_only_when_it_changed():
    clock = Clock()
    rec, rows = recorder(clock, card_finishing_at(3), grace_min=2)
    rec.run(T0, T0 + timedelta(hours=1))
    ufc = [r for r in rows if r["source"] == "ufc_feed"]
    assert [r["changed"] for r in ufc] == [True, False, False, True, False, False]
    assert all((r["body_gz"] is not None) == r["changed"] for r in ufc)
    assert json.loads(gzip.decompress(ufc[3]["body_gz"]))["LiveEventDetail"]["Status"] == "Final"


def test_a_failed_fetch_is_recorded_and_polling_continues():
    clock = Clock()
    script = card_finishing_at(4)
    ok_ufc = script["ufc_feed"]
    script["ufc_feed"] = lambda m: (None, None) if m in (1, 2) else ok_ufc(m)
    rec, rows = recorder(clock, script, grace_min=2)
    assert rec.run(T0, T0 + timedelta(hours=1)) is True
    errors = [r for r in rows if r["error"]]
    assert len(errors) == 2 and all(r["source"] == "ufc_feed" and r["http_status"] is None for r in errors)


def test_not_modified_after_the_card_is_final_still_completes():
    clock = Clock()
    script = card_finishing_at(2)
    final = script["espn_scoreboard"]
    script["espn_scoreboard"] = lambda m: (304, None) if m >= 3 else final(m)
    rec, rows = recorder(clock, script, grace_min=3)
    assert rec.run(T0, T0 + timedelta(hours=1)) is True


def test_a_bout_reopened_during_the_grace_period_restarts_it():
    clock = Clock()
    script = card_finishing_at(2)
    final = script["ufc_feed"]
    # The feed briefly takes a result back at minute 4 (a correction), final again at 5.
    script["ufc_feed"] = lambda m: (200, ufc_doc(["Final", "Live"])) if m == 4 else final(m)
    rec, rows = recorder(clock, script, grace_min=3)
    assert rec.run(T0, T0 + timedelta(hours=1)) is True
    assert clock.t >= T0 + timedelta(minutes=8)   # grace counted again from minute 5


def test_time_cap_before_the_card_finishes_is_a_failure():
    clock = Clock()
    rec, rows = recorder(clock, card_finishing_at(999))
    assert rec.run(T0, T0 + timedelta(minutes=30)) is False


def test_a_source_that_never_answers_is_a_failure():
    clock = Clock()
    script = card_finishing_at(2)
    script["espn_scoreboard"] = lambda m: (403, None)
    rec, rows = recorder(clock, script)
    assert rec.run(T0, T0 + timedelta(minutes=20)) is False


def test_unsaved_snapshots_make_the_recording_a_failure_but_do_not_stop_it():
    clock = Clock()
    saved = []

    def flaky_store(row):
        if len(saved) == 1:
            saved.append(None)
            raise RuntimeError("db down")
        saved.append(row)

    rec, _ = recorder(clock, card_finishing_at(2), store=flaky_store, grace_min=2)
    assert rec.run(T0, T0 + timedelta(hours=1)) is False
    assert len(saved) > 4


def test_waits_for_the_start_time():
    clock = Clock()
    rec, rows = recorder(clock, card_finishing_at(0), grace_min=1)
    start = T0 + timedelta(minutes=90)
    rec.run(start, start + timedelta(hours=1))
    assert rows[0]["fetched_at"] >= start


def test_summaries_from_real_feed_shapes():
    assert summarize("ufc_feed", ufc_doc(["Final", "Final"], "Final"))["complete"] is True
    assert summarize("ufc_feed", ufc_doc(["Final", "Live"]))["complete"] is False
    # Event status can lag; every bout final is enough.
    assert summarize("ufc_feed", ufc_doc(["Final", "Final"], "Live"))["complete"] is True
    assert summarize("espn_scoreboard", espn_doc(["post", "in"]))["complete"] is False
    assert summarize("espn_scoreboard", {"events": []})["complete"] is False
