"""
Enhanced UFC scraper with incremental updates, error handling, and data validation
Consolidates scraper utilities, data validation, and incremental scraping
"""

import pandas as pd
import numpy as np
import logging
import os
import sys
import time
import random
import json
import re
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
from bs4 import BeautifulSoup

# Add scrape_ufc_stats to path for Greko imports
scraper_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scrape_ufc_stats')
sys.path.append(scraper_dir)
import scrape_ufc_stats_library as greko

class UFCDataValidator:
    """Comprehensive data validator for UFC scraped data"""
    
    def validate_events_data(self, events_df):
        """Validate events DataFrame"""
        results = {'passed': True, 'errors': [], 'warnings': [], 'stats': {}}
        
        if events_df is None or events_df.empty:
            results['passed'] = False
            results['errors'].append("Events DataFrame is None or empty")
            return results
        
        # Expected columns
        expected_columns = ['EVENT', 'URL', 'DATE', 'LOCATION']
        missing_columns = set(expected_columns) - set(events_df.columns)
        
        if missing_columns:
            results['passed'] = False
            results['errors'].append(f"Missing columns: {missing_columns}")
        
        # Validate EVENT column
        if 'EVENT' in events_df.columns:
            null_events = events_df['EVENT'].isnull().sum()
            if null_events > 0:
                results['warnings'].append(f"{null_events} null values in EVENT column")
            
            ufc_events = events_df['EVENT'].str.contains('UFC', case=False, na=False).sum()
            results['stats']['ufc_events'] = ufc_events
        
        # Validate URL column
        if 'URL' in events_df.columns:
            invalid_urls = ~events_df['URL'].str.contains('ufcstats.com', case=False, na=False)
            invalid_count = invalid_urls.sum()
            if invalid_count > 0:
                results['warnings'].append(f"{invalid_count} URLs don't contain 'ufcstats.com'")
        
        # Parse date range
        if 'DATE' in events_df.columns:
            years = []
            for date_str in events_df['DATE'].dropna():
                year_match = re.search(r'(19|20)\d{2}', str(date_str))
                if year_match:
                    years.append(int(year_match.group()))
            
            if years:
                results['stats']['date_range'] = f"{min(years)}-{max(years)}"
                results['stats']['years_covered'] = max(years) - min(years) + 1
        
        results['stats']['total_events'] = len(events_df)
        return results
    
    def validate_fights_data(self, fights_df):
        """Validate fights DataFrame"""
        results = {'passed': True, 'errors': [], 'warnings': [], 'stats': {}}
        
        if fights_df is None or fights_df.empty:
            results['passed'] = False
            results['errors'].append("Fights DataFrame is None or empty")
            return results
        
        # Validate BOUT column
        if 'BOUT' in fights_df.columns:
            vs_pattern = r'.+\s+vs\.?\s+.+'
            valid_bouts = fights_df['BOUT'].str.match(vs_pattern, case=False, na=False)
            invalid_bouts = (~valid_bouts).sum()
            
            if invalid_bouts > 0:
                results['warnings'].append(f"{invalid_bouts} fights don't match 'Fighter vs Fighter' format")
            
            results['stats']['total_fights'] = len(fights_df)
            results['stats']['unique_bouts'] = fights_df['BOUT'].nunique()
        
        # Validate METHOD column
        if 'METHOD' in fights_df.columns:
            methods = fights_df['METHOD'].value_counts()
            results['stats']['finish_methods'] = methods.to_dict()
        
        return results
    
    def generate_validation_report(self, validation_results):
        """Generate comprehensive validation report"""
        report = []
        report.append("="*80)
        report.append("UFC DATA VALIDATION REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*80)
        
        for data_type, results in validation_results.items():
            report.append(f"\n{data_type.upper()} VALIDATION:")
            report.append("-" * 50)
            
            if results['passed']:
                report.append("[PASSED] Validation successful")
            else:
                report.append("[FAILED] Validation failed")
            
            if results['errors']:
                report.append("\nERRORS:")
                for error in results['errors']:
                    report.append(f"  • {error}")
            
            if results['warnings']:
                report.append("\nWARNINGS:")
                for warning in results['warnings']:
                    report.append(f"  • {warning}")
            
            if results['stats']:
                report.append("\nSTATISTICS:")
                for key, value in results['stats'].items():
                    report.append(f"  • {key}: {value}")
        
        return "\n".join(report)

class ScrapingProgress:
    """Progress tracker for scraping operations"""
    
    def __init__(self, total_items, name="items"):
        self.total_items = total_items
        self.current_item = 0
        self.name = name
        self.start_time = datetime.now()
        
    def update(self, increment=1):
        """Update progress counter"""
        self.current_item += increment
        
        log_interval = min(max(self.total_items // 10, 1), 50)
        
        if self.current_item % log_interval == 0 or self.current_item == self.total_items:
            percent = (self.current_item / self.total_items) * 100
            elapsed = datetime.now() - self.start_time
            
            if self.current_item > 0:
                avg_time = elapsed / self.current_item
                remaining = avg_time * (self.total_items - self.current_item)
                eta = datetime.now() + remaining
                
                logging.info(f"Progress: {self.current_item}/{self.total_items} {self.name} "
                           f"({percent:.1f}%) - ETA: {eta.strftime('%H:%M:%S')}")
            else:
                logging.info(f"Progress: {self.current_item}/{self.total_items} {self.name} ({percent:.1f}%)")
    
    def complete(self):
        """Mark progress as complete"""
        elapsed = datetime.now() - self.start_time
        logging.info(f"Completed scraping {self.total_items} {self.name} in {elapsed}")

class EnhancedUFCScraper:
    """
    Enhanced UFC scraper with incremental updates, validation, and error handling
    """
    
    def __init__(self, data_dir="../../scrape_ufc_stats", state_file="scraper_state.json"):
        self.data_dir = data_dir
        self.state_file = os.path.join(data_dir, state_file)
        self.state = self.load_state()
        self.validator = UFCDataValidator()
        self.logger = logging.getLogger(__name__)
        
        # Enhanced session setup
        self.session = self.create_session()
        
        # File paths
        self.files = {
            'events': os.path.join(data_dir, 'ufc_event_details.csv'),
            'fight_details': os.path.join(data_dir, 'ufc_fight_details.csv'),
            'fight_results': os.path.join(data_dir, 'ufc_fight_results.csv'),
            'fight_stats': os.path.join(data_dir, 'ufc_fight_stats.csv'),
            'fighters': os.path.join(data_dir, 'ufc_fighter_details.csv'),
            'fighter_tott': os.path.join(data_dir, 'ufc_fighter_tott.csv')
        }
    
    def create_session(self):
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
    
    def get_soup_enhanced(self, url, delay_range=(0.5, 2.0)):
        """Enhanced get_soup with rate limiting and error handling"""
        try:
            # Rate limiting
            delay = random.uniform(delay_range[0], delay_range[1])
            time.sleep(delay)
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logging.info(f"Successfully scraped: {url}")
            
            return soup
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error scraping {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error scraping {url}: {e}")
            return None
    
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
        
        self.logger.info(f"Logging initialized. Log file: {log_file}")
    
    def load_state(self):
        """Load scraper state from JSON file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logging.info(f"Loaded scraper state: {state}")
                return state
            except Exception as e:
                logging.error(f"Error loading state file: {e}")
        
        return {
            'last_scrape': None,
            'last_event_scraped': None,
            'scraped_event_urls': [],
            'scraped_fight_urls': [],
            'total_events': 0,
            'total_fights': 0
        }
    
    def save_state(self):
        """Save current scraper state to JSON file"""
        try:
            self.state['last_scrape'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logging.info(f"Saved scraper state to {self.state_file}")
        except Exception as e:
            logging.error(f"Error saving state: {e}")
    
    def load_existing_data(self):
        """Load existing CSV files if they exist"""
        existing_data = {}
        
        for name, filepath in self.files.items():
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    existing_data[name] = df
                    logging.info(f"Loaded existing {name}: {len(df)} rows")
                except Exception as e:
                    logging.error(f"Error loading {filepath}: {e}")
                    existing_data[name] = pd.DataFrame()
            else:
                existing_data[name] = pd.DataFrame()
        
        return existing_data
    
    def get_new_events(self, all_events_df):
        """Identify new events that haven't been scraped yet"""
        if all_events_df.empty:
            return pd.DataFrame()
        
        scraped_urls = set(self.state.get('scraped_event_urls', []))
        new_events = all_events_df[~all_events_df['URL'].isin(scraped_urls)]
        
        logging.info(f"Found {len(new_events)} new events out of {len(all_events_df)} total")
        return new_events
    
    def get_recent_events(self, all_events_df, days_back=30):
        """Get events from the last N days for incremental updates"""
        if all_events_df.empty or 'DATE' not in all_events_df.columns:
            return pd.DataFrame()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_events = []
            
            for idx, row in all_events_df.iterrows():
                try:
                    date_str = str(row['DATE'])
                    event_date = pd.to_datetime(date_str, errors='coerce')
                    
                    if pd.notna(event_date) and event_date >= cutoff_date:
                        recent_events.append(row)
                        
                except Exception as e:
                    logging.warning(f"Could not parse date '{row['DATE']}' for event {row['EVENT']}")
                    recent_events.append(row)
            
            recent_df = pd.DataFrame(recent_events) if recent_events else pd.DataFrame()
            logging.info(f"Found {len(recent_df)} events from the last {days_back} days")
            return recent_df
            
        except Exception as e:
            logging.error(f"Error filtering recent events: {e}")
            return all_events_df
    
    def save_dataframe_safely(self, df, filepath, backup=True):
        """Safely save DataFrame to CSV with backup option"""
        try:
            if backup and os.path.exists(filepath):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{filepath}.backup_{timestamp}"
                os.rename(filepath, backup_path)
                logging.info(f"Created backup: {backup_path}")
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            df.to_csv(filepath, index=False)
            logging.info(f"Successfully saved {len(df)} rows to {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save DataFrame to {filepath}: {e}")
            return False
    
    def validate_all_data(self, data_dict):
        """Validate all scraped data"""
        validation_results = {}
        
        if 'events' in data_dict and not data_dict['events'].empty:
            validation_results['events'] = self.validator.validate_events_data(data_dict['events'])
            
        if 'fight_results' in data_dict and not data_dict['fight_results'].empty:
            validation_results['fights'] = self.validator.validate_fights_data(data_dict['fight_results'])
        
        if validation_results:
            report = self.validator.generate_validation_report(validation_results)
            logging.info(f"\n{report}")
            
            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"logs/validation_report_{timestamp}.txt"
            
            try:
                os.makedirs("logs", exist_ok=True)
                with open(report_file, 'w') as f:
                    f.write(report)
                logging.info(f"Validation report saved to: {report_file}")
            except Exception as e:
                logging.error(f"Failed to save validation report: {e}")
        
        return validation_results
    
    def incremental_scrape(self, max_new_events=None, days_back=30, validate_data=True):
        """
        Perform incremental scrape of new UFC data
        
        Arguments:
        max_new_events: maximum number of new events to scrape (None for all)
        days_back: look for events from last N days
        validate_data: whether to run data validation
        
        Returns:
        dict: scraping results summary
        """
        
        results = {
            'success': False,
            'events_scraped': 0,
            'fights_scraped': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Load existing data
            existing_data = self.load_existing_data()
            
            # Get all events from website
            logging.info("Fetching current events list from UFC Stats...")
            events_soup = self.get_soup_enhanced("http://ufcstats.com/statistics/events/completed")
            
            if events_soup is None:
                results['errors'].append("Failed to fetch events page")
                return results
            
            all_events_df = greko.parse_event_details(events_soup)
            
            if all_events_df.empty:
                results['errors'].append("No events found on UFC Stats page")
                return results
            
            # Get events to scrape
            new_events = self.get_new_events(all_events_df)
            recent_events = self.get_recent_events(all_events_df, days_back)
            
            events_to_scrape = pd.concat([new_events, recent_events]).drop_duplicates(subset=['URL'])
            
            if max_new_events:
                events_to_scrape = events_to_scrape.head(max_new_events)
            
            if events_to_scrape.empty:
                logging.info("No new events to scrape")
                results['success'] = True
                return results
            
            logging.info(f"Will scrape {len(events_to_scrape)} events")
            
            # Initialize progress tracker
            progress = ScrapingProgress(len(events_to_scrape), "events")
            
            # Scrape events
            new_fight_details = []
            new_fight_results = []
            new_fight_stats = []
            new_fighter_data = []
            scraped_event_urls = []
            scraped_fight_urls = []
            
            for idx, event in events_to_scrape.iterrows():
                try:
                    event_url = event['URL']
                    logging.info(f"Scraping event: {event['EVENT']}")
                    
                    # Get event page soup
                    event_soup = self.get_soup_enhanced(event_url)
                    if event_soup is None:
                        results['warnings'].append(f"Failed to fetch event: {event['EVENT']}")
                        continue
                    
                    # Parse fight details for this event
                    fight_details = greko.parse_fight_details(event_soup)
                    if not fight_details.empty:
                        new_fight_details.append(fight_details)
                    
                    # Parse fight results
                    fight_results = greko.parse_fight_results(event_soup)
                    if not fight_results.empty:
                        new_fight_results.append(fight_results)
                    
                    # For each fight, get detailed stats
                    if not fight_details.empty:
                        for _, fight in fight_details.iterrows():
                            fight_url = fight['URL']
                            
                            if fight_url in self.state.get('scraped_fight_urls', []):
                                continue
                            
                            fight_soup = self.get_soup_enhanced(fight_url)
                            if fight_soup is None:
                                continue
                            
                            # Parse fight statistics
                            fight_stats = greko.parse_fight_stats(fight_soup)
                            if not fight_stats.empty:
                                new_fight_stats.append(fight_stats)
                            
                            # Parse fighter details from this fight
                            fighter_details = greko.parse_fighter_details(fight_soup)
                            if not fighter_details.empty:
                                new_fighter_data.append(fighter_details)
                            
                            scraped_fight_urls.append(fight_url)
                    
                    scraped_event_urls.append(event_url)
                    results['events_scraped'] += 1
                    progress.update()
                    
                except Exception as e:
                    logging.error(f"Error scraping event {event.get('EVENT', 'Unknown')}: {e}")
                    results['errors'].append(f"Failed to scrape event: {str(e)}")
            
            progress.complete()
            
            # Combine new data with existing data
            updated_data = existing_data.copy()
            
            # Update events data
            if not events_to_scrape.empty:
                updated_data['events'] = pd.concat([
                    existing_data['events'], 
                    events_to_scrape
                ]).drop_duplicates(subset=['URL'], keep='last')
            
            # Update other data types
            data_updates = [
                ('fight_details', new_fight_details),
                ('fight_results', new_fight_results), 
                ('fight_stats', new_fight_stats)
            ]
            
            for data_type, new_data_list in data_updates:
                if new_data_list:
                    new_combined = pd.concat(new_data_list, ignore_index=True)
                    updated_data[data_type] = pd.concat([
                        existing_data[data_type], 
                        new_combined
                    ]).drop_duplicates(subset=['URL'] if 'URL' in new_combined.columns else None, keep='last')
            
            # Handle fighter data
            if new_fighter_data:
                new_fighters = pd.concat(new_fighter_data, ignore_index=True)
                updated_data['fighters'] = pd.concat([
                    existing_data['fighters'], 
                    new_fighters
                ]).drop_duplicates(keep='last')
            
            # Validate data if requested
            if validate_data:
                logging.info("Validating scraped data...")
                self.validate_all_data(updated_data)
            
            # Save updated data
            saved_successfully = True
            for data_type, df in updated_data.items():
                if data_type in self.files and not df.empty:
                    if not self.save_dataframe_safely(df, self.files[data_type]):
                        saved_successfully = False
            
            # Update state
            self.state['scraped_event_urls'].extend(scraped_event_urls)
            self.state['scraped_fight_urls'].extend(scraped_fight_urls)
            self.state['total_events'] = len(updated_data.get('events', []))
            self.state['total_fights'] = len(updated_data.get('fight_details', []))
            
            # Remove duplicates from state
            self.state['scraped_event_urls'] = list(set(self.state['scraped_event_urls']))
            self.state['scraped_fight_urls'] = list(set(self.state['scraped_fight_urls']))
            
            self.save_state()
            
            results['success'] = saved_successfully
            results['fights_scraped'] = len(scraped_fight_urls)
            
            logging.info(f"Incremental scrape completed: {results['events_scraped']} events, {results['fights_scraped']} fights")
            
        except Exception as e:
            logging.error(f"Error during incremental scrape: {e}")
            results['errors'].append(f"Incremental scrape failed: {str(e)}")
        
        return results
    
    def reset_state(self):
        """Reset scraper state to start fresh"""
        self.state = {
            'last_scrape': None,
            'last_event_scraped': None,
            'scraped_event_urls': [],
            'scraped_fight_urls': [],
            'total_events': 0,
            'total_fights': 0
        }
        self.save_state()
        logging.info("Scraper state reset")

def main():
    """Example usage of enhanced scraper"""
    scraper = EnhancedUFCScraper()
    scraper.setup_logging()
    
    # Perform incremental scrape
    results = scraper.incremental_scrape(
        max_new_events=5,  # Limit for testing
        days_back=7,       # Check last week
        validate_data=True
    )
    
    print(f"Scraping results: {results}")

if __name__ == "__main__":
    main()