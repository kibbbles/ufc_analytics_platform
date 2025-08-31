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

# Import our enhanced scraper and database integration
from enhanced_scraper import EnhancedUFCScraper
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
        self.scraper = EnhancedUFCScraper()
        self.db_integration = DatabaseIntegration()
        
        # Set up logging
        self.scraper.setup_logging(
            log_level=getattr(logging, self.config.get('log_level', 'INFO')),
            log_file=self.config.get('log_file')
        )
        
        self.logger = logging.getLogger(__name__)
        self.setup_signal_handlers()
    
    def load_config(self):
        """Load scheduler configuration"""
        default_config = {
            'weekly_scrape_day': 'sunday',
            'weekly_scrape_time': '06:00',  # 6 AM Sunday
            'max_events_per_run': None,     # No limit (UFC events are ~2 per month)
            'days_back_to_check': 14,       # Look back 2 weeks to catch any events
            'enable_database_storage': True,
            'enable_csv_backup': True,
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
            # Save default config
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
    
    def weekly_scrape_job(self):
        """Weekly UFC scraping job (UFC events happen ~2x per month)"""
        job_name = "weekly_ufc_scrape"
        self.logger.info(f"Starting {job_name}")
        
        try:
            results = self.scraper.incremental_scrape(
                max_new_events=self.config['max_events_per_run'],  # None = no limit
                days_back=self.config['days_back_to_check'],       # 14 days lookback
                validate_data=self.config['enable_data_validation']
            )
            
            if results['success']:
                self.logger.info(f"{job_name} completed successfully: "
                               f"{results['events_scraped']} events, "
                               f"{results['fights_scraped']} fights")
                
                # Save to database if enabled
                if self.config['enable_database_storage']:
                    self.save_to_database()
                
                self.log_job_completion(job_name, True, results)
                
            else:
                self.logger.error(f"{job_name} failed: {results.get('errors', [])}")
                self.log_job_completion(job_name, False, results)
                
                if self.config['retry_failed_jobs']:
                    self.retry_job(job_name, self.weekly_scrape_job)
                    
        except Exception as e:
            self.logger.error(f"Error in {job_name}: {e}")
            self.log_job_completion(job_name, False, {'error': str(e)})
    
    def save_to_database(self):
        """Save CSV data to database"""
        if not self.db_integration.test_connection():
            self.logger.error("Database connection failed, skipping database save")
            return
        
        try:
            # Load current data
            data_dict = self.scraper.load_existing_data()
            
            # Save to database
            if data_dict:
                results = self.db_integration.save_all_data_to_db(data_dict)
                self.logger.info(f"Database save results: {results}")
            
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
    
    def retry_job(self, job_name, job_function, attempt=1):
        """Retry failed job with exponential backoff"""
        max_retries = self.config['max_retries']
        
        if attempt > max_retries:
            self.logger.error(f"{job_name} failed after {max_retries} retries")
            return
        
        # Exponential backoff: 1min, 2min, 4min, 8min...
        delay_minutes = 2 ** (attempt - 1)
        self.logger.info(f"Retrying {job_name} in {delay_minutes} minutes (attempt {attempt}/{max_retries})")
        
        # Schedule retry
        schedule.every(delay_minutes).minutes.do(self._retry_job_wrapper, job_name, job_function, attempt).tag(f"retry_{job_name}")
    
    def _retry_job_wrapper(self, job_name, job_function, attempt):
        """Wrapper for retry job execution"""
        try:
            job_function()
            # Clear retry jobs if successful
            schedule.clear(f"retry_{job_name}")
        except Exception as e:
            self.logger.error(f"Retry {attempt} failed for {job_name}: {e}")
            self.retry_job(job_name, job_function, attempt + 1)
        
        # Clear this retry job
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
        # Weekly UFC scrape (UFC events happen ~2x per month)
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
            time.sleep(60)  # Check every minute
        
        self.logger.info("Scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.setup_schedule()
        self.running = True
        
        # Start scheduler in separate thread
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
            # Run as daemon
            try:
                while True:
                    time.sleep(3600)  # Sleep for 1 hour
            except KeyboardInterrupt:
                scheduler.stop()
        else:
            # Interactive mode
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