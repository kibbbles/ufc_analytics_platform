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
# resolve_name — ambiguous names are refused, never guessed
# ---------------------------------------------------------------------------

class TestResolveNameAmbiguous:
    """A name owned by more than one fighter must resolve to nobody.

    This is the guard for the defect that filed 36 bouts under the wrong person:
    two fighters shared a name, the resolver picked whichever row came back
    first, and reported the guess as an exact match.
    """

    def test_ambiguous_name_returns_no_id(self, lookup, names_list):
        ambiguous = {"bruno silva": ["294aa73d", "12ebd7d1"]}
        fid, match_type = resolve_name(
            "Bruno Silva", lookup, names_list, ambiguous)
        assert fid is None
        assert match_type == "ambiguous"

    def test_ambiguous_beats_an_exact_match(self, lookup, names_list):
        """Refusal wins even when the name is also present in the lookup.

        Ordering matters here: if the exact-match branch ran first, an ambiguous
        name that also had a lookup entry would still be silently resolved.
        """
        name = next(iter(lookup))
        ambiguous = {name: ["AAA", "BBB"]}
        fid, match_type = resolve_name(name, lookup, names_list, ambiguous)
        assert fid is None
        assert match_type == "ambiguous"

    def test_ambiguous_matching_is_case_and_space_insensitive(
            self, lookup, names_list):
        ambiguous = {"mike davis": ["c8661e20", "fb3e6172"]}
        fid, match_type = resolve_name(
            "  MIKE   Davis  ".replace("   ", " "), lookup, names_list, ambiguous)
        assert fid is None
        assert match_type == "ambiguous"

    def test_unambiguous_name_still_resolves(self, lookup, names_list):
        """The refusal must not block ordinary names."""
        name = next(iter(lookup))
        fid, match_type = resolve_name(
            name, lookup, names_list, {"someone else": ["X", "Y"]})
        assert fid == lookup[name]
        assert match_type == "exact"

    def test_omitting_ambiguous_argument_keeps_old_signature_working(
            self, lookup, names_list):
        name = next(iter(lookup))
        fid, match_type = resolve_name(name, lookup, names_list)
        assert fid == lookup[name]
        assert match_type == "exact"


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
        lk, _ = build_fighter_lookup(conn)
        assert "khabib nurmagomedov" in lk
        assert lk["khabib nurmagomedov"] == "KH001"

    def test_lowercases_all_names(self):
        conn = self._make_conn([("CM002", "Conor", "McGregor")])
        lk, _ = build_fighter_lookup(conn)
        assert "conor mcgregor" in lk
        assert "Conor McGregor" not in lk

    def test_multiple_fighters(self):
        conn = self._make_conn([
            ("KH001", "Khabib", "Nurmagomedov"),
            ("CM002", "Conor",  "McGregor"),
            ("JJ003", "Jon",    "Jones"),
        ])
        lk, ambiguous = build_fighter_lookup(conn)
        assert len(lk) == 3
        assert lk["jon jones"] == "JJ003"
        assert ambiguous == {}

    def test_handles_null_first_name(self):
        """Mononym stored the import's way — NULL FIRST, name in LAST."""
        conn = self._make_conn([("AB001", None, "AbdulSalaam")])
        lk, _ = build_fighter_lookup(conn)
        assert "abdulsalaam" in lk
        assert lk["abdulsalaam"] == "AB001"

    def test_mononym_stored_as_first_is_still_reachable(self):
        """Mononym stored the scraper's way — name in FIRST, empty LAST.

        This row used to be dropped from the lookup entirely, so it could never
        receive an FK no matter how often the ETL ran. That is why Aoriqileng,
        Sumudaerji, Sulangrangbo and Yizha all showed 0-0 records.
        """
        conn = self._make_conn([("XX001", "Aoriqileng", None)])
        lk, _ = build_fighter_lookup(conn)
        assert lk["aoriqileng"] == "XX001"

    def test_skips_row_with_both_names_null(self):
        conn = self._make_conn([("YY001", None, None)])
        lk, ambiguous = build_fighter_lookup(conn)
        assert len(lk) == 0
        assert ambiguous == {}

    def test_shared_name_is_refused_not_guessed(self):
        """Two different fighters sharing a name must resolve to neither.

        The old behaviour kept whichever row the database returned first, which
        gave one person both careers and reported it as an exact match.
        """
        conn = self._make_conn([
            ("ID001", "Michael", "Johnson"),
            ("ID002", "Michael", "Johnson"),
        ])
        lk, ambiguous = build_fighter_lookup(conn)
        assert "michael johnson" not in lk
        assert sorted(ambiguous["michael johnson"]) == ["ID001", "ID002"]

    def test_mononym_duplicate_across_both_name_shapes_is_ambiguous(self):
        """The same mononym written both ways is one person in two rows.

        Both spellings normalise to the same name, so the pair is flagged rather
        than silently resolved to one of the two rows.
        """
        conn = self._make_conn([
            ("HCXIJG",   "Aoriqileng", None),
            ("7d420039", None,         "Aoriqileng"),
        ])
        lk, ambiguous = build_fighter_lookup(conn)
        assert "aoriqileng" not in lk
        assert sorted(ambiguous["aoriqileng"]) == ["7d420039", "HCXIJG"]

    def test_empty_db_returns_empty_lookup(self):
        conn = self._make_conn([])
        lk, ambiguous = build_fighter_lookup(conn)
        assert lk == {}
        assert ambiguous == {}

    def test_padded_names_still_stored_in_lookup(self):
        """Names with leading/trailing spaces are normalised; the fighter_id
        must still be reachable in the lookup."""
        conn = self._make_conn([("JD001", " Jane ", " Doe ")])
        lk, _ = build_fighter_lookup(conn)
        assert "JD001" in lk.values()
