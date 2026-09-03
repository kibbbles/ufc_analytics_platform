"""
Tests for batched inference feature building.

Predicting a card used to call build_prediction_features once per fight, and
each call ran every feature module across the whole fights and stats tables to
read two rows out of the result. That was about 25 seconds per fight, roughly
half an hour for a 71-fight card, and the same cost is paid by the prediction
API endpoint on every request.

The batch path augments the whole card in one pass. It is only correct because a
phantom row is inert for every fighter but its own, so these tests pin the two
properties that guarantee that: one phantom pair per matchup with ids derived
from the fighter, and a refusal when a fighter would appear twice.
"""

import numpy as np
import pandas as pd
import pytest

from features.pipeline import (
    _augment_for_inference,
    _phantom_fight_id,
    build_prediction_features_batch,
)


FIGHT_COLS = ["fight_id", "fighter_id", "opponent_id", "is_winner",
              "weight_class", "method", "total_fight_time_seconds", "date_proper"]
STAT_COLS = ["id", "fight_id", "event_id", "fighter_id", "ROUND",
             "date_proper", "sig_str_landed", "ctrl_seconds"]


@pytest.fixture
def fights():
    return pd.DataFrame(
        [{
            "fight_id": "F1", "fighter_id": "AAA", "opponent_id": "BBB",
            "is_winner": True, "weight_class": "Lightweight", "method": "KO/TKO",
            "total_fight_time_seconds": 300, "date_proper": pd.Timestamp("2025-01-01"),
        }],
        columns=FIGHT_COLS,
    )


@pytest.fixture
def stats():
    return pd.DataFrame(
        [{
            "id": "S1", "fight_id": "F1", "event_id": "E1", "fighter_id": "AAA",
            "ROUND": "Round 1", "date_proper": pd.Timestamp("2025-01-01"),
            "sig_str_landed": 10, "ctrl_seconds": 30,
        }],
        columns=STAT_COLS,
    )


class TestAugmentForInference:
    """One phantom pair per matchup, and real rows left untouched."""

    def test_single_matchup_adds_two_phantom_fight_rows(self, fights, stats):
        as_of = pd.Timestamp("2026-09-12")
        f_aug, s_aug, ids = _augment_for_inference(
            fights, stats, [("AAA", "BBB", "Lightweight")], as_of)

        assert len(f_aug) == len(fights) + 2
        assert len(s_aug) == len(stats) + 2
        assert set(ids) == {"AAA", "BBB"}

    def test_phantom_ids_derive_from_the_fighter(self, fights, stats):
        _, _, ids = _augment_for_inference(
            fights, stats, [("AAA", "BBB", "Lightweight")], pd.Timestamp("2026-09-12"))
        assert ids["AAA"] == _phantom_fight_id("AAA")
        assert ids["BBB"] == _phantom_fight_id("BBB")

    def test_phantom_carries_no_outcome_and_zeroed_stats(self, fights, stats):
        """The phantom must contribute nothing to its own features."""
        f_aug, s_aug, ids = _augment_for_inference(
            fights, stats, [("AAA", "BBB", "Lightweight")], pd.Timestamp("2026-09-12"))

        ph = f_aug[f_aug["fight_id"] == ids["AAA"]].iloc[0]
        assert ph["is_winner"] == False          # noqa: E712 - inert, shifted out
        assert ph["method"] is None
        assert np.isnan(ph["total_fight_time_seconds"])

        ps = s_aug[s_aug["fight_id"] == ids["AAA"]].iloc[0]
        assert ps["sig_str_landed"] == 0
        assert ps["ctrl_seconds"] == 0

    def test_many_matchups_add_one_pair_each(self, fights, stats):
        """Batching a card must produce exactly the rows the per-matchup path
        would, which is what makes one pass equivalent to N passes."""
        matchups = [("AAA", "BBB", "Lightweight"),
                    ("CCC", "DDD", "Flyweight"),
                    ("EEE", "FFF", None)]
        f_aug, s_aug, ids = _augment_for_inference(
            fights, stats, matchups, pd.Timestamp("2026-09-12"))

        assert len(f_aug) == len(fights) + 6
        assert len(s_aug) == len(stats) + 6
        assert set(ids) == {"AAA", "BBB", "CCC", "DDD", "EEE", "FFF"}
        # each phantom appears exactly once
        for fid in ids:
            assert (f_aug["fight_id"] == ids[fid]).sum() == 1

    def test_each_matchup_keeps_its_own_weight_class(self, fights, stats):
        matchups = [("AAA", "BBB", "Lightweight"), ("CCC", "DDD", "Flyweight")]
        f_aug, _, ids = _augment_for_inference(
            fights, stats, matchups, pd.Timestamp("2026-09-12"))
        assert f_aug[f_aug["fight_id"] == ids["AAA"]].iloc[0]["weight_class"] == "Lightweight"
        assert f_aug[f_aug["fight_id"] == ids["CCC"]].iloc[0]["weight_class"] == "Flyweight"

    def test_real_rows_are_not_modified(self, fights, stats):
        before = fights.copy()
        _augment_for_inference(fights, stats, [("AAA", "BBB", "Lightweight")],
                               pd.Timestamp("2026-09-12"))
        pd.testing.assert_frame_equal(fights, before)


class TestBatchRejectsRepeatedFighter:
    """Phantom ids come from the fighter id, so a repeat would collide.

    Silently letting two matchups share a phantom would give one of them another
    fighter's features. The batch refuses instead, and the caller groups
    matchups so no fighter repeats.
    """

    def test_same_fighter_twice_raises(self):
        with pytest.raises(ValueError, match="more than one matchup"):
            build_prediction_features_batch(
                [("AAA", "BBB", None), ("AAA", "CCC", None)])

    def test_fighter_on_both_sides_raises(self):
        with pytest.raises(ValueError, match="more than one matchup"):
            build_prediction_features_batch(
                [("AAA", "BBB", None), ("CCC", "BBB", None)])

    def test_empty_input_returns_empty(self):
        assert build_prediction_features_batch([]) == []
