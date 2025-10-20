# Quick Start: Restore Supabase & Prevent Future Pausing

## What Happened? (Summary)

1. **Sept 28**: Last successful scrape before pause
2. **Oct 5-6**: Supabase auto-paused after 7 days of inactivity
3. **Oct 10 (12:51 PM)**: Scrape failed - project was paused
4. **Oct 10 (1:12 PM)**: You restored project, scrape succeeded, added October data ✅
5. **Currently**: Project likely paused again (Oct 17+) unless you've been running pings

## Immediate Action Required

### Step 1: Restore Supabase Project (NOW)

1. Go to: https://supabase.com/dashboard
2. Find project: "kibbbles's Project"
3. Click **"Restore"** button
4. Wait ~30 seconds for restoration

### Step 2: Test Connection

```bash
cd C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper
python keepalive_ping.py
```

Should show:
```
✓ SUCCESS: Database connection active
✓ Database contains 747+ UFC events
```

If it fails, wait a bit longer for Supabase to fully restore.

### Step 3: Catch Up on Missed Data

Run the scraper to get any UFC events from the past 2 weeks:

```bash
cd C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper
python live_scraper.py
```

## Choose Your Automation Strategy

You have **two options** to prevent future pausing:

### Option A: Windows Task Scheduler (Simpler)

**Pros**: Easy setup, runs locally
**Cons**: Requires computer to be on daily

**Setup**: Follow instructions in `SETUP_TASK_SCHEDULER.md`

**Quick version**:
1. Open Task Scheduler (`taskschd.msc`)
2. Create daily task for `run_daily_keepalive.bat`
3. Create weekly task for `run_weekly_scrape.bat`

### Option B: GitHub Actions (RECOMMENDED) 🌟

**Pros**: Works even when computer is off, production-quality
**Cons**: Requires pushing to GitHub

**Setup**: Follow instructions in `GITHUB_ACTIONS_SETUP.md`

**Quick version**:
1. Add `DATABASE_URL` to GitHub Secrets
2. Push workflow files to GitHub:
   ```bash
   git add .github/workflows/
   git commit -m "Add automated scraping workflows"
   git push
   ```
3. Test workflows in GitHub Actions tab

## Why Both Solutions Work

Both prevent pausing by ensuring **at least one database connection every 7 days**:

- **Daily keepalive**: Pings database every day (lightweight, <1 second)
- **Weekly scraper**: Scrapes new UFC data every Sunday (1-2 minutes)

## Files Created for You

✅ **Keepalive Script**: `keepalive_ping.py`
✅ **Batch Files**: `run_daily_keepalive.bat`, `run_weekly_scrape.bat`
✅ **GitHub Workflows**: `.github/workflows/daily-keepalive.yml`, `weekly-ufc-scraper.yml`
✅ **Setup Guides**: `SETUP_TASK_SCHEDULER.md`, `GITHUB_ACTIONS_SETUP.md`
✅ **Analysis**: `SUPABASE_PAUSING_SOLUTION.md`

## Testing Your Setup

### Test Keepalive Ping

```bash
cd backend/scraper
python keepalive_ping.py
```

Should see success message and create `keepalive.log`.

### Test Weekly Scraper

```bash
cd backend/scraper
python live_scraper.py
```

Should show:
- "SUCCESS: No new UFC events found" (if database is up to date)
- OR "NEW DATA FOUND! X new UFC events detected" (if there are new events)

### Monitor Logs

**Keepalive log**:
```bash
type backend\scraper\keepalive.log
```

**Scraper log**:
```bash
type backend\scraper\live_scraper.log
```

## Quick Decision Matrix

**Choose GitHub Actions if:**
- ✅ You want a production-quality solution
- ✅ Your computer isn't always on
- ✅ You want to impress potential employers
- ✅ You're comfortable with Git/GitHub

**Choose Task Scheduler if:**
- ✅ Your computer is usually on daily
- ✅ You want local control
- ✅ You prefer not to use GitHub Actions
- ✅ You want the simplest setup

**Best approach**: Use BOTH! Task Scheduler as backup, GitHub Actions as primary.

## Verification Checklist

After setup, verify everything works:

- [ ] Supabase project is restored and active
- [ ] `keepalive_ping.py` runs successfully
- [ ] `live_scraper.py` runs successfully
- [ ] Automation is set up (Task Scheduler OR GitHub Actions)
- [ ] Logs are being created
- [ ] Schedule is correct (daily for keepalive, weekly for scraper)

## What to Expect

### Daily (Keepalive)
```
3:00 AM - Ping runs
        - Quick database query (< 1 second)
        - Logs to keepalive.log
        - Supabase stays active
```

### Weekly (Scraper)
```
Sunday 6:00 PM - Scraper runs
               - Checks UFCStats.com for new events
               - Compares with database
               - Adds any new events/fights
               - Takes 1-2 minutes
               - Logs to live_scraper.log
```

## Long-Term Monitoring

### Check Supabase Dashboard Monthly
- Log in to verify project is active
- Check data is growing (new events added)

### Review Logs Monthly
```bash
# Last 20 keepalive pings
tail -20 backend/scraper/keepalive.log

# Recent scraper runs
tail -50 backend/scraper/live_scraper.log | grep "Live scraping completed"
```

### GitHub Actions (if used)
- Visit: https://github.com/YOUR_USERNAME/ufc_analytics_platform/actions
- Check for green checkmarks (success) or red X's (failures)
- GitHub emails you automatically if workflows fail

## Troubleshooting

### "Database connection failed"
→ Restore Supabase project, wait 1-2 minutes, try again

### "No module named 'schedule'"
→ `pip install schedule requests beautifulsoup4`

### Task Scheduler task doesn't run
→ Check task is enabled, computer was on at scheduled time

### GitHub Action doesn't run
→ Check DATABASE_URL secret is set, workflows are enabled

## Summary

**You now have everything you need to:**
1. ✅ Restore your Supabase project
2. ✅ Prevent future auto-pausing
3. ✅ Keep UFC data up-to-date automatically
4. ✅ Monitor the system

**Choose your path and get started!** 🚀
