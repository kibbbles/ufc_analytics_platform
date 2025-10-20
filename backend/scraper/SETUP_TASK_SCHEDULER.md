# Setup Windows Task Scheduler for UFC Scraper

## Overview

Set up two automated tasks:
1. **Daily Keepalive Ping** - Prevents Supabase from pausing (runs daily)
2. **Weekly UFC Scraper** - Gets new fight data (runs Sundays)

## Prerequisites

- Supabase project must be **restored** (not paused)
- Python installed and accessible from Command Prompt
- All dependencies installed (`pip install -r backend/requirements.txt`)

## Step-by-Step Setup

### Task 1: Daily Keepalive Ping

This prevents Supabase from auto-pausing after 7 days.

1. **Open Task Scheduler**
   - Press `Windows + R`
   - Type `taskschd.msc`
   - Press Enter

2. **Create New Task**
   - Click "Create Basic Task..." in right sidebar
   - Name: `Supabase Daily Keepalive`
   - Description: `Prevents Supabase free tier from auto-pausing`
   - Click "Next"

3. **Set Trigger**
   - Select: "Daily"
   - Click "Next"
   - Start: Tomorrow at `3:00 AM` (or any time your computer is usually on)
   - Recur every: `1` days
   - Click "Next"

4. **Set Action**
   - Select: "Start a program"
   - Click "Next"
   - Program/script: `C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\run_daily_keepalive.bat`
   - Click "Next"

5. **Finish**
   - Check: "Open the Properties dialog for this task when I click Finish"
   - Click "Finish"

6. **Configure Advanced Settings** (in Properties dialog that opens)
   - Go to "Conditions" tab:
     - ✓ Check "Wake the computer to run this task" (if you want it to run even when sleeping)
     - ✓ Uncheck "Start the task only if the computer is on AC power"
   - Go to "Settings" tab:
     - ✓ Check "Run task as soon as possible after a scheduled start is missed"
   - Click "OK"

### Task 2: Weekly UFC Scraper

This scrapes new UFC events every Sunday.

1. **Create New Task**
   - Click "Create Basic Task..." again
   - Name: `UFC Weekly Scraper`
   - Description: `Scrapes new UFC events from UFCStats.com`
   - Click "Next"

2. **Set Trigger**
   - Select: "Weekly"
   - Click "Next"
   - Start: Next Sunday at `6:00 PM`
   - Recur every: `1` weeks
   - Select: Sunday only
   - Click "Next"

3. **Set Action**
   - Select: "Start a program"
   - Click "Next"
   - Program/script: `C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\run_weekly_scrape.bat`
   - Click "Next"

4. **Finish**
   - Check: "Open the Properties dialog for this task when I click Finish"
   - Click "Finish"

5. **Configure Advanced Settings**
   - Go to "Conditions" tab:
     - ✓ Check "Wake the computer to run this task"
     - ✓ Uncheck "Start the task only if the computer is on AC power"
   - Go to "Settings" tab:
     - ✓ Check "Run task as soon as possible after a scheduled start is missed"
   - Click "OK"

## Verify Setup

### Test the Keepalive Ping

```cmd
cd C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper
run_daily_keepalive.bat
```

You should see:
```
============================================================
Supabase Keepalive Ping - 2025-10-19 15:30:00
============================================================

✓ SUCCESS: Database connection active
✓ Database contains 747 UFC events
✓ Supabase project will remain active
```

### Test the Weekly Scraper

```cmd
cd C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper
run_weekly_scrape.bat
```

Check the logs folder for output.

### Test Task Scheduler

1. Open Task Scheduler
2. Find "Supabase Daily Keepalive" in the task list
3. Right-click → "Run"
4. Check the "Last Run Result" column - should show "The operation completed successfully. (0x0)"

Repeat for "UFC Weekly Scraper"

## Monitor the Tasks

### Check Keepalive Log

```cmd
type C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\keepalive.log
```

Should show daily successful pings.

### Check Scraper Logs

```cmd
dir C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\logs
```

Look for:
- `weekly_scrape_*.log` - Individual scrape run logs
- `task_scheduler_runs.log` - Summary of when tasks ran

## Troubleshooting

### Task shows "Could not start" error

**Problem**: Python not found or path issues

**Solution**:
1. Open Task Properties
2. Go to "Actions" tab
3. Edit the action
4. Change to full Python path:
   - Program: `C:\Users\kabec\AppData\Local\Microsoft\WindowsApps\python.exe`
   - Arguments: `keepalive_ping.py`
   - Start in: `C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper`

### Task runs but fails

**Check the exit code**:
- `0x0` = Success
- `0x1` = Failed (check log files)

**Check logs**:
```cmd
type C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\keepalive.log
type C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\live_scraper.log
```

### Computer sleeps and tasks don't run

**Solution**:
1. Task Properties → Conditions tab
2. ✓ Check "Wake the computer to run this task"

Or adjust schedule to times when computer is definitely on.

## Important Notes

### Task Scheduler Limitations:

❌ **Only runs when computer is ON**
- If computer is off/asleep, tasks are missed
- "Run as soon as possible after missed" helps but doesn't always work

❌ **Requires Windows login**
- Some configurations require user to be logged in
- May not work if computer is locked (depends on settings)

### Better Alternative: GitHub Actions

If you want **truly reliable** automation that works even when your computer is off, consider GitHub Actions (see `GITHUB_ACTIONS_SETUP.md`).

## Summary

Once set up, your system will:
- ✓ Ping Supabase **daily** at 3 AM (prevents pausing)
- ✓ Scrape UFC data **weekly** on Sundays at 6 PM
- ✓ Keep detailed logs of all activity
- ✓ Retry missed tasks when computer comes online

**Your Supabase project should never pause again!** (as long as computer is on daily)
