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
        """Scrape fights for a specific event.

        3.9.1 — Captures full fight metadata from the event page:
        outcome (W/L/D/NC), weight class, method, round, and time.
        These are written to fight_results in store_new_fights().
        """
        try:
            logging.info(f"Scraping fights from: {event_url}")

            time.sleep(random.uniform(1, 3))

            response = self.session.get(event_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            fights = []

            table = soup.find('table', class_='b-fight-details__table')
            if not table:
                logging.warning(f"No fights table found for {event_url}")
                return fights

            rows = table.find('tbody').find_all('tr', class_='b-fight-details__table-row')

            for row in rows:
                try:
                    cells = row.find_all('td', class_='b-fight-details__table-col')
                    if len(cells) < 5:
                        continue

                    # Cell 0: fight result flag + fight URL + fighter names
                    fight_link = cells[0].find('a', class_='b-flag')
                    if not fight_link:
                        continue

                    fight_url = fight_link.get('href')

                    # Outcome from flag CSS class (green = fighter A won)
                    flag_classes = fight_link.get('class', [])
                    if 'b-flag_style_green' in flag_classes:
                        outcome = 'W/L'
                    elif 'b-flag_style_red' in flag_classes:
                        outcome = 'L/W'
                    elif 'b-flag_style_draw' in flag_classes:
                        outcome = 'D/D'
                    elif 'b-flag_style_nc' in flag_classes:
                        outcome = 'NC/NC'
                    else:
                        outcome = ''

                    # Fighter names from the link text ("Fighter A vs. Fighter B")
                    fighters_text = fight_link.text.strip()
                    if ' vs. ' in fighters_text:
                        parts = fighters_text.split(' vs. ')
                        fighter_a = parts[0].strip()
                        fighter_b = parts[1].strip() if len(parts) > 1 else ''
                    else:
                        fighter_a = fighters_text
                        fighter_b = ''

                    # Fighter profile URLs (for tott scraping later)
                    fighter_links = cells[1].find_all('a') if len(cells) > 1 else []
                    fighter_a_url = fighter_links[0].get('href') if len(fighter_links) > 0 else None
                    fighter_b_url = fighter_links[1].get('href') if len(fighter_links) > 1 else None

                    # Cell 1: weight class, Cell 2: method, Cell 3: round, Cell 4: time
                    weight_class = cells[1].text.strip() if len(cells) > 1 else ''
                    method       = cells[2].text.strip() if len(cells) > 2 else ''
                    round_num    = cells[3].text.strip().split()[0] if len(cells) > 3 and cells[3].text.strip() else ''
                    time_str     = cells[4].text.strip().split()[0] if len(cells) > 4 and cells[4].text.strip() else ''

                    fights.append({
                        'fighter_a_name': fighter_a,
                        'fighter_b_name': fighter_b,
                        'fighter_a_url':  fighter_a_url,
                        'fighter_b_url':  fighter_b_url,
                        'fight_url':      fight_url,
                        'outcome':        outcome,
                        'weight_class':   weight_class,
                        'method':         method,
                        'round':          round_num,
                        'time':           time_str,
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
    
    def store_new_fights(self, fights, event_name, event_id):
        """Store new fights and their results in fight_details + fight_results.

        3.9.1 — Now also writes OUTCOME, METHOD, WEIGHTCLASS, ROUND, TIME to
        fight_results.  Returns list of (fight_dict, fight_id) tuples so the
        caller can use fight_id when saving per-round stats.
        """
        if not fights:
            return []

        stored = []

        try:
            with engine.connect() as conn:
                for fight in fights:
                    fight_id  = self.get_unique_id()
                    result_id = self.get_unique_id()

                    bout_str = (
                        f"{fight.get('fighter_a_name', '')} vs. "
                        f"{fight.get('fighter_b_name', '')}"
                    )

                    # fight_details
                    conn.execute(text("""
                        INSERT INTO fight_details (id, "EVENT", "BOUT", "URL", event_id)
                        VALUES (:id, :event, :bout, :url, :event_id)
                    """), {
                        'id':       fight_id,
                        'event':    event_name,
                        'bout':     bout_str,
                        'url':      fight.get('fight_url'),
                        'event_id': event_id,
                    })

                    # fight_results (3.9.1)
                    round_val = None
                    if fight.get('round'):
                        try:
                            round_val = int(fight['round'])
                        except (ValueError, TypeError):
                            pass

                    conn.execute(text("""
                        INSERT INTO fight_results
                            (id, "EVENT", "BOUT", "OUTCOME", "WEIGHTCLASS",
                             "METHOD", "ROUND", "TIME", event_id, fight_id)
                        VALUES
                            (:id, :event, :bout, :outcome, :weightclass,
                             :method, :round, :time, :event_id, :fight_id)
                    """), {
                        'id':          result_id,
                        'event':       event_name,
                        'bout':        bout_str,
                        'outcome':     fight.get('outcome', ''),
                        'weightclass': fight.get('weight_class', ''),
                        'method':      fight.get('method', ''),
                        'round':       round_val,
                        'time':        fight.get('time', ''),
                        'event_id':    event_id,
                        'fight_id':    fight_id,
                    })

                    stored.append((fight, fight_id))

                conn.commit()
                logging.info(
                    f"Stored {len(stored)} fights + results for {event_name}"
                )

        except Exception as e:
            logging.error(f"Error storing fights: {e}")

        return stored
    
    # ------------------------------------------------------------------
    # 3.9.2 — fight_stats: per-round statistics from individual fight pages
    # ------------------------------------------------------------------

    def _parse_fighter_tott(self, fighter_div):
        """Parse Tale of the Tape block from a fight detail page."""
        tott = {}
        try:
            name_elem = fighter_div.find('h3', class_='b-fight-details__person-name')
            if name_elem:
                name_link = name_elem.find('a')
                if name_link:
                    tott['name'] = name_link.text.strip()
                    tott['url']  = name_link.get('href')

            stats_list = fighter_div.find('ul', class_='b-list__box-list')
            if stats_list:
                for item in stats_list.find_all('li', class_='b-list__box-list-item'):
                    label_elem = item.find('i')
                    if label_elem:
                        label = label_elem.text.strip().rstrip(':')
                        value = item.get_text().replace(label_elem.text, '').strip()
                        if 'Height' in label:
                            tott['height'] = value
                        elif 'Weight' in label:
                            tott['weight'] = value
                        elif 'Reach' in label:
                            tott['reach']  = value
                        elif 'STANCE' in label:
                            tott['stance'] = value
                        elif 'DOB' in label:
                            tott['dob']    = value
        except Exception as e:
            logging.warning(f"Error parsing fighter TOTT: {e}")
        return tott

    def _parse_round_stats_row(self, row, round_num='1'):
        """Parse one fighter's stats from a round stats table row."""
        try:
            cells = row.find_all('td', class_='b-fight-details__table-col')
            if not cells:
                cells = row.find_all('td')
            if len(cells) < 9:
                return None

            stats = {
                'fighter':     cells[0].text.strip(),
                'round':       round_num,
                'kd':          cells[1].text.strip(),
                'sig_str':     cells[2].text.strip(),
                'sig_str_pct': cells[3].text.strip(),
                'total_str':   cells[4].text.strip(),
                'td':          cells[5].text.strip(),
                'td_pct':      cells[6].text.strip(),
                'sub_att':     cells[7].text.strip(),
                'rev':         cells[8].text.strip(),
                'ctrl':        cells[9].text.strip() if len(cells) > 9 else '',
                'head':        cells[10].text.strip() if len(cells) > 10 else '',
                'body':        cells[11].text.strip() if len(cells) > 11 else '',
                'leg':         cells[12].text.strip() if len(cells) > 12 else '',
                'distance':    cells[13].text.strip() if len(cells) > 13 else '',
                'clinch':      cells[14].text.strip() if len(cells) > 14 else '',
                'ground':      cells[15].text.strip() if len(cells) > 15 else '',
            }
            return stats
        except Exception as e:
            logging.warning(f"Error parsing round stats row: {e}")
            return None

    def scrape_fight_detail_stats(self, fight_url):
        """Visit an individual fight page and scrape TOTT + round-by-round stats."""
        empty = {'fighter_a_tott': {}, 'fighter_b_tott': {}, 'round_stats': []}
        try:
            time.sleep(random.uniform(1.5, 3.0))
            response = self.session.get(fight_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            result = {'fighter_a_tott': {}, 'fighter_b_tott': {}, 'round_stats': []}

            # Tale of the Tape
            tott_section = soup.find('div', class_='b-fight-details__persons')
            if tott_section:
                fighters = tott_section.find_all('div', class_='b-fight-details__person')
                if len(fighters) >= 2:
                    result['fighter_a_tott'] = self._parse_fighter_tott(fighters[0])
                    result['fighter_b_tott'] = self._parse_fighter_tott(fighters[1])

            # Round-by-round stats
            for section in soup.find_all('p', class_='b-fight-details__table-text'):
                section_text = section.text.strip()
                round_num = '1'
                if 'Round' in section_text:
                    parts = section_text.split()
                    for i, part in enumerate(parts):
                        if part == 'Round' and i + 1 < len(parts):
                            round_num = parts[i + 1]
                            break

                table = section.find_next('table', class_='b-fight-details__table')
                if not table:
                    continue
                tbody = table.find('tbody')
                if not tbody:
                    continue

                rows = tbody.find_all('tr', class_='b-fight-details__table-row') or tbody.find_all('tr')
                for row in rows:
                    stats = self._parse_round_stats_row(row, round_num)
                    if stats:
                        result['round_stats'].append(stats)

            return result

        except Exception as e:
            logging.error(f"Error scraping fight detail stats from {fight_url}: {e}")
            return empty

    def store_fight_stats(self, event_id, event_name, fight_id, bout_str, round_stats):
        """Write per-round stats to fight_stats table."""
        if not round_stats:
            return
        try:
            with engine.connect() as conn:
                for stats in round_stats:
                    stats_id = self.get_unique_id()
                    conn.execute(text("""
                        INSERT INTO fight_stats
                            (id, "EVENT", "BOUT", "ROUND", "FIGHTER",
                             "KD", "SIG.STR.", "SIG.STR. %", "TOTAL STR.",
                             "TD", "TD %", "SUB.ATT", "REV.", "CTRL",
                             "HEAD", "BODY", "LEG", "DISTANCE", "CLINCH", "GROUND",
                             event_id, fight_id)
                        VALUES
                            (:id, :event, :bout, :round, :fighter,
                             :kd, :sig_str, :sig_str_pct, :total_str,
                             :td, :td_pct, :sub_att, :rev, :ctrl,
                             :head, :body, :leg, :distance, :clinch, :ground,
                             :event_id, :fight_id)
                    """), {
                        'id':          stats_id,
                        'event':       event_name,
                        'bout':        bout_str,
                        'round':       stats.get('round', '1'),
                        'fighter':     stats.get('fighter', ''),
                        'kd':          stats.get('kd', ''),
                        'sig_str':     stats.get('sig_str', ''),
                        'sig_str_pct': stats.get('sig_str_pct', ''),
                        'total_str':   stats.get('total_str', ''),
                        'td':          stats.get('td', ''),
                        'td_pct':      stats.get('td_pct', ''),
                        'sub_att':     stats.get('sub_att', ''),
                        'rev':         stats.get('rev', ''),
                        'ctrl':        stats.get('ctrl', ''),
                        'head':        stats.get('head', ''),
                        'body':        stats.get('body', ''),
                        'leg':         stats.get('leg', ''),
                        'distance':    stats.get('distance', ''),
                        'clinch':      stats.get('clinch', ''),
                        'ground':      stats.get('ground', ''),
                        'event_id':    event_id,
                        'fight_id':    fight_id,
                    })
                conn.commit()
                logging.info(
                    f"Stored {len(round_stats)} round-stat rows for fight {fight_id}"
                )
        except Exception as e:
            logging.error(f"Error storing fight stats: {e}")

    # ------------------------------------------------------------------
    # 3.9.3 — fighter_details + fighter_tott: create profiles for new fighters
    # ------------------------------------------------------------------

    def get_or_create_fighter(self, fighter_name, fighter_url=None):
        """Return existing fighter_details.id or insert a new row."""
        try:
            name_parts = fighter_name.strip().split()
            first = name_parts[0] if name_parts else fighter_name
            last  = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            with engine.connect() as conn:
                row = conn.execute(text("""
                    SELECT id FROM fighter_details
                    WHERE "FIRST" = :first AND "LAST" = :last
                """), {'first': first, 'last': last}).fetchone()

                if row:
                    return row[0]

                fighter_id = self.get_unique_id()
                conn.execute(text("""
                    INSERT INTO fighter_details (id, "FIRST", "LAST", "URL")
                    VALUES (:id, :first, :last, :url)
                """), {'id': fighter_id, 'first': first, 'last': last, 'url': fighter_url})
                conn.commit()
                logging.info(f"New fighter created: {fighter_name} ({fighter_id})")
                return fighter_id

        except Exception as e:
            logging.error(f"Error getting/creating fighter '{fighter_name}': {e}")
            return None

    def store_fighter_tott(self, fighter_name, tott_data):
        """Upsert fighter Tale of the Tape (height, weight, reach, stance, DOB)."""
        if not tott_data or not fighter_name:
            return
        try:
            fighter_id = self.get_or_create_fighter(
                fighter_name, tott_data.get('url')
            )
            if not fighter_id:
                return

            with engine.connect() as conn:
                existing = conn.execute(text("""
                    SELECT id FROM fighter_tott WHERE fighter_id = :fid
                """), {'fid': fighter_id}).fetchone()

                params = {
                    'fighter':    fighter_name,
                    'height':     tott_data.get('height', ''),
                    'weight':     tott_data.get('weight', ''),
                    'reach':      tott_data.get('reach',  ''),
                    'stance':     tott_data.get('stance', ''),
                    'dob':        tott_data.get('dob',    ''),
                    'url':        tott_data.get('url',    ''),
                    'fighter_id': fighter_id,
                }

                if existing:
                    conn.execute(text("""
                        UPDATE fighter_tott
                        SET "FIGHTER"=:fighter, "HEIGHT"=:height, "WEIGHT"=:weight,
                            "REACH"=:reach, "STANCE"=:stance, "DOB"=:dob, "URL"=:url
                        WHERE fighter_id=:fighter_id
                    """), params)
                else:
                    tott_id = self.get_unique_id()
                    params['id'] = tott_id
                    conn.execute(text("""
                        INSERT INTO fighter_tott
                            (id, "FIGHTER", "HEIGHT", "WEIGHT", "REACH",
                             "STANCE", "DOB", "URL", fighter_id)
                        VALUES
                            (:id, :fighter, :height, :weight, :reach,
                             :stance, :dob, :url, :fighter_id)
                    """), params)

                conn.commit()

        except Exception as e:
            logging.error(f"Error storing fighter tott for '{fighter_name}': {e}")

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

            # Scrape fights, results, stats, and fighter profiles for each new event
            total_fights = 0
            for event in new_events:
                print(f"PROCESSING: {event['name']}")
                logging.info(f"Processing new event: {event['name']}")

                event_id = getattr(self, 'event_id_mapping', {}).get(event['name'])

                # 3.9.1 — scrape fight list with results
                fights = self.scrape_event_fights(event['url'])
                if not fights:
                    print(f"   WARNING: No fights found for this event")
                    continue

                # 3.9.1 — store fight_details + fight_results
                stored_fights = self.store_new_fights(fights, event['name'], event_id)
                total_fights += len(stored_fights)
                print(f"   Stored {len(stored_fights)} fights — scraping per-fight details...")

                for fight_data, fight_id in stored_fights:
                    bout_str = (
                        f"{fight_data['fighter_a_name']} vs. "
                        f"{fight_data['fighter_b_name']}"
                    )

                    # 3.9.2 — visit individual fight page for round stats + tott
                    detail = self.scrape_fight_detail_stats(fight_data['fight_url'])

                    # 3.9.2 — store fight_stats
                    if detail.get('round_stats'):
                        self.store_fight_stats(
                            event_id, event['name'], fight_id,
                            bout_str, detail['round_stats']
                        )

                    # 3.9.3 — upsert fighter_tott (creates fighter_details if new)
                    if detail.get('fighter_a_tott'):
                        self.store_fighter_tott(
                            fight_data['fighter_a_name'], detail['fighter_a_tott']
                        )
                    if detail.get('fighter_b_tott'):
                        self.store_fighter_tott(
                            fight_data['fighter_b_name'], detail['fighter_b_tott']
                        )

                print(f"   SUCCESS: {event['name']} fully scraped")

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