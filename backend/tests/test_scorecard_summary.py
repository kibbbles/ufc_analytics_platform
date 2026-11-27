"""
Scorecard summary counts, checked against the live database.

The summary buckets raw UFCStats method strings ("Decision - Split",
"TKO - Doctor's Stoppage") in SQL. These tests recount the same rows in
Python, so a bucketing mistake in either place shows up as a mismatch.

Run from backend/:
    pytest tests/test_scorecard_summary.py -v
"""

import os
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.main import app
from db.database import engine


def _bucket(actual_method):
    if actual_method.startswith("Decision"):
        return "Decision"
    if actual_method == "KO/TKO" or actual_method.startswith("TKO"):
        return "KO/TKO"
    if actual_method == "Submission":
        return "Submission"
    return None


def _summary():
    return TestClient(app).get("/api/v1/past-predictions").json()["summary"]


def test_method_counts_match_a_recount_of_the_live_rows():
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT predicted_method, actual_method
            FROM scored_predictions
            WHERE prediction_source = 'pre_fight_archive'
              AND is_correct IS NOT NULL
              AND predicted_method IS NOT NULL
              AND actual_method IS NOT NULL
        """)).all()

    s = _summary()
    assert s["method_total"] == len(rows)
    assert s["method_correct"] == sum(1 for p, a in rows if _bucket(a) == p)
    assert s["method_decision_count"] == sum(1 for _, a in rows if _bucket(a) == "Decision")


def test_baseline_counts_agree_with_the_accuracies():
    s = _summary()
    n = s["baseline_sample"]
    assert n > 0
    assert s["baseline_vegas_correct"] == round(s["baseline_vegas_accuracy"] * n)
    assert s["baseline_model_correct"] == round(s["baseline_model_accuracy"] * n)
    # The baseline only covers live fights that had odds, a subset of the live record.
    assert n <= s["pre_fight_total"]
