# Troubleshooting GitHub Actions Failures

## How to View Error Details

1. Go to: https://github.com/kibbbles/ufc_analytics_platform/actions
2. Click on the failed workflow run (shows red ❌)
3. Click on the job name (e.g., "keepalive" or "scrape")
4. Look for steps with red ❌ icons
5. Click to expand them and see the error message

## Common Errors & Solutions

### Error 1: "DATABASE_URL is not set" or "could not connect"

**Error message looks like:**
```
Error: DATABASE_URL environment variable not set
```
OR
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string ''
```

**Cause:** DATABASE_URL secret not added to GitHub

**Solution:**
1. Go to: https://github.com/kibbbles/ufc_analytics_platform/settings/secrets/actions
2. Click "New repository secret"
3. Name: `DATABASE_URL` (exactly, case-sensitive)
4. Value: Your database URL from `.env`:
   ```
   postgresql://postgres:p2GrvZEea/XEY%d@db.mklpmbqpegbsistkoskm.supabase.co:5432/postgres
   ```
5. Click "Add secret"
6. Re-run the workflow

### Error 2: "could not translate host name"

**Error message looks like:**
```
psycopg2.OperationalError: could not translate host name "db.mklpmbqpegbsistkoskm.supabase.co" to address
```

**Cause:** Supabase project is paused

**Solution:**
1. Go to Supabase dashboard
2. Click "Restore" on your project
3. Wait 1-2 minutes
4. Re-run the workflow

### Error 3: "relation does not exist"

**Error message looks like:**
```
psycopg2.errors.UndefinedTable: relation "event_details" does not exist
```

**Cause:** Tables haven't been created in database

**Solution:**
This shouldn't happen since your database already has data. If you see this:
1. Check you're using the correct DATABASE_URL
2. Verify tables exist in Supabase dashboard

### Error 4: Unicode/Encoding Issues

**Error message looks like:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Cause:** Windows encoding issue with special characters

**Solution:**
This should be fixed already in the latest `keepalive_ping.py`. If you still see it:
1. Check that latest code is pushed to GitHub
2. The workflow file is using the updated version

### Error 5: Module not found

**Error message looks like:**
```
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Cause:** Dependencies not installed

**Solution:**
Check workflow file has this step:
```yaml
- name: Install dependencies
  run: |
    cd backend
    pip install sqlalchemy psycopg2-binary python-dotenv
```

This should already be in place.

## How to Re-run a Failed Workflow

1. Go to the failed workflow run
2. Click "Re-run jobs" button (top right)
3. Select "Re-run failed jobs"
4. Wait for it to complete

## Viewing Successful Runs

When a workflow succeeds, you'll see:
- Green ✅ checkmark
- All steps show green
- Output shows success messages

For keepalive:
```
[SUCCESS] Database connection active
[SUCCESS] Database contains 2237 UFC events
[SUCCESS] Supabase project will remain active
```

For scraper:
```
SUCCESS: No new UFC events found - database is up to date!
```
OR
```
*** NEW DATA FOUND! X new UFC events detected
```

## Still Having Issues?

### Check the workflow logs carefully:

1. Expand each step in the failed job
2. Look for the FIRST error (not subsequent ones)
3. The first error is usually the root cause

### Verify secret is set:

1. Go to: https://github.com/kibbbles/ufc_analytics_platform/settings/secrets/actions
2. You should see: `DATABASE_URL` in the list
3. If not, add it

### Test locally first:

Run the keepalive script on your computer:
```bash
cd backend/scraper
python keepalive_ping.py
```

If this works locally but fails on GitHub, it's likely a secret/configuration issue.

If this fails locally, fix the local issue first before debugging GitHub Actions.

## Schedule Not Running?

If manual runs work but scheduled runs don't happen:

**Wait 24 hours** - First scheduled run can take time to activate

**Check if workflows are enabled:**
- Go to Actions tab
- Should NOT see "Workflows are disabled"
- If disabled, click "I understand my workflows, enable them"

**Check cron syntax:**
- Daily keepalive: `'0 3 * * *'` = 3 AM UTC every day
- Weekly scraper: `'0 18 * * 0'` = 6 PM UTC every Sunday

## Getting Help

When asking for help, provide:
1. Screenshot or copy of the error message
2. Which workflow failed (keepalive or scraper)
3. Whether you added DATABASE_URL secret
4. Whether it works when you run locally
