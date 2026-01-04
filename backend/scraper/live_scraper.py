"""
Live UFC scraper for new events after Greko's comprehensive data load
Only scrapes events that aren't already in the database
"""

import sys
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import json
import string
from datetime import datetime
from sqlalchemy import text

# Add parent directory to path to access backend modules
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from database_integration import DatabaseIntegration
from db.database import engine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class LiveUFCScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.db = DatabaseIntegration()
        self.existing_ids = set()  # Track existing IDs to ensure uniqueness
    
    def generate_alphanumeric_id(self):
        """Generate a random 6-character alphanumeric ID."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=6))
    
    def get_unique_id(self):
        """Generate a unique alphanumeric ID that doesn't exist in database or current batch."""
        while True:
            new_id = self.generate_alphanumeric_id()
            if new_id not in self.existing_ids:
                self.existing_ids.add(new_id)
                return new_id
    
    def load_existing_ids(self):
        """Load all existing IDs from database to prevent duplicates."""
        try:
            tables = ['event_details', 'fighter_details', 'fighter_tott', 'fight_details', 'fight_results', 'fight_stats']
            with engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f"SELECT id FROM {table}"))
                        for row in result:
                            self.existing_ids.add(row[0])
                    except Exception:
                        # Table might not exist yet, skip
                        continue
            logging.info(f"Loaded {len(self.existing_ids)} existing IDs from database")
        except Exception as e:
            logging.warning(f"Could not load existing IDs: {e}")

    def scrape_fighter_career_stats(self, fighter_url):
        """
        Scrape career statistics from fighter profile page

        Returns dict with keys:
            - slpm: Significant Strikes Landed per Minute
            - str_acc: Striking Accuracy %
            - sapm: Significant Strikes Absorbed per Minute
            - str_def: Striking Defense %
            - td_avg: Takedowns Average per 15 min
            - td_acc: Takedown Accuracy %
            - td_def: Takedown Defense %
            - sub_avg: Submission Average per 15 min
        """
        try:
            # Rate limiting
            time.sleep(random.uniform(2, 4))

            response = self.session.get(fighter_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('li', class_='b-list__box-list-item')

            stats = {}
            for item in items:
                # Label is in <i> tag
                label_elem = item.find('i', class_='b-list__box-item-title')
                if label_elem:
                    label = label_elem.text.strip().rstrip(':')
                    # Value is the text after the <i> tag
                    full_text = item.get_text()
                    value = full_text.replace(label_elem.text, '').strip()
                    if value:
                        stats[label] = value

            # Map UFC labels to database columns
            return {
                'slpm': stats.get('SLpM'),
                'str_acc': stats.get('Str. Acc.'),
                'sapm': stats.get('SApM'),
                'str_def': stats.get('Str. Def'),
                'td_avg': stats.get('TD Avg.'),
                'td_acc': stats.get('TD Acc.'),
                'td_def': stats.get('TD Def.'),
                'sub_avg': stats.get('Sub. Avg.')
            }

        except Exception as e:
            logging.error(f"Error scraping fighter stats from {fighter_url}: {e}")
            return None
        
    def get_existing_events(self):
        """Get list of event URLs already in database"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text('SELECT "URL" FROM event_details WHERE "URL" IS NOT NULL'))
                return {row[0] for row in result}
        except Exception as e:
            logging.error(f"Error getting existing events: {e}")
            return set()
    
    def scrape_events_page(self):
        """Scrape the main UFC events page to find new events"""
        url = "http://ufcstats.com/statistics/events/completed?page=all"
        
        try:
            logging.info(f"Scraping events from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Find the events table (try multiple selectors)
            table = soup.find('table', class_='b-statistics__table')
            if not table:
                # Try alternative selector
                table = soup.find('table')
                if not table:
                    logging.warning("Could not find events table")
                    return events
                else:
                    logging.info("Using alternative table selector")
                
            # Find table rows (try multiple selectors)
            tbody = table.find('tbody') if table.find('tbody') else table
            rows = tbody.find_all('tr', class_='b-statistics__table-row')
            if not rows:
                # Try alternative selector
                rows = tbody.find_all('tr')
                logging.info(f"Using alternative row selector, found {len(rows)} rows")
            
            for row in rows:
                try:
                    # Extract event data
                    cells = row.find_all('td', class_='b-statistics__table-col')
                    if not cells:
                        # Try alternative selector
                        cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                        
                    name_cell = cells[0]
                    event_link = name_cell.find('a', class_='b-link')
                    
                    if event_link:
                        event_name = event_link.text.strip()
                        event_url = event_link.get('href')
                        
                        # Parse date and location
                        date_text = cells[0].find_all('span')[0].text.strip() if cells[0].find_all('span') else ""
                        location_text = cells[1].text.strip()
                        
                        # Parse date
                        event_date = None
                        if date_text:
                            try:
                                event_date = pd.to_datetime(date_text).date()
                            except:
                                pass
                        
                        events.append({
                            'name': event_name,
                            'url': event_url,
                            'date': event_date,
                            'location': location_text
                        })
                        
                except Exception as e:
                    logging.warning(f"Error parsing event row: {e}")
                    continue
            
            logging.info(f"Found {len(events)} events on page")
            return events
            
        except Exception as e:
            logging.error(f"Error scraping events page: {e}")
            return []
    
    def find_new_events(self):
        """Find events that aren't in our database yet"""
        existing_urls = self.get_existing_events()
        all_events = self.scrape_events_page()
        
        new_events = []
        for event in all_events:
            if event['url'] not in existing_urls:
                new_events.append(event)
        
        logging.info(f"Found {len(new_events)} new events out of {len(all_events)} total")
        return new_events
    
    def scrape_event_fights(self, event_url):
        """Scrape fights for a specific event"""
        try:
            logging.info(f"Scraping fights from: {event_url}")
            
            # Add delay to be respectful
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(event_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            fights = []
            
            # Find fights table
            table = soup.find('table', class_='b-fight-details__table')
            if not table:
                logging.warning(f"No fights table found for {event_url}")
                return fights
            
            rows = table.find('tbody').find_all('tr', class_='b-fight-details__table-row')
            
            for row in rows:
                try:
                    cells = row.find_all('td', class_='b-fight-details__table-col')
                    if len(cells) < 2:
                        continue
                    
                    # Get fight link
                    fight_link = cells[0].find('a', class_='b-flag')
                    if not fight_link:
                        continue
                        
                    fight_url = fight_link.get('href')
                    
                    # Extract fighter names from the fight link
                    fighters_text = fight_link.text.strip()
                    # Typically format: "Fighter A vs. Fighter B"
                    if ' vs. ' in fighters_text:
                        fighter_names = fighters_text.split(' vs. ')
                        fighter_a = fighter_names[0].strip()
                        fighter_b = fighter_names[1].strip() if len(fighter_names) > 1 else ""
                    else:
                        fighter_a = fighters_text
                        fighter_b = ""
                    
                    fights.append({
                        'fighter_a_name': fighter_a,
                        'fighter_b_name': fighter_b,
                        'url': fight_url
                    })
                    
                except Exception as e:
                    logging.warning(f"Error parsing fight row: {e}")
                    continue
            
            logging.info(f"Found {len(fights)} fights for event")
            return fights
            
        except Exception as e:
            logging.error(f"Error scraping event fights: {e}")
            return []
    
    def store_new_events(self, events):
        """Store new events in database with alphanumeric IDs"""
        if not events:
            return
        
        try:
            with engine.connect() as conn:
                inserted_count = 0
                for event in events:
                    # Generate unique ID for this event
                    event_id = self.get_unique_id()
                    
                    # Prepare event data with proper date parsing
                    date_str = str(event.get('date')) if event.get('date') else None
                    date_proper = None

                    # Try to parse date_proper from DATE field
                    if date_str:
                        try:
                            # Handle formats like "2025-11-22" or "November 22, 2025"
                            if '-' in date_str and len(date_str) == 10:
                                # Already in YYYY-MM-DD format
                                date_proper = date_str
                            else:
                                # Try parsing other formats
                                from dateutil import parser
                                parsed_date = parser.parse(date_str)
                                date_proper = parsed_date.strftime('%Y-%m-%d')
                        except:
                            # If parsing fails, leave date_proper as None
                            pass

                    event_data = {
                        'id': event_id,
                        'EVENT': event.get('name'),
                        'URL': event.get('url'),
                        'DATE': date_str,
                        'date_proper': date_proper,
                        'LOCATION': event.get('location')
                    }

                    # Insert event with date_proper
                    insert_sql = '''
                        INSERT INTO event_details (id, "EVENT", "URL", "DATE", date_proper, "LOCATION")
                        VALUES (:id, :EVENT, :URL, :DATE, :date_proper, :LOCATION)
                    '''
                    conn.execute(text(insert_sql), event_data)
                    inserted_count += 1
                    
                    # Store mapping for fight foreign keys
                    if not hasattr(self, 'event_id_mapping'):
                        self.event_id_mapping = {}
                    self.event_id_mapping[event.get('name')] = event_id
                
                conn.commit()
                logging.info(f"Stored {inserted_count} new events with alphanumeric IDs")
                
        except Exception as e:
            logging.error(f"Error storing events: {e}")
    
    def store_new_fights(self, fights, event_name):
        """Store new fights in database with alphanumeric IDs"""
        if not fights:
            return
        
        try:
            with engine.connect() as conn:
                inserted_count = 0
                
                # Get event ID for foreign key
                event_id = getattr(self, 'event_id_mapping', {}).get(event_name)
                
                for fight in fights:
                    # Generate unique ID for this fight
                    fight_id = self.get_unique_id()
                    
                    # Prepare fight data
                    fight_data = {
                        'id': fight_id,
                        'EVENT': event_name,
                        'BOUT': f"{fight.get('fighter_a_name', '')} vs. {fight.get('fighter_b_name', '')}",
                        'URL': fight.get('url'),
                        'event_id': event_id
                    }
                    
                    # Insert fight
                    insert_sql = '''
                        INSERT INTO fight_details (id, "EVENT", "BOUT", "URL", event_id)
                        VALUES (:id, :EVENT, :BOUT, :URL, :event_id)
                    '''
                    conn.execute(text(insert_sql), fight_data)
                    inserted_count += 1
                
                conn.commit()
                logging.info(f"Stored {inserted_count} new fights for {event_name} with alphanumeric IDs")
                
        except Exception as e:
            logging.error(f"Error storing fights: {e}")
    
    def run_live_scraping(self):
        """Main method to run live scraping for new events"""
        print("=" * 60)
        print("UFC LIVE SCRAPER - WEEKLY UPDATE CHECK")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        logging.info("Starting live UFC scraping for new events...")
        
        try:
            # Test database connection
            if not self.db.test_connection():
                logging.error("Database connection failed!")
                print("ERROR: Database connection failed!")
                return False
            
            # Load existing IDs to ensure uniqueness
            self.load_existing_ids()
            
            # Find new events
            new_events = self.find_new_events()
            
            if not new_events:
                print("SUCCESS: No new UFC events found - database is up to date!")
                print(f"INFO: Current database contains 744+ events through 2025")
                logging.info("No new events found - database is up to date!")
                return True
            
            # Store new events
            print(f"*** NEW DATA FOUND! {len(new_events)} new UFC events detected:")
            for i, event in enumerate(new_events, 1):
                print(f"   {i}. {event['name']} ({event['date']})")
            print()
            
            self.store_new_events(new_events)
            
            # Scrape fights for each new event
            total_fights = 0
            for event in new_events:
                print(f"PROCESSING: {event['name']}")
                logging.info(f"Processing new event: {event['name']}")
                
                fights = self.scrape_event_fights(event['url'])
                if fights:
                    self.store_new_fights(fights, event['name'])
                    total_fights += len(fights)
                    print(f"   SUCCESS: Added {len(fights)} fights")
                else:
                    print(f"   WARNING: No fights found for this event")
                
                # Be respectful with delays
                time.sleep(random.uniform(2, 5))
            
            print("=" * 60)
            print("*** SUCCESS! NEW UFC DATA ADDED TO DATABASE ***")
            print(f"SUMMARY: Added {len(new_events)} events, {total_fights} fights")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            
            logging.info(f"Live scraping completed successfully! Added {len(new_events)} new events.")
            return True
            
        except Exception as e:
            print("=" * 60)
            print("*** ERROR: Live scraping failed! ***")
            print(f"ERROR DETAILS: {str(e)}")
            print(f"Failed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)
            logging.error(f"Live scraping failed: {e}")
            return False

def main():
    """Run live scraping"""
    scraper = LiveUFCScraper()
    success = scraper.run_live_scraping()
    
    # Additional completion message
    if success:
        print("\nUPDATE CHECK COMPLETE! Your UFC database is up to date.")
    else:
        print("\nUPDATE CHECK FAILED! Check logs for details.")

if __name__ == "__main__":
    main()