@echo off
REM Daily Supabase Keepalive Ping
REM Prevents free tier from auto-pausing

cd /d "%~dp0"

REM Run keepalive ping
python keepalive_ping.py

REM Exit with python's exit code
exit /b %ERRORLEVEL%
