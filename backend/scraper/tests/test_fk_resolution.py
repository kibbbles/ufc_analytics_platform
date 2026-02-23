"""
Unit tests for FK resolution logic in populate_fighter_fks.py.

resolve_name() is pure Python (no DB) and is tested directly.
build_fighter_lookup() accepts a conn and is tested with a MagicMock.

No real database connection required.

Run from the project root:
    cd backend
    pytest scraper/tests/test_fk_resolution.py -v
"""

import pytest
from unittest.mock import MagicMock

from scraper.populate_fighter_fks import resolve_name, build_fighter_lookup, SCORE_CUTOFF


# ---------------------------------------------------------------------------
# Shared fixture — small in-memory fighter lookup
# ---------------------------------------------------------------------------

@pytest.fixture()
def lookup():
    return {
        "khabib nurmagomedov": "KH001",
        "conor mcgregor":      "CM002",
        "jon jones":           "JJ003",
        "anderson silva":      "AS004",
        "demetrious johnson":  "DJ005",
        "amanda nunes":        "AN006",
    }


@pytest.fixture()
def names_list(lookup):
    return list(lookup.keys())


# ---------------------------------------------------------------------------
# resolve_name — exact matches
# ---------------------------------------------------------------------------

class TestResolveNameExact:
    """Exact-match branch of resolve_name()."""

    def test_canonical_name(self, lookup, names_list):
        fid, match_type = resolve_name("Khabib Nurmagomedov", lookup, names_list)
        assert fid == "KH001"
        assert match_type == "exact"

    def test_case_insensitive(self, lookup, names_list):
        fid, match_type = resolve_name("CONOR MCGREGOR", lookup, names_list)
        assert fid == "CM002"
        assert match_type == "exact"

    def test_mixed_case(self, lookup, names_list):
        fid, match_type = resolve_name("Jon Jones", lookup, names_list)
        assert fid == "JJ003"
        assert match_type == "exact"

    def test_leading_trailing_whitespace_stripped(self, lookup, names_list):
        fid, match_type = resolve_name("  Anderson Silva  ", lookup, names_list)
        assert fid == "AS004"
        assert match_type == "exact"

    def test_internal_spaces_preserved(self, lookup, names_list):
        # "demetrious johnson" must not accidentally match something shorter
        fid, match_type = resolve_name("Demetrious Johnson", lookup, names_list)
        assert fid == "DJ005"
        assert match_type == "exact"


# ---------------------------------------------------------------------------
# resolve_name — fuzzy matches
# ---------------------------------------------------------------------------

class TestResolveNameFuzzy:
    """Fuzzy-match branch of resolve_name() (above SCORE_CUTOFF threshold)."""

    def test_slight_misspelling_of_last_name(self, lookup, names_list):
        # "Nurmagomedof" — one char substitution at end
        fid, match_type = resolve_name("Khabib Nurmagomedof", lookup, names_list)
        assert fid == "KH001"
        assert match_type == "fuzzy"

    def test_slight_misspelling_of_first_name(self, lookup, names_list):
        # "Conner McGregor" — common anglicised misspelling
        fid, match_type = resolve_name("Conner McGregor", lookup, names_list)
        assert fid == "CM002"
        assert match_type == "fuzzy"

    def test_transposition_error(self, lookup, names_list):
        # "Jon Jons" — one letter dropped
        fid, match_type = resolve_name("Jon Jons", lookup, names_list)
        assert fid == "JJ003"
        assert match_type == "fuzzy"


# ---------------------------------------------------------------------------
# resolve_name — no match
# ---------------------------------------------------------------------------

class TestResolveNameNoMatch:
    """Cases where no match should be returned."""

    def test_completely_unknown_fighter(self, lookup, names_list):
        fid, match_type = resolve_name("Zzyzx Quirky", lookup, names_list)
        assert fid is None
        assert match_type is None

    def test_empty_string(self, lookup, names_list):
        fid, match_type = resolve_name("", lookup, names_list)
        assert fid is None
        assert match_type is None

    def test_whitespace_only(self, lookup, names_list):
        fid, match_type = resolve_name("   ", lookup, names_list)
        assert fid is None
        assert match_type is None

    def test_single_word_no_match(self, lookup, names_list):
        # Partial name unlikely to score above SCORE_CUTOFF
        fid, _ = resolve_name("Xyzabc", lookup, names_list)
        assert fid is None

    def test_score_cutoff_constant_is_positive(self):
        """SCORE_CUTOFF must be > 0 to prevent trivially low-quality matches."""
        assert SCORE_CUTOFF > 0

    def test_score_cutoff_is_reasonable(self):
        """SCORE_CUTOFF should be ≥ 80 to avoid false positives."""
        assert SCORE_CUTOFF >= 80


# ---------------------------------------------------------------------------
# build_fighter_lookup — mocked DB connection
# ---------------------------------------------------------------------------

class TestBuildFighterLookup:
    """build_fighter_lookup(conn) with mocked conn.execute()."""

    def _make_conn(self, rows):
        """rows: list of (id, first, last) tuples."""
        conn = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = rows
        conn.execute.return_value = result
        return conn

    def test_builds_full_name_entry(self):
        conn = self._make_conn([("KH001", "Khabib", "Nurmagomedov")])
        lk = build_fighter_lookup(conn)
        assert "khabib nurmagomedov" in lk
        assert lk["khabib nurmagomedov"] == "KH001"

    def test_lowercases_all_names(self):
        conn = self._make_conn([("CM002", "Conor", "McGregor")])
        lk = build_fighter_lookup(conn)
        assert "conor mcgregor" in lk
        assert "Conor McGregor" not in lk

    def test_multiple_fighters(self):
        conn = self._make_conn([
            ("KH001", "Khabib", "Nurmagomedov"),
            ("CM002", "Conor",  "McGregor"),
            ("JJ003", "Jon",    "Jones"),
        ])
        lk = build_fighter_lookup(conn)
        assert len(lk) == 3
        assert lk["jon jones"] == "JJ003"

    def test_handles_null_first_name(self):
        """Fighter with no first name — last name used as key."""
        conn = self._make_conn([("AB001", None, "AbdulSalaam")])
        lk = build_fighter_lookup(conn)
        assert "abdulsalaam" in lk
        assert lk["abdulsalaam"] == "AB001"

    def test_skips_row_with_null_last_name(self):
        """Row with NULL last name should be silently skipped."""
        conn = self._make_conn([("XX001", "Fighter", None)])
        lk = build_fighter_lookup(conn)
        assert len(lk) == 0

    def test_skips_row_with_both_names_null(self):
        conn = self._make_conn([("YY001", None, None)])
        lk = build_fighter_lookup(conn)
        assert len(lk) == 0

    def test_first_occurrence_wins_on_duplicate_name(self):
        """Two fighters with the same full name — first one in DB wins."""
        conn = self._make_conn([
            ("ID001", "Michael", "Johnson"),
            ("ID002", "Michael", "Johnson"),
        ])
        lk = build_fighter_lookup(conn)
        assert lk.get("michael johnson") == "ID001"

    def test_empty_db_returns_empty_dict(self):
        conn = self._make_conn([])
        lk = build_fighter_lookup(conn)
        assert lk == {}

    def test_padded_names_still_stored_in_lookup(self):
        """Names with leading/trailing spaces are outer-stripped but internal
        spacing from the f-string join is preserved in the key.  The fighter_id
        must still be accessible in the lookup."""
        conn = self._make_conn([("JD001", " Jane ", " Doe ")])
        lk = build_fighter_lookup(conn)
        # f"{' Jane '} {' Doe '}".strip().lower() = "jane   doe" (3 spaces)
        # Regardless of exact key spacing, the ID must be reachable.
        assert "JD001" in lk.values()
