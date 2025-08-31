"""
Scheduling and automation system for UFC scraper
Weekly scraping (UFC events happen ~2x per month)
"""

import schedule
import time
import logging
import os
import json
from datetime import datetime, timedelta
import threading
import signal
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
import random

# Import database integration and live scraper
from live_scraper import LiveUFCScraper
from database_integration import DatabaseIntegration

class UFCScrapingScheduler:
    """
    Handles weekly scheduled scraping of UFC data (UFC events happen ~2x per month)
    """
    
    def __init__(self, config_file="scheduler_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.running = False
        self.scheduler_thread = None
        self.db_integration = DatabaseIntegration()
        
        # Set up logging
        self.setup_logging(
            log_level=getattr(logging, self.config.get('log_level', 'INFO')),
            log_file=self.config.get('log_file')
        )
        
        self.logger = logging.getLogger(__name__)
        self.setup_signal_handlers()
    
    def setup_logging(self, log_level=logging.INFO, log_file=None):
        """Set up comprehensive logging"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"{log_dir}/ufc_scraper_{timestamp}.log"
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging initialized. Log file: {log_file}")
    
    def load_config(self):
        """Load scheduler configuration"""
        default_config = {
            'weekly_scrape_day': 'sunday',
            'weekly_scrape_time': '06:00',
            'max_events_per_run': 20,
            'days_back_to_check': 14,
            'enable_database_storage': True,
            'enable_data_validation': True,
            'log_level': 'INFO',
            'log_file': None,
            'retry_failed_jobs': True,
            'max_retries': 3
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logging.info(f"Loaded scheduler config: {self.config_file}")
            except Exception as e:
                logging.error(f"Error loading config file: {e}")
        else:
            self.save_config(default_config)
        
        return default_config
    
    def save_config(self, config=None):
        """Save scheduler configuration"""
        if config is None:
            config = self.config
            
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Saved scheduler config to {self.config_file}")
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def safe_get_soup(self, url, max_retries=3):
        """Safely get soup with retries"""
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(1, 3))
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"Failed to fetch after {max_retries} attempts: {url}")
        return None
    
    def parse_events_page(self, soup):
        """Parse events from the main events page"""
        events = []
        
        try:
            event_rows = soup.find_all('tr', class_='b-statistics__table-row')
            
            for row in event_rows:
                try:
                    event_link = row.find('a', class_='b-link')
                    if not event_link:
                        continue
                        
                    event_name = event_link.text.strip()
                    event_url = event_link.get('href', '')
                    
                    cols = row.find_all('td', class_='b-statistics__table-col')
                    
                    event_date = cols[0].find('span', class_='b-statistics__date').text.strip() if cols and cols[0].find('span', class_='b-statistics__date') else None
                    event_location = cols[1].text.strip() if len(cols) > 1 else None
                    
                    if event_name and event_url:
                        events.append({
                            'EVENT': event_name,
                            'URL': event_url,
                            'DATE': event_date,
                            'LOCATION': event_location
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Error parsing event row: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error parsing events page: {e}")
        
        return pd.DataFrame(events)
    
    def parse_fight_details(self, soup):
        """Parse fight details from an event page"""
        fights = []
        
        try:
            fight_rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            for row in fight_rows[1:]:  # Skip header row
                try:
                    fight_link = row.find('a', {'class': 'b-flag'})
                    if not fight_link:
                        continue
                        
                    fight_url = fight_link.get('href', '')
                    
                    fighters = row.find_all('a', class_='b-link_style_black')
                    if len(fighters) >= 2:
                        fighter_a = fighters[0].text.strip()
                        fighter_b = fighters[1].text.strip()
                        bout = f"{fighter_a} vs. {fighter_b}"
                    else:
                        continue
                    
                    weight_class_td = row.find_all('td', class_='b-fight-details__table-col')[6] if len(row.find_all('td', class_='b-fight-details__table-col')) > 6 else None
                    weight_class = weight_class_td.text.strip() if weight_class_td else None
                    
                    method_td = row.find_all('td', class_='b-fight-details__table-col')[7] if len(row.find_all('td', class_='b-fight-details__table-col')) > 7 else None
                    method = method_td.text.strip() if method_td else None
                    
                    fights.append({
                        'URL': fight_url,
                        'BOUT': bout,
                        'FIGHTER_A': fighter_a,
                        'FIGHTER_B': fighter_b,
                        'WEIGHT_CLASS': weight_class,
                        'METHOD': method
                    })
                    
                except Exception as e:
                    self.logger.warning(f"Error parsing fight row: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error parsing fights: {e}")
        
        return pd.DataFrame(fights)
    
    def weekly_scrape_job(self):
        """Weekly UFC scraping job using live scraper (after Greko data load)"""
        job_name = "weekly_ufc_scrape"
        self.logger.info(f"Starting {job_name}")
        
        try:
            # Use the new live scraper for incremental updates
            scraper = LiveUFCScraper()
            success = scraper.run_live_scraping()
            
            if success:
                self.logger.info("Weekly live scraping completed successfully")
                self.log_job_completion(job_name, True, {'status': 'completed', 'type': 'live_scraping'})
            else:
                self.logger.error("Weekly live scraping failed")
                self.log_job_completion(job_name, False, {'error': 'Live scraping failed'})
                
        except Exception as e:
            self.logger.error(f"Error in {job_name}: {e}")
            self.log_job_completion(job_name, False, {'error': str(e)})
            
            if self.config['retry_failed_jobs']:
                self.retry_job(job_name, self.weekly_scrape_job)
    
    def retry_job(self, job_name, job_function, attempt=1):
        """Retry failed job with exponential backoff"""
        max_retries = self.config['max_retries']
        
        if attempt > max_retries:
            self.logger.error(f"{job_name} failed after {max_retries} retries")
            return
        
        delay_minutes = 2 ** (attempt - 1)
        self.logger.info(f"Retrying {job_name} in {delay_minutes} minutes (attempt {attempt}/{max_retries})")
        
        schedule.every(delay_minutes).minutes.do(self._retry_job_wrapper, job_name, job_function, attempt).tag(f"retry_{job_name}")
    
    def _retry_job_wrapper(self, job_name, job_function, attempt):
        """Wrapper for retry job execution"""
        try:
            job_function()
            schedule.clear(f"retry_{job_name}")
        except Exception as e:
            self.logger.error(f"Retry {attempt} failed for {job_name}: {e}")
            self.retry_job(job_name, job_function, attempt + 1)
        
        return schedule.CancelJob
    
    def log_job_completion(self, job_name, success, results):
        """Log job completion to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'job_name': job_name,
            'success': success,
            'results': results
        }
        
        log_file = 'scheduler_history.jsonl'
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            self.logger.error(f"Error writing to job history: {e}")
    
    def setup_schedule(self):
        """Setup scheduled jobs"""
        weekly_day = self.config['weekly_scrape_day'].lower()
        weekly_time = self.config['weekly_scrape_time']
        
        if weekly_day == 'monday':
            schedule.every().monday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        elif weekly_day == 'tuesday':
            schedule.every().tuesday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        elif weekly_day == 'wednesday':
            schedule.every().wednesday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        elif weekly_day == 'thursday':
            schedule.every().thursday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        elif weekly_day == 'friday':
            schedule.every().friday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        elif weekly_day == 'saturday':
            schedule.every().saturday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        else:  # default to sunday
            schedule.every().sunday.at(weekly_time).do(self.weekly_scrape_job).tag('weekly')
        
        self.logger.info(f"Scheduled weekly UFC scrape on {weekly_day} at {weekly_time}")
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        self.logger.info("Starting UFC scraping scheduler...")
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)
        
        self.logger.info("Scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.setup_schedule()
        self.running = True
        
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("UFC scraping scheduler started")
        self.print_schedule_summary()
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        self.logger.info("UFC scraping scheduler stopped")
    
    def print_schedule_summary(self):
        """Print summary of scheduled jobs"""
        self.logger.info("Scheduled jobs:")
        for job in schedule.jobs:
            next_run = job.next_run.strftime('%Y-%m-%d %H:%M:%S') if job.next_run else 'Not scheduled'
            self.logger.info(f"  - {job.job_func.__name__}: {next_run}")
    
    def run_job_now(self, job_type='weekly'):
        """Manually run a job immediately"""
        if job_type == 'weekly':
            self.logger.info("Running weekly UFC scrape job manually")
            self.weekly_scrape_job()
        else:
            self.logger.error(f"Unknown job type: {job_type}. Only 'weekly' is supported.")

def main():
    """Example usage of scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UFC Scraping Scheduler')
    parser.add_argument('--action', choices=['start', 'run-weekly'], 
                       default='start', help='Action to perform')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    scheduler = UFCScrapingScheduler()
    
    if args.action == 'start':
        scheduler.start()
        
        if args.daemon:
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                scheduler.stop()
        else:
            print("Scheduler started. Commands: 'weekly', 'quit'")
            while True:
                try:
                    cmd = input("> ").strip().lower()
                    if cmd == 'quit':
                        break
                    elif cmd == 'weekly':
                        scheduler.run_job_now('weekly')
                    else:
                        print("Unknown command. Use 'weekly' or 'quit'")
                except KeyboardInterrupt:
                    break
            
            scheduler.stop()
            
    elif args.action == 'run-weekly':
        scheduler.run_job_now('weekly')

if __name__ == "__main__":
    main()