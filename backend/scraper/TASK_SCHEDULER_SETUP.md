# Windows Task Scheduler Setup for UFC Scraper

## Quick Setup Instructions

### Step 1: Open Task Scheduler
1. Press `Win + R`
2. Type `taskschd.msc` and press Enter
3. Click "Create Basic Task" in the right panel

### Step 2: Configure the Task

**Name & Description:**
- **Name:** `UFC Weekly Scraper`
- **Description:** `Runs weekly UFC data scraper to keep Supabase database active and updated`

**Trigger:**
- **Trigger Type:** Weekly
- **Start:** Choose next Sunday at 6:00 PM (18:00)
- **Recur every:** 1 week
- **Day:** Sunday
- **Time:** 6:00 PM (or choose your preferred time)

**Action:**
- **Action Type:** Start a program
- **Program/script:** `C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\run_weekly_scrape.bat`
- **Start in (optional):** `C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper`

**Finish:**
- Check "Open the Properties dialog" before clicking Finish

### Step 3: Advanced Settings (In Properties Dialog)

**General Tab:**
- ✅ Check "Run whether user is logged on or not" (optional - requires password)
- ✅ Check "Run with highest privileges" (if needed)
- Configure for: Windows 10/11

**Conditions Tab:**
- ⬜ Uncheck "Start the task only if the computer is on AC power" (if laptop)
- ✅ Check "Wake the computer to run this task" (ensures it runs even if sleeping)

**Settings Tab:**
- ✅ Check "Allow task to be run on demand"
- ✅ Check "Run task as soon as possible after a scheduled start is missed"
- If task fails, restart every: 10 minutes
- Attempt to restart up to: 3 times

### Step 4: Test the Task

1. Right-click the newly created task
2. Select "Run"
3. Check `backend\scraper\logs\task_scheduler_runs.log` for confirmation

## Verification

After setting up, verify the task is working:

1. Check Task Scheduler Library for "UFC Weekly Scraper"
2. Look at "Last Run Time" and "Last Run Result" columns
3. Review log files in `backend\scraper\logs\`

## Monitoring

The task will create two types of logs:
- `logs\weekly_scrape_YYYYMMDD_HHMMSS.log` - Detailed scraper output
- `logs\task_scheduler_runs.log` - Simple completion log

## Alternative: PowerShell Command

If you prefer using PowerShell to create the task automatically, run this as Administrator:

```powershell
$action = New-ScheduledTaskAction -Execute "C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper\run_weekly_scrape.bat" -WorkingDirectory "C:\Users\kabec\Documents\ufc_analytics_platform\backend\scraper"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 6pm

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -StartWhenAvailable

Register-ScheduledTask -TaskName "UFC Weekly Scraper" -Action $action -Trigger $trigger -Settings $settings -Description "Runs weekly UFC data scraper to keep Supabase database active and updated"
```

## Troubleshooting

**Task runs but nothing happens:**
- Check that Python is in your system PATH
- Verify the batch file path is correct
- Look at the detailed log files in `logs\` directory

**Python not found:**
- Add Python to system PATH, or
- Modify `run_weekly_scrape.bat` to use full Python path:
  ```batch
  "C:\Users\kabec\AppData\Local\Programs\Python\Python311\python.exe" live_scraper.py
  ```

**Permission errors:**
- Run Task Scheduler as Administrator
- Check "Run with highest privileges" in task properties

## Benefits Over Daemon Approach

✅ Survives system reboots
✅ Doesn't require terminal/session to stay open
✅ Built-in retry logic
✅ Windows manages the process lifecycle
✅ Easy to modify schedule through GUI
✅ Better error logging and monitoring
