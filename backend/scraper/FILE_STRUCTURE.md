# Scraper Directory - File Structure

## Current Setup: GitHub Actions (Cloud-based Automation)

This directory contains the UFC scraper with automated GitHub Actions workflows.

---

## Python Files

### Core Scraping
- **`live_scraper.py`** - Main UFC scraper
  - Scrapes new events from UFCStats.com
  - Compares with existing database
  - Only adds NEW events (incremental updates)
  - Used by: Weekly GitHub Actions workflow

- **`keepalive_ping.py`** - Database keepalive
  - Simple daily database query
  - Prevents Supabase free tier from auto-pausing
  - Used by: Daily GitHub Actions workflow

### Database Integration
- **`database_integration.py`** - Database helper functions
  - Handles Supabase connections
  - Data insertion/updates
  - Used by: Scrapers

### Scheduler (Legacy/Backup)
- **`scheduler.py`** - Local scheduling daemon
  - NOT currently used (using GitHub Actions instead)
  - Kept as backup option
  - Can run weekly scrapes on local machine

- **`__init__.py`** - Python package marker

---

## Documentation

- **`GITHUB_ACTIONS_SETUP.md`** - Main setup guide
  - How to configure GitHub Actions workflows
  - Adding DATABASE_URL secret
  - Testing workflows

- **`TROUBLESHOOT_GITHUB_ACTIONS.md`** - Debugging guide
  - Common errors and solutions
  - How to view workflow logs
  - Re-running failed workflows

- **`README.md`** - Original scraper documentation
  - Historical reference
  - May be outdated

---

## Log Files

- **`keepalive.log`** - Keepalive ping history
  - Records daily database pings
  - Format: timestamp - status - event count

- **`live_scraper.log`** - Scraper execution history
  - Records all scraping activity
  - Shows events found, errors, etc.

- **`logs/`** - Additional log storage
  - Archived logs
  - Task scheduler logs (if used)

---

## GitHub Actions Workflows (in `.github/workflows/`)

- **`daily-keepalive.yml`** - Daily keepalive workflow
  - Schedule: Every day at 3 AM UTC (10 PM ET)
  - Runs: `keepalive_ping.py`
  - Purpose: Prevent Supabase auto-pause

- **`weekly-ufc-scraper.yml`** - Weekly scraper workflow
  - Schedule: Sundays at 6 PM UTC (1 PM ET)
  - Runs: `live_scraper.py`
  - Purpose: Get new UFC events

---

## How It Works

### Daily (3 AM UTC):
1. GitHub Actions triggers `daily-keepalive.yml`
2. Runs `keepalive_ping.py` on GitHub's servers
3. Queries database (SELECT COUNT(*))
4. Logs result to `keepalive.log`
5. Keeps Supabase project active

### Weekly (Sundays 6 PM UTC):
1. GitHub Actions triggers `weekly-ufc-scraper.yml`
2. Runs `live_scraper.py` on GitHub's servers
3. Scrapes UFCStats.com for new events
4. Compares with existing database
5. Inserts only NEW events/fights
6. Logs results to `live_scraper.log`

**Both run automatically in the cloud - no local machine needed!**

---

## What Was Removed (Cleanup)

Deleted files (no longer needed):
- ❌ `run_daily_keepalive.bat` - Windows Task Scheduler script
- ❌ `run_weekly_scrape.bat` - Windows Task Scheduler script  
- ❌ `scheduler_config.json` - Scheduler settings
- ❌ `scheduler_history.jsonl` - Scheduler run history
- ❌ `SETUP_TASK_SCHEDULER.md` - Task Scheduler guide
- ❌ `TASK_SCHEDULER_SETUP.md` - Duplicate guide
- ❌ `RESTORE_AND_FIX_GUIDE.md` - Temporary troubleshooting doc
- ❌ `SUPABASE_PAUSING_SOLUTION.md` - Long analysis doc
- ❌ `GITHUB_SETUP_COMPLETE.md` - Redundant with main setup guide

**Reason:** Using GitHub Actions (cloud) instead of Windows Task Scheduler (local).

---

## Quick Reference

### Test Locally
```bash
# Test keepalive ping
cd backend/scraper
python keepalive_ping.py

# Test scraper
python live_scraper.py
```

### View Logs
```bash
# Recent keepalive pings
tail -20 keepalive.log

# Recent scraper runs
tail -50 live_scraper.log
```

### Check GitHub Actions
- View runs: https://github.com/kibbbles/ufc_analytics_platform/actions
- Daily keepalive: Should run every day
- Weekly scraper: Should run every Sunday

---

## Database Tables Updated

When scraper runs, these Supabase tables are updated:
- `event_details` - UFC events (name, date, location)
- `fight_details` - Individual fights
- `fighter_details` - Fighter profiles (if new fighters)
- `fight_stats` - Per-round statistics (if available)
- `fighter_tott` - Tale of the Tape data
- `fight_results` - Fight outcomes

---

Last updated: 2025-10-20
