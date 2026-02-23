"""
Unit tests for type_parsing.py — pure-Python helper functions and DB wrappers.

No real database connection required.  DB interactions are exercised via
MagicMock so the logic of add_columns() and parse_x_of_y() is verified
without touching Supabase.

Run from the project root:
    cd backend
    pytest scraper/tests/test_parsers.py -v
"""

import pytest
from unittest.mock import MagicMock, call, patch
from sqlalchemy import text as sa_text

from scraper.type_parsing import (
    parse_x_of_y_str,
    parse_ctrl_time_str,
    parse_height_inches_str,
    parse_weight_lbs_str,
    parse_reach_inches_str,
    calc_total_fight_time,
    add_columns,
    parse_x_of_y,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(existing_cols=None, rowcount=10):
    """Return a MagicMock conn pre-configured for add_columns / parse_x_of_y."""
    conn = MagicMock()
    # First execute() call (information_schema) returns column names.
    col_result = MagicMock()
    col_result.fetchall.return_value = [(c,) for c in (existing_cols or [])]
    # Subsequent execute() calls (ALTER / UPDATE) return a result with rowcount.
    update_result = MagicMock()
    update_result.rowcount = rowcount
    conn.execute.side_effect = [col_result, update_result, update_result,
                                 update_result, update_result, update_result]
    return conn


# ---------------------------------------------------------------------------
# parse_x_of_y_str
# ---------------------------------------------------------------------------

class TestParseXOfYStr:
    """parse_x_of_y_str(val) -> (landed, attempted) | (None, None)."""

    def test_typical_strike_count(self):
        assert parse_x_of_y_str("17 of 37") == (17, 37)

    def test_zero_of_zero(self):
        assert parse_x_of_y_str("0 of 0") == (0, 0)

    def test_zero_landed_nonzero_attempted(self):
        assert parse_x_of_y_str("0 of 12") == (0, 12)

    def test_equal_landed_and_attempted(self):
        assert parse_x_of_y_str("5 of 5") == (5, 5)

    def test_large_values(self):
        assert parse_x_of_y_str("150 of 200") == (150, 200)

    def test_none_input(self):
        assert parse_x_of_y_str(None) == (None, None)

    def test_double_dash_placeholder(self):
        assert parse_x_of_y_str("--") == (None, None)

    def test_triple_dash_placeholder(self):
        assert parse_x_of_y_str("---") == (None, None)

    def test_empty_string(self):
        assert parse_x_of_y_str("") == (None, None)

    def test_whitespace_only(self):
        assert parse_x_of_y_str("   ") == (None, None)

    def test_missing_of_separator(self):
        assert parse_x_of_y_str("17") == (None, None)

    def test_non_numeric_values(self):
        assert parse_x_of_y_str("abc of xyz") == (None, None)

    def test_partial_non_numeric(self):
        assert parse_x_of_y_str("17 of xyz") == (None, None)

    def test_non_string_input_int(self):
        assert parse_x_of_y_str(42) == (None, None)

    def test_leading_trailing_whitespace_stripped(self):
        # The function strips the outer val; internal spacing handled by split
        assert parse_x_of_y_str("  5 of 10  ") == (5, 10)


# ---------------------------------------------------------------------------
# parse_ctrl_time_str
# ---------------------------------------------------------------------------

class TestParseCtrlTimeStr:
    """parse_ctrl_time_str(val) -> int seconds | None."""

    def test_zero_ctrl(self):
        assert parse_ctrl_time_str("0:00") == 0

    def test_full_five_minutes(self):
        assert parse_ctrl_time_str("5:00") == 300

    def test_two_minutes_34_seconds(self):
        assert parse_ctrl_time_str("2:34") == 154

    def test_one_second(self):
        assert parse_ctrl_time_str("0:01") == 1

    def test_one_minute_exactly(self):
        assert parse_ctrl_time_str("1:00") == 60

    def test_none_input(self):
        assert parse_ctrl_time_str(None) is None

    def test_double_dash_placeholder(self):
        assert parse_ctrl_time_str("--") is None

    def test_triple_dash_placeholder(self):
        assert parse_ctrl_time_str("---") is None

    def test_empty_string(self):
        assert parse_ctrl_time_str("") is None

    def test_no_colon(self):
        assert parse_ctrl_time_str("234") is None

    def test_non_numeric_parts(self):
        assert parse_ctrl_time_str("abc:def") is None

    def test_non_string_input(self):
        assert parse_ctrl_time_str(300) is None

    def test_large_value_pre_2001_ufc(self):
        # Old UFC had no time limits; 15-min rounds are legitimate.
        assert parse_ctrl_time_str("15:00") == 900

    def test_leading_whitespace_stripped(self):
        assert parse_ctrl_time_str("  2:30  ") == 150


# ---------------------------------------------------------------------------
# parse_height_inches_str
# ---------------------------------------------------------------------------

class TestParseHeightInchesStr:
    """parse_height_inches_str(val) -> float inches | None."""

    def test_five_ten(self):
        assert parse_height_inches_str("5' 10\"") == 70.0

    def test_six_foot_even(self):
        assert parse_height_inches_str("6' 0\"") == 72.0

    def test_six_four(self):
        assert parse_height_inches_str("6' 4\"") == 76.0

    def test_five_foot_with_space_and_quote(self):
        assert parse_height_inches_str("5' 5\"") == 65.0

    def test_none_input(self):
        assert parse_height_inches_str(None) is None

    def test_double_dash_placeholder(self):
        assert parse_height_inches_str("--") is None

    def test_empty_string(self):
        assert parse_height_inches_str("") is None

    def test_no_feet_marker(self):
        # Plain number without ' is not parseable as height
        assert parse_height_inches_str("70") is None

    def test_non_numeric(self):
        assert parse_height_inches_str("six foot") is None

    def test_non_string_input(self):
        assert parse_height_inches_str(70) is None

    def test_no_inch_component(self):
        # "5' " — no inch digit; should return 60.0 (5 feet, 0 inches)
        result = parse_height_inches_str("5' ")
        assert result == 60.0


# ---------------------------------------------------------------------------
# parse_weight_lbs_str
# ---------------------------------------------------------------------------

class TestParseWeightLbsStr:
    """parse_weight_lbs_str(val) -> float lbs | None."""

    def test_lightweight_155(self):
        assert parse_weight_lbs_str("155 lbs.") == 155.0

    def test_heavyweight_265(self):
        assert parse_weight_lbs_str("265 lbs.") == 265.0

    def test_flyweight_125(self):
        assert parse_weight_lbs_str("125 lbs.") == 125.0

    def test_welterweight_170(self):
        assert parse_weight_lbs_str("170 lbs.") == 170.0

    def test_none_input(self):
        assert parse_weight_lbs_str(None) is None

    def test_double_dash_placeholder(self):
        assert parse_weight_lbs_str("--") is None

    def test_empty_string(self):
        assert parse_weight_lbs_str("") is None

    def test_non_numeric(self):
        assert parse_weight_lbs_str("heavy lbs.") is None

    def test_non_string_input(self):
        assert parse_weight_lbs_str(155) is None


# ---------------------------------------------------------------------------
# parse_reach_inches_str
# ---------------------------------------------------------------------------

class TestParseReachInchesStr:
    """parse_reach_inches_str(val) -> float inches | None."""

    def test_standard_reach(self):
        assert parse_reach_inches_str('74"') == 74.0

    def test_short_reach(self):
        assert parse_reach_inches_str('60"') == 60.0

    def test_long_reach(self):
        assert parse_reach_inches_str('84"') == 84.0

    def test_none_input(self):
        assert parse_reach_inches_str(None) is None

    def test_double_dash_placeholder(self):
        assert parse_reach_inches_str("--") is None

    def test_empty_string(self):
        assert parse_reach_inches_str("") is None

    def test_no_quote_still_parseable(self):
        # "74" without trailing quote — should still parse
        assert parse_reach_inches_str("74") == 74.0

    def test_non_numeric(self):
        assert parse_reach_inches_str('long"') is None

    def test_non_string_input(self):
        assert parse_reach_inches_str(74) is None


# ---------------------------------------------------------------------------
# calc_total_fight_time
# ---------------------------------------------------------------------------

class TestCalcTotalFightTime:
    """calc_total_fight_time(round_num, time_str) -> int seconds | None."""

    def test_round_1_early_finish(self):
        # R1, 2:30 -> 150 s
        assert calc_total_fight_time(1, "2:30") == 150

    def test_round_1_end(self):
        # R1, 5:00 -> 300 s
        assert calc_total_fight_time(1, "5:00") == 300

    def test_round_2_finish(self):
        # R2, 0:30 -> 1*300 + 30 = 330 s
        assert calc_total_fight_time(2, "0:30") == 330

    def test_round_3_end(self):
        # R3, 5:00 -> 2*300 + 300 = 900 s
        assert calc_total_fight_time(3, "5:00") == 900

    def test_round_4_midway(self):
        # R4, 2:12 -> 3*300 + 132 = 1032 s
        assert calc_total_fight_time(4, "2:12") == 1032

    def test_round_5_end_full_fight(self):
        # R5, 5:00 -> 4*300 + 300 = 1500 s
        assert calc_total_fight_time(5, "5:00") == 1500

    def test_round_5_early_finish(self):
        # R5, 2:12 -> 4*300 + 132 = 1332 s
        assert calc_total_fight_time(5, "2:12") == 1332

    def test_none_round(self):
        assert calc_total_fight_time(None, "2:30") is None

    def test_none_time(self):
        assert calc_total_fight_time(1, None) is None

    def test_both_none(self):
        assert calc_total_fight_time(None, None) is None

    def test_invalid_time_string(self):
        assert calc_total_fight_time(1, "--") is None

    def test_invalid_round_string(self):
        assert calc_total_fight_time("abc", "2:30") is None

    def test_string_round_number(self):
        # ROUND column is TEXT in the DB, so "1" is valid input.
        assert calc_total_fight_time("1", "2:30") == 150

    def test_string_round_5(self):
        assert calc_total_fight_time("5", "5:00") == 1500


# ---------------------------------------------------------------------------
# add_columns (mocked DB)
# ---------------------------------------------------------------------------

class TestAddColumns:
    """add_columns(conn, table, col_defs) — verifies DDL logic with mock conn."""

    def _make_conn(self, existing_cols):
        conn = MagicMock()
        col_result = MagicMock()
        col_result.fetchall.return_value = [(c,) for c in existing_cols]
        # Return the column-query result first; subsequent calls return a generic mock.
        conn.execute.side_effect = lambda q, *a, **kw: col_result
        return conn

    def test_adds_missing_columns(self):
        conn = self._make_conn([])
        add_columns(conn, "fight_stats", [("sig_str_landed", "INTEGER"),
                                          ("sig_str_attempted", "INTEGER")])
        # 1 SELECT (information_schema) + 2 ALTER TABLE calls
        assert conn.execute.call_count == 3

    def test_skips_existing_columns(self):
        conn = self._make_conn(["sig_str_landed"])
        add_columns(conn, "fight_stats", [("sig_str_landed", "INTEGER"),
                                          ("sig_str_attempted", "INTEGER")])
        # 1 SELECT + 1 ALTER TABLE (only sig_str_attempted is new)
        assert conn.execute.call_count == 2

    def test_all_existing_no_alter(self):
        conn = self._make_conn(["col_a", "col_b"])
        add_columns(conn, "fight_stats", [("col_a", "INTEGER"),
                                          ("col_b", "TEXT")])
        # Only the information_schema SELECT — no ALTER statements needed
        assert conn.execute.call_count == 1

    def test_commits_when_column_added(self):
        conn = self._make_conn([])
        add_columns(conn, "fight_stats", [("new_col", "INTEGER")])
        conn.commit.assert_called()

    def test_commits_even_when_nothing_added(self):
        conn = self._make_conn(["new_col"])
        add_columns(conn, "fight_stats", [("new_col", "INTEGER")])
        conn.commit.assert_called()


# ---------------------------------------------------------------------------
# parse_x_of_y (SQL wrapper, mocked DB)
# ---------------------------------------------------------------------------

class TestParseXOfYSql:
    """parse_x_of_y(conn, src_col, landed_col, attempted_col) — verifies SQL execution."""

    def _make_conn(self, rowcount=100):
        conn = MagicMock()
        result = MagicMock()
        result.rowcount = rowcount
        conn.execute.return_value = result
        return conn

    def test_returns_rowcount(self):
        conn = self._make_conn(rowcount=500)
        n = parse_x_of_y(conn, "SIG.STR.", "sig_str_landed", "sig_str_attempted")
        assert n == 500

    def test_executes_update_statement(self):
        conn = self._make_conn()
        parse_x_of_y(conn, "SIG.STR.", "sig_str_landed", "sig_str_attempted")
        assert conn.execute.called
        # The argument is a sqlalchemy TextClause — inspect its .text attribute
        executed_sql = conn.execute.call_args.args[0].text
        assert "UPDATE" in executed_sql
        assert "fight_stats" in executed_sql

    def test_commits_after_update(self):
        conn = self._make_conn()
        parse_x_of_y(conn, "SIG.STR.", "sig_str_landed", "sig_str_attempted")
        conn.commit.assert_called_once()

    def test_zero_rows_updated(self):
        conn = self._make_conn(rowcount=0)
        n = parse_x_of_y(conn, "SIG.STR.", "sig_str_landed", "sig_str_attempted")
        assert n == 0
