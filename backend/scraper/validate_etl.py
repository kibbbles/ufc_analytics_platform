"""
validate_etl.py — Post-ETL data quality validation (Task 3.10)

Runs a suite of checks against the Supabase database to verify that all
ETL phases completed correctly and data quality thresholds are met.

Outputs a timestamped JSON report to backend/scraper/reports/.
Exits with code 0 if all checks pass, 1 if any check fails.
INFO-only checks never contribute to a failure.

Usage:
    python backend/scraper/validate_etl.py
    python backend/scraper/validate_etl.py --report-dir /custom/path
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timezone

_HERE    = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from sqlalchemy import text
from db.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("validate_etl")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANONICAL_WEIGHT_CLASSES = {
    "Women's Strawweight", "Women's Flyweight", "Women's Bantamweight",
    "Women's Featherweight", "Light Heavyweight", "Super Heavyweight",
    "Heavyweight", "Middleweight", "Welterweight", "Lightweight",
    "Featherweight", "Bantamweight", "Flyweight", "Catch Weight", "Open Weight",
}

DASH_PLACEHOLDERS = ("'--'", "'---'", "''")

# Columns checked for '--' placeholder removal (Task 3.4 scope)
DASH_CHECK_COLS = {
    "fighter_tott": ["HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB"],
    "fight_stats":  ["SIG.STR. %", "TD %", "CTRL"],
}

# Division ladder, low to high. Used by the identity-integrity oscillation
# check: a fighter moving up or down the ladder is normal, a fighter who drops
# several rungs and then climbs back is two people merged into one row.
DIVISION_LADDER = {
    "Strawweight": 0, "Flyweight": 1, "Bantamweight": 2, "Featherweight": 3,
    "Lightweight": 4, "Welterweight": 5, "Middleweight": 6,
    "Light Heavyweight": 7, "Heavyweight": 8,
    "Women's Strawweight": 0, "Women's Flyweight": 1,
    "Women's Bantamweight": 2, "Women's Featherweight": 3,
}

# A drop of this many divisions followed by a return upward is treated as a
# merged identity. Tuned against the real data: at 3 it isolates the known
# Bruno Silva merge with no false positives, while 2 also flags legitimate
# journeymen (Diego Sanchez, Jeff Monson, Kevin Jackson).
OSCILLATION_DIVISIONS = 3

# Whether identity-integrity failures fail the pipeline.
#
# These checks currently find 65 real violations (16 shared names, 13 duplicate
# URLs, 4 unreachable rows, 20 duplicate tott rows, 12 orphaned fighters, 1
# weight-class oscillation). Making them blocking before that data is repaired
# would fail post_scrape_clean.py every Sunday, which skips archive-predictions
# and stops feature-engineering, retrain and deploy from running at all.
#
# So they report as INFO until the identity repair lands. Flip this to True as
# the last step of that repair - it then becomes the regression guard that stops
# the merge bug from ever coming back.
IDENTITY_CHECKS_BLOCKING = False


def _identity_threshold_type():
    return "max_count" if IDENTITY_CHECKS_BLOCKING else "info"

# One-night tournaments ran through 1999, so a fighter legitimately appears
# twice on those cards. Anything after this date is a duplicate-identity bug.
TOURNAMENT_ERA_END = "2000-01-01"

# Minimum row counts — catching accidental truncation
MIN_ROW_COUNTS = {
    "event_details":   750,
    "fighter_details": 4_400,
    "fight_details":   8_400,
    "fight_results":   8_400,
    "fight_stats":     39_000,
    "fighter_tott":    4_400,
}


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _pct(populated, total):
    return round(100.0 * populated / total, 2) if total else 0.0


class CheckResult:
    """Represents one validation check."""

    SYMBOLS = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "INFO": "i"}

    def __init__(self, name, value, threshold, threshold_type, detail=""):
        """
        threshold_type:
            min_pct   — value (percentage) must be >= threshold to pass
            min_count — value (integer)    must be >= threshold to pass
            max_count — value (integer)    must be <= threshold to pass
            info      — informational only, never fails
        """
        self.name           = name
        self.value          = value
        self.threshold      = threshold
        self.threshold_type = threshold_type
        self.detail         = detail
        self.status         = self._evaluate()

    def _evaluate(self):
        if self.threshold_type == "info":
            return "INFO"
        if self.threshold_type in ("min_pct", "min_count"):
            return "PASS" if self.value >= self.threshold else "FAIL"
        if self.threshold_type == "max_count":
            return "PASS" if self.value <= self.threshold else "FAIL"
        return "UNKNOWN"

    def log(self):
        sym = self.SYMBOLS.get(self.status, "?")
        log.info(f"  {sym}  {self.name}: {self.value}  (threshold: {self.threshold}) → {self.status}")
        if self.detail:
            log.info(f"       {self.detail}")

    def to_dict(self):
        return {
            "name":           self.name,
            "value":          self.value,
            "threshold":      self.threshold,
            "threshold_type": self.threshold_type,
            "status":         self.status,
            "detail":         self.detail,
        }


# ---------------------------------------------------------------------------
# Individual check groups
# ---------------------------------------------------------------------------

def check_fk_completeness(conn):
    results = []
    log.info("\n  [FK Completeness]")

    # fight_details — fighter_a_id / fighter_b_id (exclude placeholder rows)
    for col in ("fighter_a_id", "fighter_b_id"):
        row = conn.execute(text(f"""
            SELECT COUNT(*) AS total, COUNT({col}) AS pop
            FROM fight_details
            WHERE "BOUT" NOT LIKE '%win vs.%'
              AND "BOUT" NOT LIKE '%draw vs.%'
        """)).fetchone()
        pct = _pct(row[1], row[0])
        r = CheckResult(
            f"fight_details.{col} completeness",
            pct, 99.5, "min_pct",
            f"{row[1]:,}/{row[0]:,} rows populated"
        )
        r.log(); results.append(r)

    # fight_results — fighter_id / opponent_id
    for col in ("fighter_id", "opponent_id"):
        row = conn.execute(text(f"""
            SELECT COUNT(*) AS total, COUNT({col}) AS pop FROM fight_results
        """)).fetchone()
        pct = _pct(row[1], row[0])
        r = CheckResult(
            f"fight_results.{col} completeness",
            pct, 99.5, "min_pct",
            f"{row[1]:,}/{row[0]:,} rows populated"
        )
        r.log(); results.append(r)

    # fight_stats — fighter_id / fight_id
    for col, threshold in [("fighter_id", 90.0), ("fight_id", 99.9)]:
        row = conn.execute(text(f"""
            SELECT COUNT(*) AS total, COUNT({col}) AS pop FROM fight_stats
        """)).fetchone()
        pct = _pct(row[1], row[0])
        r = CheckResult(
            f"fight_stats.{col} completeness",
            pct, threshold, "min_pct",
            f"{row[1]:,}/{row[0]:,} rows populated"
        )
        r.log(); results.append(r)

    # fighter_tott — fighter_id
    row = conn.execute(text("""
        SELECT COUNT(*) AS total, COUNT(fighter_id) AS pop FROM fighter_tott
    """)).fetchone()
    pct = _pct(row[1], row[0])
    r = CheckResult(
        "fighter_tott.fighter_id completeness",
        pct, 99.5, "min_pct",
        f"{row[1]:,}/{row[0]:,} rows populated"
    )
    r.log(); results.append(r)

    return results


def check_quality_cleanup(conn):
    results = []
    log.info("\n  [Quality Cleanup]")

    # '--' placeholders gone from fighter_tott and fight_stats
    for table, cols in DASH_CHECK_COLS.items():
        for col in cols:
            count = conn.execute(text(f"""
                SELECT COUNT(*) FROM {table}
                WHERE "{col}" IN ('--', '---', '')
            """)).scalar()
            r = CheckResult(
                f"{table}.{col} — zero dash placeholders",
                count, 0, "max_count",
                f"{count} rows still have '--' / '---' values"
            )
            r.log(); results.append(r)

    # No trailing spaces in METHOD
    trailing = conn.execute(text("""
        SELECT COUNT(*) FROM fight_results
        WHERE "METHOD" != TRIM("METHOD") AND "METHOD" IS NOT NULL
    """)).scalar()
    r = CheckResult(
        "fight_results.METHOD — no trailing spaces",
        trailing, 0, "max_count",
        f"{trailing} rows have untrimmed METHOD"
    )
    r.log(); results.append(r)

    # No embedded newlines in fight_stats stat columns — catches scraper merge bug
    newline_count = conn.execute(text(r"""
        SELECT COUNT(*) FROM fight_stats
        WHERE "KD" LIKE E'%\n%'
    """)).scalar()
    r = CheckResult(
        "fight_stats.KD — no embedded newlines (scraper merge check)",
        newline_count, 0, "max_count",
        f"{newline_count} rows have newline-merged values"
    )
    r.log(); results.append(r)

    return results


def check_derived_columns(conn):
    results = []
    log.info("\n  [Derived Columns]")

    # weight_class contains only canonical values
    rows = conn.execute(text("""
        SELECT DISTINCT weight_class FROM fight_results
        WHERE weight_class IS NOT NULL
    """)).fetchall()
    unknowns = {r[0] for r in rows} - CANONICAL_WEIGHT_CLASSES
    r = CheckResult(
        "weight_class — canonical values only",
        len(unknowns), 0, "max_count",
        f"Unknown values: {unknowns}" if unknowns else "All values canonical"
    )
    r.log(); results.append(r)

    # is_title_fight not NULL where WEIGHTCLASS is known
    null_tf = conn.execute(text("""
        SELECT COUNT(*) FROM fight_results
        WHERE is_title_fight IS NULL AND "WEIGHTCLASS" IS NOT NULL
    """)).scalar()
    r = CheckResult(
        "is_title_fight — no NULLs where WEIGHTCLASS known",
        null_tf, 0, "max_count",
        f"{null_tf} rows have NULL is_title_fight"
    )
    r.log(); results.append(r)

    # is_championship_rounds >= is_title_fight (5-round main events)
    row = conn.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE is_championship_rounds) AS champ,
            COUNT(*) FILTER (WHERE is_title_fight)         AS title
        FROM fight_results
    """)).fetchone()
    champ, title = row[0], row[1]
    r = CheckResult(
        "is_championship_rounds >= is_title_fight count",
        champ, title, "min_count",
        f"championship_rounds={champ:,}  title_fights={title:,}"
    )
    r.log(); results.append(r)

    # fight_bonus: informational (not tracked on UFCStats)
    has_bonus_col = conn.execute(text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'fight_results' AND column_name = 'fight_bonus'
    """)).scalar()
    detail = (
        "fight_bonus column not present — bonuses not tracked on UFCStats.com"
        if not has_bonus_col else "fight_bonus column present (informational)"
    )
    r = CheckResult("fight_bonus distribution", 0, 0, "info", detail)
    r.log(); results.append(r)

    return results


def check_type_parsing(conn):
    results = []
    log.info("\n  [Type Parsing Coverage]")

    fs_total = conn.execute(text("SELECT COUNT(*) FROM fight_stats")).scalar()
    for col, threshold in [
        ("sig_str_landed", 80.0),
        ("ctrl_seconds",   40.0),   # CTRL absent in many older fights
        ("kd_int",         80.0),
        ("sig_str_pct",    80.0),
    ]:
        pop = conn.execute(text(f"SELECT COUNT({col}) FROM fight_stats")).scalar()
        pct = _pct(pop, fs_total)
        r = CheckResult(
            f"fight_stats.{col} parsed coverage",
            pct, threshold, "min_pct",
            f"{pop:,}/{fs_total:,} rows"
        )
        r.log(); results.append(r)

    fr_total = conn.execute(text("SELECT COUNT(*) FROM fight_results")).scalar()
    for col, threshold in [
        ("fight_time_seconds",       90.0),
        ("total_fight_time_seconds", 90.0),
    ]:
        pop = conn.execute(text(f"SELECT COUNT({col}) FROM fight_results")).scalar()
        pct = _pct(pop, fr_total)
        r = CheckResult(
            f"fight_results.{col} parsed coverage",
            pct, threshold, "min_pct",
            f"{pop:,}/{fr_total:,} rows"
        )
        r.log(); results.append(r)

    tott_total = conn.execute(text("SELECT COUNT(*) FROM fighter_tott")).scalar()
    for col, threshold in [
        ("height_inches", 80.0),
        ("weight_lbs",    80.0),
        ("reach_inches",  50.0),
        ("dob_date",      70.0),
    ]:
        pop = conn.execute(text(f"SELECT COUNT({col}) FROM fighter_tott")).scalar()
        pct = _pct(pop, tott_total)
        r = CheckResult(
            f"fighter_tott.{col} parsed coverage",
            pct, threshold, "min_pct",
            f"{pop:,}/{tott_total:,} rows"
        )
        r.log(); results.append(r)

    return results


def check_row_counts(conn):
    results = []
    log.info("\n  [Row Count Guards]")

    for table, minimum in MIN_ROW_COUNTS.items():
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        r = CheckResult(
            f"{table} — minimum row count",
            count, minimum, "min_count",
            f"{count:,} rows  (minimum {minimum:,})"
        )
        r.log(); results.append(r)

    return results


def check_identity_integrity(conn):
    """Correctness checks on fighter identity.

    Every other group in this file measures *coverage* - what fraction of rows
    got populated. Coverage cannot see the failure this group exists for: FK
    resolution keyed on fighter names, so when two fighters shared a name the
    lookup silently kept one and gave that id both careers. Coverage read 100%
    the whole time while 36 bouts sat under the wrong human being.

    So these are thresholded at zero, not at a percentage. A percentage gate is
    structurally blind here - 36 bad rows out of 8,847 passes any sane one.
    """
    results = []
    log.info("\n  [Identity Integrity]")

    # A name shared by two fighter rows is the precondition for the merge bug:
    # the resolver has to pick one, and it picks by heap order.
    rows = conn.execute(text("""
        SELECT lower(trim(coalesce("FIRST", '') || ' ' || coalesce("LAST", ''))) AS nm,
               COUNT(*) AS n
        FROM fighter_details
        WHERE trim(coalesce("FIRST", '') || ' ' || coalesce("LAST", '')) <> ''
        GROUP BY 1
        HAVING COUNT(*) > 1
        ORDER BY 2 DESC, 1
    """)).fetchall()
    r = CheckResult(
        "fighter_details - names shared by multiple fighters",
        len(rows), 0, _identity_threshold_type(),
        ", ".join(f"{nm} x{n}" for nm, n in rows[:6]) or "no shared names"
    )
    r.log(); results.append(r)

    # The UFCStats URL is the real identity. Two rows sharing one means a single
    # person's career is split in half.
    rows = conn.execute(text("""
        SELECT "URL", COUNT(*) AS n
        FROM fighter_details
        WHERE "URL" IS NOT NULL
        GROUP BY "URL"
        HAVING COUNT(*) > 1
        ORDER BY 2 DESC
    """)).fetchall()
    r = CheckResult(
        "fighter_details - duplicate UFCStats URLs",
        len(rows), 0, _identity_threshold_type(),
        f"{len(rows)} URL(s) claimed by more than one fighter row"
    )
    r.log(); results.append(r)

    # build_fighter_lookup() skips rows with an empty LAST, so these can never
    # receive an FK no matter how many times the ETL runs. Mononyms land here.
    rows = conn.execute(text("""
        SELECT id, "FIRST"
        FROM fighter_details
        WHERE coalesce("FIRST", '') <> '' AND coalesce("LAST", '') = ''
        ORDER BY "FIRST"
    """)).fetchall()
    r = CheckResult(
        "fighter_details - rows unreachable by name lookup",
        len(rows), 0, _identity_threshold_type(),
        ", ".join(f"{fid}:{nm}" for fid, nm in rows[:6]) or "all rows reachable"
    )
    r.log(); results.append(r)

    # Two tale-of-the-tape rows for one fighter means the tott linker collided
    # the same way the fight linker did.
    count = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fighter_id FROM fighter_tott
            WHERE fighter_id IS NOT NULL
            GROUP BY fighter_id HAVING COUNT(*) > 1
        ) t
    """)).scalar()
    r = CheckResult(
        "fighter_tott - fighters with duplicate rows",
        count, 0, _identity_threshold_type(),
        f"{count} fighter(s) with more than one tott row"
    )
    r.log(); results.append(r)

    # The detector that found this whole class: a fighter whose name appears in
    # a BOUT string but who owns no bouts. Their fights went to someone else.
    rows = conn.execute(text("""
        WITH sides AS (
            SELECT lower(trim(split_part("BOUT", ' vs. ', 1))) AS nm
            FROM fight_results WHERE "BOUT" LIKE :sep
            UNION
            SELECT lower(trim(split_part("BOUT", ' vs. ', 2)))
            FROM fight_results WHERE "BOUT" LIKE :sep
        ),
        linked AS (
            SELECT fighter_id AS id FROM fight_results WHERE fighter_id IS NOT NULL
            UNION
            SELECT opponent_id FROM fight_results WHERE opponent_id IS NOT NULL
        ),
        named AS (
            SELECT id, lower(trim(coalesce("FIRST", '') || ' ' || coalesce("LAST", ''))) AS nm
            FROM fighter_details
            WHERE trim(coalesce("FIRST", '') || ' ' || coalesce("LAST", '')) <> ''
        )
        SELECT n.id, n.nm
        FROM named n
        JOIN sides s ON s.nm = n.nm
        WHERE n.id NOT IN (SELECT id FROM linked)
        ORDER BY n.nm
    """), {"sep": "% vs. %"}).fetchall()
    r = CheckResult(
        "fight_results - fighters named in a bout but owning none",
        len(rows), 0, _identity_threshold_type(),
        ", ".join(f"{fid}:{nm}" for fid, nm in rows[:6]) or "no orphaned fighters"
    )
    r.log(); results.append(r)

    # Nobody fights twice on one card outside the tournament era. Two bouts on
    # one event for one id means two people wearing that id.
    count = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fr.event_id, x.fid
            FROM fight_results fr
            JOIN event_details e ON e.id = fr.event_id
            CROSS JOIN LATERAL (VALUES (fr.fighter_id), (fr.opponent_id)) AS x(fid)
            WHERE x.fid IS NOT NULL AND e.date_proper >= :cutoff
            GROUP BY 1, 2 HAVING COUNT(*) > 1
        ) t
    """), {"cutoff": TOURNAMENT_ERA_END}).scalar()
    r = CheckResult(
        "fight_results - fighter booked twice on one event",
        count, 0, _identity_threshold_type(),
        f"{count} fighter/event pair(s) after {TOURNAMENT_ERA_END}"
    )
    r.log(); results.append(r)

    # Weight-class oscillation. Measured in divisions, not pounds: a pound
    # threshold flags every legitimate 205/265 mover (Couture, Cormier, Pereira)
    # because heavyweight's 265 is a limit rather than a fighting weight.
    rows = conn.execute(text("""
        SELECT x.fid, fr.weight_class
        FROM fight_results fr
        JOIN event_details e ON e.id = fr.event_id
        CROSS JOIN LATERAL (VALUES (fr.fighter_id), (fr.opponent_id)) AS x(fid)
        WHERE x.fid IS NOT NULL AND fr.weight_class IS NOT NULL
        ORDER BY x.fid, e.date_proper
    """)).fetchall()

    career = {}
    for fid, wc in rows:
        if wc in DIVISION_LADDER:
            career.setdefault(fid, []).append(DIVISION_LADDER[wc])

    def _oscillates(divs):
        """True if the career drops OSCILLATION_DIVISIONS rungs, then returns."""
        for i in range(len(divs) - 1):
            for j in range(i + 1, len(divs)):
                if divs[i] - divs[j] < OSCILLATION_DIVISIONS:
                    continue
                if any(divs[k] >= divs[i] for k in range(j + 1, len(divs))):
                    return True
        return False

    offenders = [fid for fid, divs in career.items() if _oscillates(divs)]
    r = CheckResult(
        "fight_results - impossible weight-class oscillation",
        len(offenders), 0, _identity_threshold_type(),
        ", ".join(offenders[:6]) or
        f"no career drops {OSCILLATION_DIVISIONS}+ divisions and returns"
    )
    r.log(); results.append(r)

    return results


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

def run_validation():
    log.info("")
    log.info("=" * 70)
    log.info("  validate_etl.py — ETL Data Quality Validation")
    log.info("=" * 70)

    all_results = []

    with engine.connect() as conn:
        all_results += check_fk_completeness(conn)
        all_results += check_quality_cleanup(conn)
        all_results += check_derived_columns(conn)
        all_results += check_type_parsing(conn)
        all_results += check_row_counts(conn)
        all_results += check_identity_integrity(conn)

    passed  = sum(1 for r in all_results if r.status == "PASS")
    failed  = sum(1 for r in all_results if r.status == "FAIL")
    info    = sum(1 for r in all_results if r.status == "INFO")
    overall = "PASS" if failed == 0 else "FAIL"

    log.info("")
    log.info("=" * 70)
    log.info("  SUMMARY")
    log.info("=" * 70)
    log.info(f"  Passed:       {passed}")
    log.info(f"  Failed:       {failed}")
    log.info(f"  Informational:{info}")
    log.info(f"  Overall:      {overall}")

    identity = [r for r in all_results if r.status == "INFO"
                and r.threshold_type == "info" and isinstance(r.value, int)
                and r.value > 0 and " - " in r.name]
    if identity and not IDENTITY_CHECKS_BLOCKING:
        log.warning("")
        log.warning("  Identity-integrity violations (non-blocking, see "
                    "IDENTITY_CHECKS_BLOCKING):")
        for r in identity:
            log.warning(f"    !  {r.name}: {r.value}")

    if failed:
        log.error("\n  FAILED checks:")
        for r in all_results:
            if r.status == "FAIL":
                log.error(f"    ✗  {r.name}: {r.value} (threshold: {r.threshold})")

    return all_results, overall


def write_report(all_results, overall, report_dir):
    os.makedirs(report_dir, exist_ok=True)
    ts       = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"etl_validation_{ts}.json"
    path     = os.path.join(report_dir, filename)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall":   overall,
        "passed":    sum(1 for r in all_results if r.status == "PASS"),
        "failed":    sum(1 for r in all_results if r.status == "FAIL"),
        "info":      sum(1 for r in all_results if r.status == "INFO"),
        "checks":    [r.to_dict() for r in all_results],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    log.info(f"\n  Report written to: {path}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate ETL data quality after post_scrape_clean.py."
    )
    parser.add_argument(
        "--report-dir",
        default=os.path.join(_HERE, "reports"),
        help="Directory to write JSON report (default: backend/scraper/reports/)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    all_results, overall = run_validation()
    write_report(all_results, overall, args.report_dir)
    sys.exit(0 if overall == "PASS" else 1)


if __name__ == "__main__":
    main()
