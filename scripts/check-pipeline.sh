#!/usr/bin/env bash
# check-pipeline.sh - Would the weekly pipeline still run against today's data?
#
# Runs every pipeline gate that can be exercised without writing to the
# database, against the real database:
#   1. unit tests (no database)
#   2. data quality tests (read-only)
#   3. validate_etl.py - the exact gate the Post-Scrape ETL blocks on
#   4. the prediction archive, as a dry run
#   5. the pipeline health check
#
# Run by the Pipeline Check workflow on every push and pull request, and by
# the pre-push hook in .githooks/ (enable once per clone with
#   git config core.hooksPath .githooks).
#
# Needs DATABASE_URL, from the environment or backend/.env.

set -euo pipefail

cd "$(dirname "$0")/../backend"

step() { printf '\n==> %s\n' "$1"; }

step "Unit tests"
python -m pytest scraper/tests -q

step "Data quality tests"
python -m pytest tests -q

step "ETL validation gate"
python scraper/validate_etl.py

step "Prediction archive (dry run)"
python scraper/archive_completed_predictions.py --dry-run

step "Pipeline health"
python scraper/check_pipeline_health.py

printf '\nPipeline check passed.\n'
