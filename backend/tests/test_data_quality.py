"""
Data Quality Test Suite — programmatic version of docs/sanity-check.md.

Checks are grouped into four sections:
  1. Fighter record ground truths  (W-L-D-NC)
  2. Fight-level spot checks       (correct FK assignment, OUTCOME, winner)
  3. FK coverage thresholds        (completeness %)
  4. Parsed column sanity          (ranges, NULLs, derived values)

Run from the project root:
    cd backend
    pytest tests/test_data_quality.py -v

Add new tests freely — each function is self-contained and uses a shared
`conn` fixture that wraps a single Supabase connection for the whole session.
"""

import sys
import os
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine


# ---------------------------------------------------------------------------
# Shared fixture — one connection per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def conn():
    with engine.connect() as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RECORD_SQL = """
    SELECT
        COUNT(*) FILTER (WHERE fr.fighter_id  = :fid AND fr.is_winner = TRUE)   AS wins,
        COUNT(*) FILTER (WHERE fr.opponent_id = :fid AND fr.is_winner = TRUE)   AS losses,
        COUNT(*) FILTER (WHERE (fr.fighter_id = :fid OR fr.opponent_id = :fid)
                          AND fr."OUTCOME" = 'D/D')                              AS draws,
        COUNT(*) FILTER (WHERE (fr.fighter_id = :fid OR fr.opponent_id = :fid)
                          AND fr."OUTCOME" = 'NC/NC')                            AS nc
    FROM fight_results fr
"""


def get_fighter_id(conn, last_name, first_name=None):
    """Return the fighter_details.id for a fighter by name."""
    if first_name:
        row = conn.execute(text("""
            SELECT id FROM fighter_details
            WHERE "LAST"  ILIKE :last
              AND "FIRST" ILIKE :first
        """), {"last": last_name, "first": first_name}).fetchone()
    else:
        rows = conn.execute(text("""
            SELECT id, "FIRST", "LAST" FROM fighter_details
            WHERE "LAST" ILIKE :last
        """), {"last": last_name}).fetchall()
        if len(rows) == 1:
            return rows[0][0]
        # Multiple matches — caller should pass first_name
        names = [f"{r[1]} {r[2]}" for r in rows]
        pytest.fail(
            f"Ambiguous last name '{last_name}': found {names}. "
            "Pass first_name= to get_fighter_id()."
        )
    if row is None:
        pytest.fail(f"Fighter '{first_name} {last_name}' not found in fighter_details")
    return row[0]


def get_record(conn, fid):
    """Return (wins, losses, draws, nc) for a fighter_details.id."""
    row = conn.execute(text(RECORD_SQL), {"fid": fid}).fetchone()
    return tuple(row)


# ---------------------------------------------------------------------------
# Section 1 — Fighter Record Ground Truths
# From docs/sanity-check.md Part 1, verified 2025-12.
# ---------------------------------------------------------------------------

class TestFighterRecords:
    """W-L-D-NC ground truths for known fighters."""

    def test_khabib_nurmagomedov_13_0_0_0(self, conn):
        # Must specify first name — Said, Abubakar, Umar Nurmagomedov also in DB
        fid = get_fighter_id(conn, "nurmagomedov", first_name="khabib")
        assert get_record(conn, fid) == (13, 0, 0, 0), "Khabib should be 13-0"

    def test_conor_mcgregor_10_4_0_0(self, conn):
        fid = get_fighter_id(conn, "mcgregor")
        assert get_record(conn, fid) == (10, 4, 0, 0), "McGregor should be 10-4"

    def test_jon_jones_22_1_0_1(self, conn):
        # Must specify first name — other fighters named Jones exist
        fid = get_fighter_id(conn, "jones", first_name="jon")
        w, l, d, nc = get_record(conn, fid)
        assert w == 22,  f"Jones wins: expected 22, got {w}"
        assert l == 1,   f"Jones losses: expected 1 (DQ vs Hamill), got {l}"
        assert d == 0,   f"Jones draws: expected 0, got {d}"
        assert nc == 1,  f"Jones NCs: expected 1 (Cormier 2 overturned), got {nc}"

    def test_petr_yan_12_4_0_0(self, conn):
        fid = get_fighter_id(conn, "yan", first_name="petr")
        assert get_record(conn, fid) == (12, 4, 0, 0), "Petr Yan should be 12-4"

    def test_georges_st_pierre_20_2_0_0(self, conn):
        fid = get_fighter_id(conn, "st-pierre")
        w, l, d, nc = get_record(conn, fid)
        assert w == 20, f"GSP wins: expected 20, got {w}"
        assert l == 2,  f"GSP losses: expected 2, got {l}"

    def test_anderson_silva_17_7_0_1(self, conn):
        fid = get_fighter_id(conn, "silva", first_name="anderson")
        w, l, d, nc = get_record(conn, fid)
        assert w == 17, f"Silva wins: expected 17, got {w}"
        assert l == 7,  f"Silva losses: expected 7, got {l}"
        assert nc == 1, f"Silva NCs: expected 1 (Sonnen 2 PED), got {nc}"

    def test_amanda_nunes_16_2_0_0(self, conn):
        fid = get_fighter_id(conn, "nunes", first_name="amanda")
        assert get_record(conn, fid) == (16, 2, 0, 0), "Nunes should be 16-2"

    def test_demetrious_johnson_15_2_1_0(self, conn):
        # Losses: Cruz (2011), Cejudo 2 (2018). Draw: Ian McCall (2012). Dodson fights were both wins.
        fid = get_fighter_id(conn, "johnson", first_name="demetrious")
        w, l, d, nc = get_record(conn, fid)
        assert w == 15, f"DJ wins: expected 15, got {w}"
        assert l == 2,  f"DJ losses: expected 2 (Cruz, Cejudo 2), got {l}"
        assert d == 1,  f"DJ draws: expected 1 (Ian McCall majority draw), got {d}"


# ---------------------------------------------------------------------------
# Section 2 — Fight-Level Spot Checks
# From docs/sanity-check.md Part 2.
# ---------------------------------------------------------------------------

class TestFightSpotChecks:
    """Verify OUTCOME, winner, and FK assignment for specific famous fights."""

    def _fetch_fight(self, conn, name_a, name_b):
        """Return list of fight_results rows matching both names in BOUT."""
        return conn.execute(text("""
            SELECT
                fr."BOUT",
                fr."OUTCOME",
                fr.is_winner,
                fw."FIRST" || ' ' || fw."LAST" AS winner_name,
                fo."FIRST" || ' ' || fo."LAST" AS loser_name,
                ev.date_proper
            FROM fight_results fr
            JOIN fight_details  fd ON fd.id = fr.fight_id
            JOIN fighter_details fw ON fw.id = fr.fighter_id
            JOIN fighter_details fo ON fo.id = fr.opponent_id
            JOIN event_details   ev ON ev.id = fr.event_id
            WHERE fr."BOUT" LIKE :a AND fr."BOUT" LIKE :b
            ORDER BY ev.date_proper DESC
        """), {"a": f"%{name_a}%", "b": f"%{name_b}%"}).fetchall()

    def test_mcgregor_khabib_khabib_wins(self, conn):
        """UFC 229 — Khabib beat McGregor by Sub R4."""
        rows = self._fetch_fight(conn, "Khabib", "McGregor")
        assert rows, "McGregor vs Khabib fight not found"
        latest = rows[0]
        # Khabib is listed first in BOUT so OUTCOME is W/L
        assert latest[1] == "W/L", f"OUTCOME should be W/L (Khabib listed first), got {latest[1]}"
        assert "Khabib" in latest[3], f"Winner should be Khabib, got {latest[3]}"

    def test_jones_hamill_dq_jones_loses(self, conn):
        """Jones vs Hamill — Jones DQ'd, only loss on record."""
        rows = self._fetch_fight(conn, "Jones", "Hamill")
        assert rows, "Jones vs Hamill fight not found"
        row = rows[0]
        assert "Hamill" in row[3], f"Hamill should be winner (DQ), got {row[3]}"
        assert "Jones" in row[4],  f"Jones should be loser (DQ), got {row[4]}"

    def test_nunes_rousey_nunes_wins(self, conn):
        """UFC 207 — Nunes KO'd Rousey R1."""
        rows = self._fetch_fight(conn, "Nunes", "Rousey")
        assert rows, "Nunes vs Rousey fight not found"
        assert "Nunes" in rows[0][3], f"Nunes should be winner, got {rows[0][3]}"

    def test_silva_weidman_2013_silva_loses(self, conn):
        """UFC 162 — Weidman KO'd Silva R2."""
        rows = self._fetch_fight(conn, "Silva", "Weidman")
        assert rows, "Silva vs Weidman fight not found"
        # 2013 fight — get the earliest one
        earliest = rows[-1]
        assert "Weidman" in earliest[3], f"Weidman should be winner, got {earliest[3]}"

    def test_johnson_mccall_draw(self, conn):
        """DJ vs Ian McCall 1 (UFC on FX 2, Mar 2012) — majority draw, is_winner=FALSE.
        Note: both DJ vs Dodson fights were Johnson wins. The draw was vs McCall."""
        rows = conn.execute(text("""
            SELECT fr."BOUT", fr."OUTCOME", fr.is_winner
            FROM fight_results fr
            WHERE fr."BOUT" LIKE '%Johnson%' AND fr."BOUT" LIKE '%McCall%'
              AND fr."OUTCOME" = 'D/D'
        """)).fetchall()
        assert rows, "Johnson vs McCall draw not found"
        for r in rows:
            assert r[2] is False or r[2] == False, \
                f"is_winner should be FALSE for draw, got {r[2]}"

    def test_cormier_jones2_nc(self, conn):
        """Cormier vs Jones 2 — OUTCOME=NC/NC after positive test."""
        rows = conn.execute(text("""
            SELECT fr."OUTCOME", fr.is_winner
            FROM fight_results fr
            WHERE fr."BOUT" LIKE '%Jones%' AND fr."BOUT" LIKE '%Cormier%'
              AND fr."OUTCOME" = 'NC/NC'
        """)).fetchall()
        assert rows, "Jones vs Cormier NC not found"
        for r in rows:
            assert r[1] is False or r[1] == False, \
                f"is_winner should be FALSE for NC, got {r[1]}"


# ---------------------------------------------------------------------------
# Section 3 — FK Coverage Thresholds
# From docs/sanity-check.md Part 3.
# ---------------------------------------------------------------------------

class TestFKCoverage:
    """FK population completeness checks."""

    def test_fight_details_fighter_a_id_coverage(self, conn):
        """fighter_a_id should be ≥ 99.5% populated (excluding placeholder bouts)."""
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(fighter_a_id) AS populated
            FROM fight_details
            WHERE "BOUT" NOT LIKE '%win vs.%'
              AND "BOUT" NOT LIKE '%draw vs.%'
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct >= 99.5, f"fight_details.fighter_a_id coverage: {pct:.2f}% (< 99.5%)"

    def test_fight_details_fighter_b_id_coverage(self, conn):
        """fighter_b_id should be ≥ 99.5% populated (excluding placeholder bouts)."""
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(fighter_b_id) AS populated
            FROM fight_details
            WHERE "BOUT" NOT LIKE '%win vs.%'
              AND "BOUT" NOT LIKE '%draw vs.%'
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct >= 99.5, f"fight_details.fighter_b_id coverage: {pct:.2f}% (< 99.5%)"

    def test_fight_results_fighter_id_100pct(self, conn):
        """fight_results.fighter_id should be 100% populated."""
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fighter_id) AS populated
            FROM fight_results
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct == 100.0, f"fight_results.fighter_id coverage: {pct:.2f}% (expected 100%)"

    def test_fight_results_opponent_id_100pct(self, conn):
        """fight_results.opponent_id should be 100% populated."""
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(opponent_id) AS populated
            FROM fight_results
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct == 100.0, f"fight_results.opponent_id coverage: {pct:.2f}% (expected 100%)"

    def test_event_id_coverage_fight_details(self, conn):
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(event_id) AS populated
            FROM fight_details
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct == 100.0, f"fight_details.event_id: {pct:.2f}%"

    def test_event_id_coverage_fight_results(self, conn):
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(event_id) AS populated
            FROM fight_results
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct == 100.0, f"fight_results.event_id: {pct:.2f}%"

    def test_event_id_coverage_fight_stats(self, conn):
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(event_id) AS populated
            FROM fight_stats
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct == 100.0, f"fight_stats.event_id: {pct:.2f}%"

    def test_fight_stats_fight_id_coverage(self, conn):
        """fight_stats.fight_id should be ≥ 99.9% (full coverage achieved in Task 3.3)."""
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fight_id) AS populated
            FROM fight_stats
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct >= 99.9, f"fight_stats.fight_id coverage: {pct:.2f}% (< 99.9%)"

    def test_fight_stats_fighter_id_coverage(self, conn):
        """fight_stats.fighter_id should be ≥ 99.8% (42 unfixable NULLs where FIGHTER='None')."""
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fighter_id) AS populated
            FROM fight_stats
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct >= 99.8, f"fight_stats.fighter_id coverage: {pct:.2f}% (< 99.8%)"

    def test_fighter_tott_fighter_id_coverage(self, conn):
        """fighter_tott.fighter_id should be ≥ 99.5%."""
        row = conn.execute(text("""
            SELECT COUNT(*) AS total, COUNT(fighter_id) AS populated
            FROM fighter_tott
        """)).fetchone()
        pct = 100.0 * row[1] / row[0] if row[0] else 0
        assert pct >= 99.5, f"fighter_tott.fighter_id coverage: {pct:.2f}% (< 99.5%)"


# ---------------------------------------------------------------------------
# Section 4 — Parsed Column Sanity
# Verify Task 3.4, 3.5, 3.6 output is in range and non-null where expected.
# ---------------------------------------------------------------------------

class TestParsedColumns:
    """Range checks and coverage checks for Task 3.5/3.6 derived columns."""

    # --- fight_results parsed cols ---

    def test_fight_time_seconds_range(self, conn):
        """fight_time_seconds should be 1–3600.
        Early UFC (1993-2001) had no time limits or very long rounds (15–20 min),
        so values above 300 are legitimate for round 1 of those events."""
        row = conn.execute(text("""
            SELECT MIN(fight_time_seconds), MAX(fight_time_seconds)
            FROM fight_results
            WHERE fight_time_seconds IS NOT NULL
        """)).fetchone()
        assert row[0] >= 1,    f"fight_time_seconds min is {row[0]} (expected >= 1)"
        assert row[1] <= 3600, f"fight_time_seconds max is {row[1]} (expected <= 3600)"

    def test_total_fight_time_seconds_range(self, conn):
        """total_fight_time_seconds should be ≥ 1 and ≤ 1500 (5×300 = 5 full rounds)."""
        row = conn.execute(text("""
            SELECT MIN(total_fight_time_seconds), MAX(total_fight_time_seconds)
            FROM fight_results
            WHERE total_fight_time_seconds IS NOT NULL
        """)).fetchone()
        assert row[0] >= 1,    f"total_fight_time_seconds min is {row[0]}"
        assert row[1] <= 1500, f"total_fight_time_seconds max is {row[1]} (expected ≤ 1500)"

    def test_weight_class_no_nulls(self, conn):
        """weight_class should be populated for every fight_results row."""
        null_count = conn.execute(text("""
            SELECT COUNT(*) FROM fight_results WHERE weight_class IS NULL
        """)).scalar()
        assert null_count == 0, f"{null_count} fight_results rows have NULL weight_class"

    def test_weight_class_known_values_only(self, conn):
        """weight_class must only contain canonical class names."""
        valid = {
            "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight",
            "Women's Featherweight", "Light Heavyweight", "Super Heavyweight",
            "Heavyweight", "Middleweight", "Welterweight", "Lightweight",
            "Featherweight", "Bantamweight", "Flyweight", "Catch Weight", "Open Weight",
        }
        rows = conn.execute(text("""
            SELECT DISTINCT weight_class FROM fight_results
        """)).fetchall()
        unknowns = {r[0] for r in rows} - valid
        assert not unknowns, f"Unexpected weight_class values: {unknowns}"

    def test_is_title_fight_not_null(self, conn):
        """is_title_fight should be populated for every fight_results row."""
        null_count = conn.execute(text("""
            SELECT COUNT(*) FROM fight_results
            WHERE is_title_fight IS NULL AND "WEIGHTCLASS" IS NOT NULL
        """)).scalar()
        assert null_count == 0, f"{null_count} rows have NULL is_title_fight"

    def test_is_championship_rounds_vs_title_fight(self, conn):
        """is_championship_rounds count should be ≥ is_title_fight count
        (main events are 5 rounds even without a title)."""
        row = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE is_championship_rounds) AS champ,
                COUNT(*) FILTER (WHERE is_title_fight)         AS title
            FROM fight_results
        """)).fetchone()
        assert row[0] >= row[1], (
            f"is_championship_rounds ({row[0]}) < is_title_fight ({row[1]}); unexpected"
        )

    def test_khabib_mcgregor_derived_columns(self, conn):
        """Khabib vs McGregor should be Lightweight title fight with championship rounds."""
        row = conn.execute(text("""
            SELECT weight_class, is_title_fight, is_championship_rounds
            FROM fight_results
            WHERE "BOUT" LIKE '%Khabib%' AND "BOUT" LIKE '%McGregor%'
        """)).fetchone()
        assert row is not None, "Khabib vs McGregor fight not found"
        assert row[0] == "Lightweight", f"weight_class: expected Lightweight, got {row[0]}"
        assert row[1] is True,          f"is_title_fight: expected True, got {row[1]}"
        assert row[2] is True,          f"is_championship_rounds: expected True, got {row[2]}"

    def test_method_no_trailing_spaces(self, conn):
        """Task 3.4: METHOD should have no trailing spaces after quality_cleanup."""
        count = conn.execute(text("""
            SELECT COUNT(*) FROM fight_results
            WHERE "METHOD" != TRIM("METHOD") AND "METHOD" IS NOT NULL
        """)).scalar()
        assert count == 0, f"{count} fight_results rows still have trailing spaces in METHOD"

    # --- fight_stats parsed cols ---

    def test_sig_str_pct_range(self, conn):
        """sig_str_pct should be 0–100 (it's a percentage, stored as 0–100 numeric)."""
        row = conn.execute(text("""
            SELECT MIN(sig_str_pct), MAX(sig_str_pct)
            FROM fight_stats
            WHERE sig_str_pct IS NOT NULL
        """)).fetchone()
        assert row[0] >= 0,   f"sig_str_pct min is {row[0]}"
        assert row[1] <= 100, f"sig_str_pct max is {row[1]}"

    def test_ctrl_seconds_non_negative(self, conn):
        """ctrl_seconds should be ≥ 0."""
        min_val = conn.execute(text("""
            SELECT MIN(ctrl_seconds) FROM fight_stats WHERE ctrl_seconds IS NOT NULL
        """)).scalar()
        assert min_val >= 0, f"ctrl_seconds has negative value: {min_val}"

    def test_kd_int_non_negative(self, conn):
        """kd_int should be ≥ 0."""
        min_val = conn.execute(text("""
            SELECT MIN(kd_int) FROM fight_stats WHERE kd_int IS NOT NULL
        """)).scalar()
        assert min_val >= 0, f"kd_int has negative value: {min_val}"

    def test_sig_str_landed_lte_attempted(self, conn):
        """sig_str_landed should never exceed sig_str_attempted."""
        bad = conn.execute(text("""
            SELECT COUNT(*) FROM fight_stats
            WHERE sig_str_landed > sig_str_attempted
              AND sig_str_landed IS NOT NULL
        """)).scalar()
        assert bad == 0, f"{bad} rows have sig_str_landed > sig_str_attempted"

    def test_td_landed_lte_attempted(self, conn):
        """td_landed should never exceed td_attempted."""
        bad = conn.execute(text("""
            SELECT COUNT(*) FROM fight_stats
            WHERE td_landed > td_attempted AND td_landed IS NOT NULL
        """)).scalar()
        assert bad == 0, f"{bad} rows have td_landed > td_attempted"

    # --- fighter_tott parsed cols ---

    def test_height_inches_range(self, conn):
        """height_inches should be 48–90 inches (4'0\" to 7'6\")."""
        row = conn.execute(text("""
            SELECT MIN(height_inches), MAX(height_inches)
            FROM fighter_tott
            WHERE height_inches IS NOT NULL
        """)).fetchone()
        assert row[0] >= 48, f"height_inches min is {row[0]} (< 48in = 4'0\")"
        assert row[1] <= 90, f"height_inches max is {row[1]} (> 90in = 7'6\")"

    def test_weight_lbs_range(self, conn):
        """weight_lbs should be 100–350 lbs (flyweight to super heavyweight)."""
        row = conn.execute(text("""
            SELECT MIN(weight_lbs), MAX(weight_lbs)
            FROM fighter_tott
            WHERE weight_lbs IS NOT NULL
        """)).fetchone()
        assert row[0] >= 100, f"weight_lbs min is {row[0]}"
        assert row[1] <= 350, f"weight_lbs max is {row[1]}"

    def test_reach_inches_range(self, conn):
        """reach_inches should be 40–90 inches."""
        row = conn.execute(text("""
            SELECT MIN(reach_inches), MAX(reach_inches)
            FROM fighter_tott
            WHERE reach_inches IS NOT NULL
        """)).fetchone()
        assert row[0] >= 40, f"reach_inches min is {row[0]}"
        assert row[1] <= 90, f"reach_inches max is {row[1]}"

    def test_dob_date_range(self, conn):
        """dob_date should be between 1950 and 2005 (fighters in UFC)."""
        row = conn.execute(text("""
            SELECT MIN(dob_date), MAX(dob_date)
            FROM fighter_tott
            WHERE dob_date IS NOT NULL
        """)).fetchone()
        assert str(row[0]) >= "1950-01-01", f"dob_date min is {row[0]}"
        assert str(row[1]) <= "2006-01-01", f"dob_date max is {row[1]}"

    def test_fighter_tott_no_dash_placeholders(self, conn):
        """Task 3.4: '--' placeholders should be gone from fighter_tott."""
        for col in ["HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB"]:
            count = conn.execute(text(f"""
                SELECT COUNT(*) FROM fighter_tott
                WHERE "{col}" IN ('--', '---', '')
            """)).scalar()
            assert count == 0, f"fighter_tott.{col} still has {count} '--' placeholders"

    def test_fight_stats_no_dash_placeholders(self, conn):
        """Task 3.4: '--' placeholders should be gone from fight_stats."""
        for col in ["SIG.STR. %", "TD %", "CTRL"]:
            count = conn.execute(text(f"""
                SELECT COUNT(*) FROM fight_stats
                WHERE "{col}" IN ('--', '---', '')
            """)).scalar()
            assert count == 0, f"fight_stats.{col} still has {count} '--' placeholders"


# ---------------------------------------------------------------------------
# Section 5 — Row Count Sanity
# Catch accidental truncation or double-loads.
# ---------------------------------------------------------------------------

class TestRowCounts:
    """Minimum row count guards — catch accidental data loss."""

    def test_event_details_minimum(self, conn):
        count = conn.execute(text("SELECT COUNT(*) FROM event_details")).scalar()
        assert count >= 750, f"event_details has only {count} rows (expected ≥ 750)"

    def test_fighter_details_minimum(self, conn):
        count = conn.execute(text("SELECT COUNT(*) FROM fighter_details")).scalar()
        assert count >= 4400, f"fighter_details has only {count} rows (expected ≥ 4400)"

    def test_fight_results_minimum(self, conn):
        count = conn.execute(text("SELECT COUNT(*) FROM fight_results")).scalar()
        assert count >= 8000, f"fight_results has only {count} rows (expected ≥ 8000)"

    def test_fight_stats_minimum(self, conn):
        count = conn.execute(text("SELECT COUNT(*) FROM fight_stats")).scalar()
        assert count >= 39000, f"fight_stats has only {count} rows (expected ≥ 39000)"

    def test_fighter_tott_minimum(self, conn):
        count = conn.execute(text("SELECT COUNT(*) FROM fighter_tott")).scalar()
        assert count >= 4400, f"fighter_tott has only {count} rows (expected ≥ 4400)"
