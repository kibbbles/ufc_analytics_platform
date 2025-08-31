"""
Check if the weekly UFC scraper is running and show status
"""

import os
import subprocess
import json
from datetime import datetime

def check_scheduler_running():
    """Check if scheduler process is running"""
    try:
        # Check for Python processes running scheduler.py
        result = subprocess.run(['tasklist', '/fi', 'imagename eq python.exe'], 
                              capture_output=True, text=True, shell=True)
        
        if 'python.exe' in result.stdout:
            print("STATUS: Python processes are running (likely includes scheduler)")
            return True
        else:
            print("STATUS: No Python processes detected")
            return False
    except Exception as e:
        print(f"Could not check process status: {e}")
        return False

def check_log_files():
    """Check recent log activity"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        print("No logs directory found")
        return
    
    log_files = [f for f in os.listdir(log_dir) if f.startswith('ufc_scraper_')]
    if not log_files:
        print("No scheduler log files found")
        return
    
    # Get the most recent log file
    latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join(log_dir, x)))
    log_path = os.path.join(log_dir, latest_log)
    
    print(f"LATEST LOG: {latest_log}")
    
    # Show last few lines
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            if lines:
                print("RECENT LOG ENTRIES:")
                for line in lines[-5:]:
                    print(f"  {line.strip()}")
            else:
                print("Log file is empty")
    except Exception as e:
        print(f"Could not read log file: {e}")

def check_schedule_history():
    """Check scheduler history for recent activity"""
    history_file = "scheduler_history.jsonl"
    if not os.path.exists(history_file):
        print("No scheduler history found")
        return
    
    try:
        with open(history_file, 'r') as f:
            lines = f.readlines()
            if lines:
                print("RECENT SCHEDULER ACTIVITY:")
                # Show last 3 entries
                for line in lines[-3:]:
                    data = json.loads(line.strip())
                    timestamp = data.get('timestamp', 'Unknown')
                    job_name = data.get('job_name', 'Unknown')
                    success = data.get('success', False)
                    status = "SUCCESS" if success else "FAILED"
                    print(f"  {timestamp}: {job_name} - {status}")
            else:
                print("No scheduler history found")
    except Exception as e:
        print(f"Could not read scheduler history: {e}")

def main():
    print("=" * 60)
    print("UFC WEEKLY SCRAPER STATUS CHECK")
    print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check if scheduler is running
    is_running = check_scheduler_running()
    
    print()
    print("CONFIGURATION:")
    print("  Weekly Schedule: Every Sunday at 6:00 AM")
    print("  Next Run: Check logs below for exact date")
    
    print()
    check_log_files()
    
    print()
    check_schedule_history()
    
    print()
    print("=" * 60)
    if is_running:
        print("SUMMARY: Weekly scraper appears to be running")
        print("Next update: Sunday at 6:00 AM")
    else:
        print("SUMMARY: Weekly scraper may not be running")
        print("To start: python scheduler.py --action start --daemon")
    print("=" * 60)

if __name__ == "__main__":
    main()