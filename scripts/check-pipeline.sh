#!/usr/bin/env bash
# check-pipeline.sh - Would the weekly pipeline still run against today's data?
#
# Runs every pipeline gate that can be exercised without writing to the
# database, against the real database:
#   1. unit tests (no database)
#   2. every workflow step that pushes to main, replayed against a scratch
#      remote where main has moved and the job left tracked files dirty
#   3. data quality tests (read-only)
#   4. validate_etl.py - the exact gate the Post-Scrape ETL blocks on
#   5. the prediction archive, as a dry run
#   6. the pipeline health check
#
# Run by the Pipeline Check workflow on every push and pull request, and by
# the pre-push hook in .githooks/ (enable once per clone with
#   git config core.hooksPath .githooks).
#
# Needs DATABASE_URL, from the environment or backend/.env.

set -euo pipefail

# Under a git hook on Windows, stdout is a pipe and Python falls back to
# cp1252, printing the validation marks as ✓ escapes.
export PYTHONUTF8=1

cd "$(dirname "$0")/../backend"

step() { printf '\n==> %s\n' "$1"; }

step "Unit tests"
python -m pytest scraper/tests -q

step "Workflow bot pushes"
python -m pytest ../scripts/tests -q

step "Data quality tests"
python -m pytest tests -q

step "ETL validation gate"
python scraper/validate_etl.py

step "Prediction archive (dry run)"
python scraper/archive_completed_predictions.py --dry-run

step "Pipeline health"
python scraper/check_pipeline_health.py

printf '\nPipeline check passed.\n'
