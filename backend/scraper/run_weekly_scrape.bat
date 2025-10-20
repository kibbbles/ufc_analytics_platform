@echo off
REM Weekly UFC Scraper Task
REM This script runs the live UFC scraper and logs output

cd /d "%~dp0"

REM Set timestamp for log file
set timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Run the scraper and log output
python live_scraper.py >> "logs\weekly_scrape_%timestamp%.log" 2>&1

REM Also log completion
echo Scrape completed at %date% %time% >> "logs\task_scheduler_runs.log"
