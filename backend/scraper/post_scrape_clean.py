"""
post_scrape_clean.py — ETL orchestration script (Task 3.8)

Runs all four ETL cleanup phases in sequence after a scrape run.
Each phase calls into the same functions used by the individual scripts,
so all operations are idempotent (safe to re-run on already-processed data).

Phases
------
  1  FK Resolution    — populate fighter_a_id/b_id, winner/loser FKs,
                        and fight_stats.fighter_id
  2  Quality Cleanup  — NULL out '--' placeholders, strip METHOD spaces
  3  Type Parsing     — convert text columns to INTEGER/NUMERIC/DATE
  4  Derived Columns  — weight_class, is_title_fight, is_championship_rounds

Usage
-----
    # Run all phases (default)
    python backend/scraper/post_scrape_clean.py

    # Run a single phase (useful for debugging)
    python backend/scraper/post_scrape_clean.py --phase 2

    # Dry-run: show what would run without executing
    python backend/scraper/post_scrape_clean.py --dry-run

Environment
-----------
    DATABASE_URL  — Supabase connection string (read from .env via db.database)
"""

import sys
import os
import argparse
import logging
import time

# Ensure backend/ is on the path so db.database and sibling scraper modules
# are importable regardless of where this script is invoked from.
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# ---------------------------------------------------------------------------
# Logging — structured, with timestamps and phase labels
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("post_scrape_clean")


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------

def phase_1_fk_resolution():
    """Populate all FK columns across fight_details, fight_results, fight_stats."""
    from scraper.populate_fighter_fks import populate_fighter_a_b_ids
    from scraper.populate_result_fks import populate_result_fks
    from scraper.populate_stats_fighter_fks import populate_stats_fighter_fks

    populate_fighter_a_b_ids()   # fight_details.fighter_a_id / fighter_b_id
    populate_result_fks()        # fight_results.fighter_id / opponent_id / is_winner
    populate_stats_fighter_fks() # fight_stats.fighter_id


def phase_2_quality_cleanup():
    """Replace '--' placeholders with NULL; strip METHOD trailing spaces."""
    from scraper.quality_cleanup import run_quality_cleanup
    run_quality_cleanup()


def phase_3_type_parsing():
    """Parse text columns into INTEGER / NUMERIC / DATE typed columns."""
    from scraper.type_parsing import run_type_parsing
    run_type_parsing()


def phase_4_derived_columns():
    """Populate weight_class, is_title_fight, is_interim_title, is_championship_rounds."""
    from scraper.derived_columns import run_derived_columns
    run_derived_columns()


PHASES = {
    1: ("FK Resolution",    phase_1_fk_resolution),
    2: ("Quality Cleanup",  phase_2_quality_cleanup),
    3: ("Type Parsing",     phase_3_type_parsing),
    4: ("Derived Columns",  phase_4_derived_columns),
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_phase(phase_num, dry_run=False):
    """Run a single phase, wrapping it in timing + error handling.

    Returns True on success, False on failure.
    """
    name, fn = PHASES[phase_num]
    log.info("=" * 70)
    log.info(f"  PHASE {phase_num}: {name}")
    log.info("=" * 70)

    if dry_run:
        log.info(f"  [DRY RUN] Would execute phase {phase_num}: {name}")
        return True

    start = time.monotonic()
    try:
        fn()
        elapsed = time.monotonic() - start
        log.info(f"  Phase {phase_num} completed in {elapsed:.1f}s")
        return True
    except Exception as exc:
        elapsed = time.monotonic() - start
        log.error(f"  Phase {phase_num} FAILED after {elapsed:.1f}s: {exc}", exc_info=True)
        return False


def run(phases_to_run, dry_run=False):
    """Run the requested phases in order.

    Returns exit code: 0 = all passed, 1 = one or more phases failed.
    """
    log.info("")
    log.info("=" * 70)
    log.info("  post_scrape_clean.py  —  UFC Analytics ETL Pipeline")
    log.info("=" * 70)
    if dry_run:
        log.info("  Mode: DRY RUN (no DB changes)")
    log.info(f"  Phases to run: {phases_to_run}")
    log.info("")

    overall_start = time.monotonic()
    results = {}

    for phase_num in phases_to_run:
        success = run_phase(phase_num, dry_run=dry_run)
        results[phase_num] = success
        if not success:
            log.error(f"  Halting: phase {phase_num} failed.")
            break

    total_elapsed = time.monotonic() - overall_start

    # Summary
    log.info("")
    log.info("=" * 70)
    log.info("  SUMMARY")
    log.info("=" * 70)
    for phase_num, success in results.items():
        name = PHASES[phase_num][0]
        status = "OK" if success else "FAILED"
        log.info(f"  Phase {phase_num} ({name}): {status}")

    skipped = [p for p in phases_to_run if p not in results]
    for phase_num in skipped:
        name = PHASES[phase_num][0]
        log.info(f"  Phase {phase_num} ({name}): SKIPPED (prior failure)")

    log.info(f"  Total time: {total_elapsed:.1f}s")

    failed = any(not v for v in results.values())
    if failed:
        log.error("  Result: FAILED")
        return 1

    log.info("  Result: OK")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run UFC Analytics ETL cleanup phases after a scrape.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Phases:
  1  FK Resolution    — fighter_a_id, fighter_b_id, winner/loser FKs, fight_stats.fighter_id
  2  Quality Cleanup  — NULL out '--' placeholders, strip METHOD whitespace
  3  Type Parsing     — parse 'X of Y' strikes, CTRL time, height/weight/reach, fight time
  4  Derived Columns  — weight_class, is_title_fight, is_interim_title, is_championship_rounds
""",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=list(PHASES.keys()),
        help="Run only this phase (1–4). Omit to run all phases in sequence.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would run without executing any DB operations.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    phases = [args.phase] if args.phase else list(PHASES.keys())
    exit_code = run(phases, dry_run=args.dry_run)

    # Run data-quality validation after all ETL phases complete.
    # Only validate when all phases ran (no --phase flag) and not dry-running.
    if not args.dry_run and not args.phase:
        log.info("")
        log.info("=" * 70)
        log.info("  POST-ETL VALIDATION")
        log.info("=" * 70)
        try:
            from scraper.validate_etl import run_validation, write_report
            import os
            report_dir = os.path.join(_HERE, "reports")
            all_results, overall = run_validation()
            write_report(all_results, overall, report_dir)
            if overall != "PASS":
                log.error("  Validation FAILED — pipeline exiting with code 1")
                exit_code = 1
        except Exception as exc:
            log.error(f"  Validation script error: {exc}", exc_info=True)
            exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
