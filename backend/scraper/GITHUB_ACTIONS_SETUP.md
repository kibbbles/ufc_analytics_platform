# Setup GitHub Actions for UFC Scraper (RECOMMENDED)

## Why GitHub Actions?

**Advantages over Windows Task Scheduler:**
- ✅ Runs even when your computer is OFF
- ✅ Runs even when you're away on vacation
- ✅ No daemon process to maintain
- ✅ Cloud-based, always reliable
- ✅ **FREE** - 2,000 minutes/month (way more than needed)
- ✅ Email notifications on failures
- ✅ Easy to monitor via GitHub UI

**Use this if:**
- Your computer isn't always on
- You want "set it and forget it" automation
- You want a production-quality solution

## Prerequisites

1. **GitHub account** (you already have this since you have the repo)
2. **Supabase project restored** (not paused)
3. **Database credentials** from `.env` file

## Setup Instructions

### Step 1: Add Database Credentials to GitHub Secrets

1. **Go to your GitHub repository**
   - Navigate to: https://github.com/YOUR_USERNAME/ufc_analytics_platform

2. **Open Settings**
   - Click "Settings" tab (top menu)

3. **Go to Secrets**
   - Left sidebar → "Secrets and variables" → "Actions"

4. **Add New Secret**
   - Click "New repository secret"
   - Name: `DATABASE_URL`
   - Value: Copy from your `.env` file:
     ```
     postgresql://postgres:p2GrvZEea/XEY%d@db.mklpmbqpegbsistkoskm.supabase.co:5432/postgres
     ```
   - Click "Add secret"

### Step 2: Push Workflow Files to GitHub

The workflow files are already created in `.github/workflows/`:
- `daily-keepalive.yml` - Daily database ping
- `weekly-ufc-scraper.yml` - Weekly UFC data scraping

**Push them to GitHub:**

```bash
cd C:\Users\kabec\Documents\ufc_analytics_platform

# Add the workflow files
git add .github/workflows/

# Commit
git commit -m "Add GitHub Actions for automated UFC scraping and Supabase keepalive"

# Push to GitHub
git push origin main
```

### Step 3: Verify Workflows Are Active

1. **Go to GitHub repository**
2. **Click "Actions" tab**
3. You should see two workflows:
   - "Daily Supabase Keepalive"
   - "Weekly UFC Scraper"

### Step 4: Test the Workflows

**Test the keepalive ping:**

1. Go to "Actions" tab
2. Click "Daily Supabase Keepalive"
3. Click "Run workflow" dropdown (top right)
4. Click "Run workflow" button
5. Wait ~30 seconds, refresh page
6. Click on the workflow run to see logs
7. Should show "✓ Keepalive ping successful"

**Test the scraper:**

1. Go to "Actions" tab
2. Click "Weekly UFC Scraper"
3. Click "Run workflow" dropdown
4. Click "Run workflow" button
5. Wait ~1-2 minutes, refresh page
6. Click on the workflow run to see logs
7. Should show scraper output

### Step 5: Monitor Automated Runs

**Check workflow history:**
- Go to "Actions" tab
- Click on a workflow name
- See all past runs with status (✓ success or ✗ failed)

**Email notifications:**
- GitHub sends email when workflows fail
- Go to GitHub Settings → Notifications to configure

## Schedules

### Daily Keepalive
- **When**: Every day at 3:00 AM UTC
- **What**: Simple database query to keep Supabase active
- **Duration**: ~30 seconds
- **Cost**: Free (uses ~15 minutes/month)

### Weekly Scraper
- **When**: Every Sunday at 6:00 PM UTC
- **What**: Scrapes new UFC events from UFCStats.com
- **Duration**: ~1-2 minutes
- **Cost**: Free (uses ~8 minutes/month)

**Total usage**: ~23 minutes/month out of 2,000 free minutes

## Troubleshooting

### Workflow shows "Workflow failed" ❌

**Check the logs:**
1. Click on the failed workflow run
2. Click on the "keepalive" or "scrape" job
3. Expand each step to see error messages

**Common issues:**

**1. Database connection failed**
```
Error: could not translate host name
```
**Solution**: Restore your Supabase project if paused

**2. DATABASE_URL secret not found**
```
Error: DATABASE_URL environment variable not set
```
**Solution**: Add DATABASE_URL to GitHub Secrets (Step 1)

**3. Module not found**
```
ModuleNotFoundError: No module named 'sqlalchemy'
```
**Solution**: Workflow file has wrong dependencies - check that `pip install -r requirements.txt` runs

### Workflow doesn't run on schedule

**Wait 24 hours** - First scheduled run may take time to activate

**Check if schedules are enabled:**
- Go to "Actions" tab
- Should NOT see "Workflows disabled" message
- If disabled, click "Enable workflows"

### Change the schedule

**Edit the workflow file:**

For daily keepalive (`.github/workflows/daily-keepalive.yml`):
```yaml
on:
  schedule:
    - cron: '0 15 * * *'  # Change to 3 PM UTC (10 AM ET)
```

For weekly scraper (`.github/workflows/weekly-ufc-scraper.yml`):
```yaml
on:
  schedule:
    - cron: '0 18 * * 0'  # Sunday 6 PM UTC (1 PM ET)
```

**Cron syntax**: `'minute hour day month weekday'`
- `'0 3 * * *'` = 3:00 AM UTC every day
- `'0 18 * * 0'` = 6:00 PM UTC every Sunday (0 = Sunday)

**After editing**, commit and push changes:
```bash
git add .github/workflows/
git commit -m "Update workflow schedules"
git push
```

## Security Best Practices

### Never commit credentials to Git!

❌ **DON'T**:
```yaml
env:
  DATABASE_URL: postgresql://postgres:password@host/db  # NEVER DO THIS
```

✅ **DO**:
```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}  # Use secrets
```

### Protect your `.env` file

Make sure `.env` is in `.gitignore`:
```bash
# Check if .env is ignored
git status

# If .env shows up, add to .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Ensure .env is ignored"
```

## Monitoring Your Workflows

### View Recent Runs

```bash
# Install GitHub CLI (optional)
# Then run:
gh run list --workflow=daily-keepalive.yml
gh run list --workflow=weekly-ufc-scraper.yml
```

### Email Notifications

GitHub sends emails for:
- ✗ Workflow failures (automatic)
- ✓ First successful run after failures
- Configure in: GitHub Settings → Notifications

### Check Supabase Dashboard

Verify data is being added:
1. Log into Supabase
2. Go to Table Editor
3. Check `event_details` table - should see new events weekly

## Comparison: Task Scheduler vs GitHub Actions

| Feature | Windows Task Scheduler | GitHub Actions |
|---------|----------------------|----------------|
| **Requires computer on** | ✅ Yes | ❌ No |
| **Runs when away** | ❌ No | ✅ Yes |
| **Setup complexity** | Medium | Easy |
| **Reliability** | Medium | High |
| **Cost** | Free | Free |
| **Monitoring** | Manual (check logs) | Built-in UI |
| **Notifications** | None | Email on failure |
| **Best for** | Always-on computers | Production use |

## Recommendation

**Use GitHub Actions** for the UFC Analytics Platform because:
1. This is a **portfolio project** - you want it to work reliably
2. You may not always have your computer on
3. It's completely free and production-quality
4. Easy to show employers: "My scraper runs automatically in the cloud"

**Keep Task Scheduler** as a backup if you want local control.

## Next Steps

Once GitHub Actions is set up:
1. ✅ Restore Supabase project
2. ✅ Push workflow files to GitHub
3. ✅ Add DATABASE_URL secret
4. ✅ Test both workflows manually
5. ✅ Wait for first scheduled run (24 hours)
6. ✅ Monitor via Actions tab

**Your UFC database will stay up-to-date automatically, forever!** 🎉
