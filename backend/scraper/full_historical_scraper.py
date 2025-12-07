"""
Full Historical UFC Scraper
Complete rescrape of all UFC events from UFCStats.com

This script performs a one-time complete scrape of all UFC historical data.
It populates all database tables with comprehensive fight data.

Progress Tracking:
- Console output shows current event being processed
- Log file (full_scraper.log) contains detailed progress
- Periodic database commits save progress incrementally
- Can resume if interrupted (skips already-scraped events)

Usage:
    python full_historical_scraper.py --dry-run    # Preview what will be scraped
    python full_historical_scraper.py --clear-db   # Clear existing data first
    python full_historical_scraper.py              # Start scraping (keeps existing data)
"""

import sys
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import string
import argparse
from datetime import datetime
from sqlalchemy import text
from tqdm import tqdm  # Progress bar library

# Add parent directory to path to access backend modules
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db.database import engine, SessionLocal

# Setup logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class FullHistoricalScraper:
    """
    Complete UFC historical data scraper

    Scrapes all events from UFCStats.com and populates database tables:
    - event_details: Event information and dates
    - fighter_details: Fighter profiles
    - fight_details: Fight matchups
    - fight_results: Fight outcomes and methods
    - fighter_tott: Tale of the Tape (physical stats)
    - fight_stats: Round-by-round statistics
    """

    def __init__(self, dry_run=False):
        """
        Initialize scraper

        Args:
            dry_run: If True, only preview what would be scraped without saving to DB
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.dry_run = dry_run
        self.existing_ids = set()  # Track all IDs to prevent duplicates

        # Statistics tracking
        self.stats = {
            'events_processed': 0,
            'fights_processed': 0,
            'fighters_added': 0,
            'errors': 0
        }

        logging.info("Initialized Full Historical Scraper")
        if dry_run:
            logging.info("DRY RUN MODE - No data will be saved to database")

    def generate_alphanumeric_id(self):
        """
        Generate a random 6-character alphanumeric ID
        Format: Uppercase letters and digits (e.g., 'A3K9M2')
        """
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=6))

    def get_unique_id(self):
        """
        Generate a unique alphanumeric ID that doesn't exist in database or current batch
        Checks against existing_ids set to prevent collisions
        """
        while True:
            new_id = self.generate_alphanumeric_id()
            if new_id not in self.existing_ids:
                self.existing_ids.add(new_id)
                return new_id

    def load_existing_ids(self):
        """
        Load all existing IDs from database to prevent duplicates
        Called at startup to populate existing_ids set
        """
        if self.dry_run:
            logging.info("Dry run mode - skipping existing ID load")
            return

        try:
            tables = ['event_details', 'fighter_details', 'fighter_tott',
                     'fight_details', 'fight_results', 'fight_stats']

            with engine.connect() as conn:
                for table in tables:
                    try:
                        result = conn.execute(text(f"SELECT id FROM {table}"))
                        for row in result:
                            self.existing_ids.add(row[0])
                    except Exception as e:
                        # Table might not exist yet, that's okay
                        logging.warning(f"Could not load IDs from {table}: {e}")
                        continue

            logging.info(f"Loaded {len(self.existing_ids)} existing IDs from database")
        except Exception as e:
            logging.error(f"Error loading existing IDs: {e}")

    def get_existing_event_urls(self):
        """
        Get set of event URLs already in database
        Used to skip events that have already been scraped
        """
        if self.dry_run:
            return set()

        try:
            with engine.connect() as conn:
                result = conn.execute(text('SELECT "URL" FROM event_details WHERE "URL" IS NOT NULL'))
                return {row[0] for row in result}
        except Exception as e:
            logging.error(f"Error getting existing events: {e}")
            return set()

    def scrape_all_events_list(self):
        """
        Scrape the main UFC events page to get list of all events

        Returns:
            List of dicts with event metadata:
            - name: Event name
            - url: Link to event details page
            - date: Event date (parsed)
            - location: Event location
        """
        url = "http://ufcstats.com/statistics/events/completed?page=all"

        try:
            logging.info(f"Fetching event list from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            events = []

            # Find the events table
            table = soup.find('table', class_='b-statistics__table')
            if not table:
                table = soup.find('table')
                if not table:
                    logging.error("Could not find events table on page")
                    return events

            # Find all event rows
            tbody = table.find('tbody') if table.find('tbody') else table
            rows = tbody.find_all('tr', class_='b-statistics__table-row')
            if not rows:
                rows = tbody.find_all('tr')

            logging.info(f"Found {len(rows)} event rows to parse")

            # Parse each event row
            for row in rows:
                try:
                    cells = row.find_all('td', class_='b-statistics__table-col')
                    if not cells:
                        cells = row.find_all('td')
                    if len(cells) < 2:
                        continue

                    # Extract event name and URL
                    name_cell = cells[0]
                    event_link = name_cell.find('a', class_='b-link')

                    if event_link:
                        event_name = event_link.text.strip()
                        event_url = event_link.get('href')

                        # Extract date from span within same cell
                        date_text = ""
                        date_spans = cells[0].find_all('span')
                        if date_spans:
                            date_text = date_spans[0].text.strip()

                        # Extract location from second column
                        location_text = cells[1].text.strip()

                        # Parse date string to date object
                        event_date = None
                        if date_text:
                            try:
                                event_date = pd.to_datetime(date_text).date()
                            except:
                                logging.warning(f"Could not parse date: {date_text}")

                        events.append({
                            'name': event_name,
                            'url': event_url,
                            'date': event_date,
                            'location': location_text
                        })

                except Exception as e:
                    logging.warning(f"Error parsing event row: {e}")
                    continue

            logging.info(f"Successfully parsed {len(events)} events")
            return events

        except Exception as e:
            logging.error(f"Error scraping events list: {e}")
            return []

    def scrape_event_fights_list(self, event_url):
        """
        Scrape list of fights for a specific event

        Args:
            event_url: URL to event details page

        Returns:
            List of dicts with fight data:
            - fighter_a_name: First fighter name
            - fighter_b_name: Second fighter name
            - fight_url: Link to detailed fight page
            - result: Win/Loss format (e.g., 'W/L')
            - method: Finish method (KO, Sub, Decision, etc.)
            - round: Round finished
            - time: Time in round
            - weight_class: Weight class of fight
        """
        try:
            # Rate limiting - be respectful to the website
            time.sleep(random.uniform(1.5, 3.0))

            response = self.session.get(event_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            fights = []

            # Find the fights table
            table = soup.find('table', class_='b-fight-details__table')
            if not table:
                logging.warning(f"No fights table found for {event_url}")
                return fights

            tbody = table.find('tbody')
            if not tbody:
                logging.warning(f"No tbody found in fights table for {event_url}")
                return fights

            rows = tbody.find_all('tr', class_='b-fight-details__table-row')

            # Parse each fight row
            for row in rows:
                try:
                    cells = row.find_all('td', class_='b-fight-details__table-col')
                    if len(cells) < 7:
                        continue

                    # Column 0: Result and fighters
                    fight_link = cells[0].find('a', class_='b-flag')
                    if not fight_link:
                        continue

                    fight_url = fight_link.get('href')

                    # Parse fighter names from link text (format: "Fighter A  vs. Fighter B")
                    fighters_text = fight_link.text.strip()
                    if ' vs. ' in fighters_text:
                        parts = fighters_text.split(' vs. ')
                        fighter_a = parts[0].strip()
                        fighter_b = parts[1].strip() if len(parts) > 1 else ""
                    else:
                        fighter_a = fighters_text
                        fighter_b = ""

                    # Column 0 also contains result (W/L)
                    result_icons = cells[0].find_all('i')
                    result = ""
                    if len(result_icons) >= 2:
                        # Icons show win/loss for each fighter
                        fighter_a_result = 'W' if 'win' in result_icons[0].get('class', []) else 'L'
                        fighter_b_result = 'W' if 'win' in result_icons[1].get('class', []) else 'L'
                        result = f"{fighter_a_result}/{fighter_b_result}"

                    # Column 1: Weight class
                    weight_class = cells[1].text.strip()

                    # Column 2: Method
                    method = cells[2].text.strip()

                    # Column 3: Round
                    round_num = cells[3].text.strip()

                    # Column 4: Time
                    time_str = cells[4].text.strip()

                    fights.append({
                        'fighter_a_name': fighter_a,
                        'fighter_b_name': fighter_b,
                        'fight_url': fight_url,
                        'result': result,
                        'method': method,
                        'round': round_num,
                        'time': time_str,
                        'weight_class': weight_class
                    })

                except Exception as e:
                    logging.warning(f"Error parsing fight row: {e}")
                    continue

            return fights

        except Exception as e:
            logging.error(f"Error scraping fights from {event_url}: {e}")
            return []

    def scrape_fight_details(self, fight_url):
        """
        Scrape detailed statistics from individual fight page

        Args:
            fight_url: URL to fight details page

        Returns:
            Dict with:
            - fighter_a_tott: Tale of the tape for fighter A
            - fighter_b_tott: Tale of the tape for fighter B
            - round_stats: List of round-by-round stats for both fighters
        """
        try:
            # Rate limiting
            time.sleep(random.uniform(1.5, 3.0))

            response = self.session.get(fight_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            result = {
                'fighter_a_tott': {},
                'fighter_b_tott': {},
                'round_stats': []
            }

            # Scrape Tale of the Tape (fighter physical stats)
            # This appears in a specific section of the page
            tott_section = soup.find('div', class_='b-fight-details__persons')
            if tott_section:
                fighters = tott_section.find_all('div', class_='b-fight-details__person')

                if len(fighters) >= 2:
                    # Fighter A (left side)
                    result['fighter_a_tott'] = self._parse_fighter_tott(fighters[0])
                    # Fighter B (right side)
                    result['fighter_b_tott'] = self._parse_fighter_tott(fighters[1])

            # Scrape round-by-round statistics tables
            # Each round has a separate section with a table
            # Look for section headers to identify round numbers
            sections = soup.find_all('p', class_='b-fight-details__table-text')

            for section in sections:
                # Section header contains "Round X" text
                section_text = section.text.strip()
                round_num = '1'  # Default

                if 'Round' in section_text:
                    # Extract round number from text like "Round 1", "Round 2", etc.
                    parts = section_text.split()
                    for i, part in enumerate(parts):
                        if part == 'Round' and i + 1 < len(parts):
                            round_num = parts[i + 1]
                            break

                # Find the stats table immediately following this section
                table = section.find_next('table', class_='b-fight-details__table')
                if not table:
                    continue

                tbody = table.find('tbody')
                if not tbody:
                    continue

                # Parse each fighter's stats for this round
                rows = tbody.find_all('tr', class_='b-fight-details__table-row')
                if not rows:
                    rows = tbody.find_all('tr')

                for row in rows:
                    round_data = self._parse_round_stats_row(row, round_num)
                    if round_data:
                        result['round_stats'].append(round_data)

            return result

        except Exception as e:
            logging.error(f"Error scraping fight details from {fight_url}: {e}")
            return {
                'fighter_a_tott': {},
                'fighter_b_tott': {},
                'round_stats': []
            }

    def _parse_fighter_tott(self, fighter_div):
        """
        Parse Tale of the Tape data for a single fighter

        Args:
            fighter_div: BeautifulSoup div containing fighter TOTT data

        Returns:
            Dict with height, weight, reach, stance, DOB, etc.
        """
        tott = {}

        try:
            # Fighter name
            name_elem = fighter_div.find('h3', class_='b-fight-details__person-name')
            if name_elem:
                name_link = name_elem.find('a')
                if name_link:
                    tott['name'] = name_link.text.strip()
                    tott['url'] = name_link.get('href')

            # Parse stats list
            stats_list = fighter_div.find('ul', class_='b-list__box-list')
            if stats_list:
                items = stats_list.find_all('li', class_='b-list__box-list-item')

                for item in items:
                    # Label is in the i tag
                    label_elem = item.find('i')
                    if label_elem:
                        label = label_elem.text.strip().rstrip(':')
                        # Value is text after the label
                        full_text = item.get_text()
                        value = full_text.replace(label_elem.text, '').strip()

                        # Map common labels to database fields
                        if 'Height' in label:
                            tott['height'] = value
                        elif 'Weight' in label:
                            tott['weight'] = value
                        elif 'Reach' in label:
                            tott['reach'] = value
                        elif 'STANCE' in label:
                            tott['stance'] = value
                        elif 'DOB' in label:
                            tott['dob'] = value

        except Exception as e:
            logging.warning(f"Error parsing fighter TOTT: {e}")

        return tott

    def _parse_round_stats_row(self, row, round_num='1'):
        """
        Parse a single row from round statistics table

        Args:
            row: BeautifulSoup tr element
            round_num: Round number for this stats row

        Returns:
            Dict with fighter name, round number, and all stats (KD, sig strikes, etc.)
        """
        try:
            cells = row.find_all('td', class_='b-fight-details__table-col')
            if not cells:
                cells = row.find_all('td')

            if len(cells) < 9:
                return None

            # Extract data from each column
            # Column layout on UFCStats.com:
            # 0: Fighter name, 1: KD, 2: Sig str, 3: Sig str %, 4: Total str
            # 5: TD, 6: TD %, 7: Sub att, 8: Rev, 9: Ctrl

            stats = {
                'fighter': cells[0].text.strip(),
                'round': round_num,
                'kd': cells[1].text.strip(),
                'sig_str': cells[2].text.strip(),
                'sig_str_pct': cells[3].text.strip(),
                'total_str': cells[4].text.strip(),
                'td': cells[5].text.strip(),
                'td_pct': cells[6].text.strip(),
                'sub_att': cells[7].text.strip(),
                'rev': cells[8].text.strip(),
                'ctrl': cells[9].text.strip() if len(cells) > 9 else ''
            }

            # Additional detailed striking stats if available (head, body, leg, etc.)
            # These appear in a separate "Significant Strikes" table
            if len(cells) > 10:
                stats['head'] = cells[10].text.strip()
            if len(cells) > 11:
                stats['body'] = cells[11].text.strip()
            if len(cells) > 12:
                stats['leg'] = cells[12].text.strip()
            if len(cells) > 13:
                stats['distance'] = cells[13].text.strip()
            if len(cells) > 14:
                stats['clinch'] = cells[14].text.strip()
            if len(cells) > 15:
                stats['ground'] = cells[15].text.strip()

            return stats

        except Exception as e:
            logging.warning(f"Error parsing round stats row: {e}")
            return None

    def save_event_to_db(self, event_data):
        """
        Save event to event_details table

        Args:
            event_data: Dict with name, url, date, location

        Returns:
            event_id: Generated ID for this event
        """
        if self.dry_run:
            return self.get_unique_id()

        try:
            event_id = self.get_unique_id()

            with engine.connect() as conn:
                # Insert into event_details table
                conn.execute(text("""
                    INSERT INTO event_details (id, "EVENT", "URL", date_proper, "LOCATION")
                    VALUES (:id, :event, :url, :date, :location)
                """), {
                    'id': event_id,
                    'event': event_data['name'],
                    'url': event_data['url'],
                    'date': event_data['date'],
                    'location': event_data['location']
                })
                conn.commit()

            return event_id

        except Exception as e:
            logging.error(f"Error saving event to DB: {e}")
            self.stats['errors'] += 1
            return None

    def get_or_create_fighter(self, fighter_name, fighter_url=None):
        """
        Get existing fighter ID or create new fighter record

        Args:
            fighter_name: Full fighter name
            fighter_url: Optional URL to fighter profile

        Returns:
            fighter_id: Database ID for this fighter
        """
        if self.dry_run:
            return self.get_unique_id()

        try:
            # Parse first and last name
            name_parts = fighter_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = fighter_name
                last_name = ''

            with engine.connect() as conn:
                # Check if fighter already exists
                result = conn.execute(text("""
                    SELECT id FROM fighter_details
                    WHERE "FIRST" = :first AND "LAST" = :last
                """), {'first': first_name, 'last': last_name})

                existing = result.fetchone()
                if existing:
                    return existing[0]

                # Create new fighter record
                fighter_id = self.get_unique_id()
                conn.execute(text("""
                    INSERT INTO fighter_details (id, "FIRST", "LAST", "URL")
                    VALUES (:id, :first, :last, :url)
                """), {
                    'id': fighter_id,
                    'first': first_name,
                    'last': last_name,
                    'url': fighter_url
                })
                conn.commit()

                self.stats['fighters_added'] += 1
                return fighter_id

        except Exception as e:
            logging.error(f"Error getting/creating fighter {fighter_name}: {e}")
            return None

    def save_fighter_tott(self, fighter_name, tott_data):
        """
        Save fighter Tale of the Tape data

        Args:
            fighter_name: Fighter name to link TOTT data to
            tott_data: Dict with height, weight, reach, stance, DOB
        """
        if self.dry_run or not tott_data:
            return

        try:
            # Get or create fighter
            fighter_id = self.get_or_create_fighter(fighter_name, tott_data.get('url'))
            if not fighter_id:
                return

            with engine.connect() as conn:
                # Check if TOTT already exists for this fighter
                result = conn.execute(text("""
                    SELECT id FROM fighter_tott WHERE fighter_id = :fighter_id
                """), {'fighter_id': fighter_id})

                existing = result.fetchone()

                if existing:
                    # Update existing TOTT record
                    conn.execute(text("""
                        UPDATE fighter_tott
                        SET "FIGHTER" = :fighter,
                            "HEIGHT" = :height,
                            "WEIGHT" = :weight,
                            "REACH" = :reach,
                            "STANCE" = :stance,
                            "DOB" = :dob,
                            "URL" = :url
                        WHERE fighter_id = :fighter_id
                    """), {
                        'fighter': fighter_name,
                        'height': tott_data.get('height', ''),
                        'weight': tott_data.get('weight', ''),
                        'reach': tott_data.get('reach', ''),
                        'stance': tott_data.get('stance', ''),
                        'dob': tott_data.get('dob', ''),
                        'url': tott_data.get('url', ''),
                        'fighter_id': fighter_id
                    })
                else:
                    # Create new TOTT record
                    tott_id = self.get_unique_id()
                    conn.execute(text("""
                        INSERT INTO fighter_tott
                        (id, "FIGHTER", "HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB", "URL", fighter_id)
                        VALUES (:id, :fighter, :height, :weight, :reach, :stance, :dob, :url, :fighter_id)
                    """), {
                        'id': tott_id,
                        'fighter': fighter_name,
                        'height': tott_data.get('height', ''),
                        'weight': tott_data.get('weight', ''),
                        'reach': tott_data.get('reach', ''),
                        'stance': tott_data.get('stance', ''),
                        'dob': tott_data.get('dob', ''),
                        'url': tott_data.get('url', ''),
                        'fighter_id': fighter_id
                    })

                conn.commit()

        except Exception as e:
            logging.error(f"Error saving fighter TOTT for {fighter_name}: {e}")
            self.stats['errors'] += 1

    def save_round_stats(self, event_id, event_name, fight_id, bout_str, round_num, stats_data):
        """
        Save round-by-round fight statistics

        Args:
            event_id: Parent event ID
            event_name: Event name
            fight_id: Parent fight ID
            bout_str: Fighter matchup string
            round_num: Round number
            stats_data: Dict with all round statistics
        """
        if self.dry_run or not stats_data:
            return

        try:
            stats_id = self.get_unique_id()

            with engine.connect() as conn:
                # Insert into fight_stats table
                conn.execute(text("""
                    INSERT INTO fight_stats
                    (id, "EVENT", "BOUT", "ROUND", "FIGHTER", "KD", "SIG.STR.", "SIG.STR.%",
                     "TOTAL STR.", "TD", "TD%", "SUB.ATT", "REV.", "CTRL",
                     "HEAD", "BODY", "LEG", "DISTANCE", "CLINCH", "GROUND",
                     event_id, fight_id)
                    VALUES (:id, :event, :bout, :round, :fighter, :kd, :sig_str, :sig_str_pct,
                            :total_str, :td, :td_pct, :sub_att, :rev, :ctrl,
                            :head, :body, :leg, :distance, :clinch, :ground,
                            :event_id, :fight_id)
                """), {
                    'id': stats_id,
                    'event': event_name,
                    'bout': bout_str,
                    'round': round_num,
                    'fighter': stats_data.get('fighter', ''),
                    'kd': stats_data.get('kd', ''),
                    'sig_str': stats_data.get('sig_str', ''),
                    'sig_str_pct': stats_data.get('sig_str_pct', ''),
                    'total_str': stats_data.get('total_str', ''),
                    'td': stats_data.get('td', ''),
                    'td_pct': stats_data.get('td_pct', ''),
                    'sub_att': stats_data.get('sub_att', ''),
                    'rev': stats_data.get('rev', ''),
                    'ctrl': stats_data.get('ctrl', ''),
                    'head': stats_data.get('head', ''),
                    'body': stats_data.get('body', ''),
                    'leg': stats_data.get('leg', ''),
                    'distance': stats_data.get('distance', ''),
                    'clinch': stats_data.get('clinch', ''),
                    'ground': stats_data.get('ground', ''),
                    'event_id': event_id,
                    'fight_id': fight_id
                })
                conn.commit()

        except Exception as e:
            logging.error(f"Error saving round stats: {e}")
            self.stats['errors'] += 1

    def save_fight_to_db(self, event_id, event_name, fight_data, detailed_data=None):
        """
        Save fight and related data to multiple tables

        Args:
            event_id: ID of parent event
            event_name: Name of event
            fight_data: Dict with all fight information
            detailed_data: Optional dict with fighter_a_tott, fighter_b_tott, round_stats
        """
        if self.dry_run:
            return

        try:
            # Generate IDs
            fight_id = self.get_unique_id()
            result_id = self.get_unique_id()

            # Create BOUT string (format: "Fighter A  vs. Fighter B")
            bout_str = f"{fight_data['fighter_a_name']}  vs. {fight_data['fighter_b_name']}"

            with engine.connect() as conn:
                # Insert into fight_details table
                conn.execute(text("""
                    INSERT INTO fight_details (id, "EVENT", "BOUT", "URL", event_id)
                    VALUES (:id, :event, :bout, :url, :event_id)
                """), {
                    'id': fight_id,
                    'event': event_name,
                    'bout': bout_str,
                    'url': fight_data['fight_url'],
                    'event_id': event_id
                })

                # Insert into fight_results table
                conn.execute(text("""
                    INSERT INTO fight_results
                    (id, "EVENT", "BOUT", "OUTCOME", "WEIGHTCLASS", "METHOD", "ROUND", "TIME", event_id, fight_id)
                    VALUES (:id, :event, :bout, :outcome, :weightclass, :method, :round, :time, :event_id, :fight_id)
                """), {
                    'id': result_id,
                    'event': event_name,
                    'bout': bout_str,
                    'outcome': fight_data['result'],
                    'weightclass': fight_data['weight_class'],
                    'method': fight_data['method'],
                    'round': fight_data['round'],
                    'time': fight_data['time'],
                    'event_id': event_id,
                    'fight_id': fight_id
                })

                conn.commit()

            # Save detailed data if available (Tale of the Tape and round stats)
            if detailed_data:
                # Save fighter Tale of the Tape data
                if detailed_data.get('fighter_a_tott'):
                    self.save_fighter_tott(fight_data['fighter_a_name'], detailed_data['fighter_a_tott'])

                if detailed_data.get('fighter_b_tott'):
                    self.save_fighter_tott(fight_data['fighter_b_name'], detailed_data['fighter_b_tott'])

                # Save round-by-round statistics
                if detailed_data.get('round_stats'):
                    for round_stat in detailed_data['round_stats']:
                        # Round stats contain fighter name and round number
                        round_num = round_stat.get('round', '1')
                        self.save_round_stats(event_id, event_name, fight_id, bout_str,
                                            round_num, round_stat)

        except Exception as e:
            logging.error(f"Error saving fight to DB: {e}")
            self.stats['errors'] += 1

    def run_full_scrape(self):
        """
        Main execution method - scrapes all UFC history

        Process:
        1. Get list of all events from UFCStats.com
        2. For each event:
           a. Save event details
           b. Get list of fights
           c. For each fight:
              - Save fight details and results
              - Optionally scrape detailed stats (slower)
        3. Show final statistics
        """
        logging.info("=" * 60)
        logging.info("Starting Full Historical UFC Scrape")
        logging.info("=" * 60)

        # Load existing IDs to prevent duplicates
        self.load_existing_ids()

        # Get list of already-scraped events to skip
        existing_event_urls = self.get_existing_event_urls()
        logging.info(f"Found {len(existing_event_urls)} events already in database")

        # Get complete list of all UFC events
        all_events = self.scrape_all_events_list()
        if not all_events:
            logging.error("Failed to retrieve events list. Exiting.")
            return

        # Filter to only new events (or all if doing fresh scrape)
        events_to_scrape = [e for e in all_events if e['url'] not in existing_event_urls]

        logging.info(f"Total events available: {len(all_events)}")
        logging.info(f"Events to scrape: {len(events_to_scrape)}")

        if self.dry_run:
            logging.info("DRY RUN - Would scrape these events:")
            for event in events_to_scrape[:10]:  # Show first 10
                logging.info(f"  - {event['name']} ({event['date']})")
            if len(events_to_scrape) > 10:
                logging.info(f"  ... and {len(events_to_scrape) - 10} more")
            return

        # Progress bar for events
        logging.info("Beginning event scraping with detailed fight stats...")
        logging.info("NOTE: This will take several hours due to detailed scraping")

        for i, event in enumerate(events_to_scrape, 1):
            try:
                logging.info(f"[{i}/{len(events_to_scrape)}] Processing: {event['name']}")

                # Save event to database
                event_id = self.save_event_to_db(event)
                if not event_id:
                    continue

                # Get fights for this event
                fights = self.scrape_event_fights_list(event['url'])
                logging.info(f"  Found {len(fights)} fights")

                # Save each fight with detailed stats
                for j, fight in enumerate(fights, 1):
                    # Scrape detailed fight statistics (Tale of the Tape and round stats)
                    detailed_data = self.scrape_fight_details(fight['fight_url'])

                    # Save fight with all detailed data
                    self.save_fight_to_db(event_id, event['name'], fight, detailed_data)
                    self.stats['fights_processed'] += 1

                    # Log progress for long events
                    if len(fights) > 10 and j % 5 == 0:
                        logging.info(f"    Fight {j}/{len(fights)} processed")

                self.stats['events_processed'] += 1

                # Log progress every 10 events
                if i % 10 == 0:
                    logging.info(f"Progress: {i}/{len(events_to_scrape)} events processed")
                    logging.info(f"  Total fights: {self.stats['fights_processed']}")
                    logging.info(f"  Fighters added: {self.stats['fighters_added']}")
                    logging.info(f"  Errors: {self.stats['errors']}")

            except Exception as e:
                logging.error(f"Error processing event {event['name']}: {e}")
                self.stats['errors'] += 1
                continue

        # Final statistics
        logging.info("=" * 60)
        logging.info("Scraping Complete!")
        logging.info(f"Events processed: {self.stats['events_processed']}")
        logging.info(f"Fights processed: {self.stats['fights_processed']}")
        logging.info(f"Fighters added: {self.stats['fighters_added']}")
        logging.info(f"Errors encountered: {self.stats['errors']}")
        logging.info("=" * 60)
        logging.info("Database now contains complete UFC historical data!")
        logging.info("Tables populated:")
        logging.info("  - event_details: Event information")
        logging.info("  - fighter_details: Fighter profiles")
        logging.info("  - fighter_tott: Tale of the Tape (physical stats)")
        logging.info("  - fight_details: Fight matchups")
        logging.info("  - fight_results: Fight outcomes")
        logging.info("  - fight_stats: Round-by-round statistics")
        logging.info("=" * 60)

def clear_database():
    """
    Clear all data from UFC tables
    WARNING: This deletes all existing data!
    """
    print("\nWARNING: This will delete ALL existing UFC data from your database.")
    print("Tables to be cleared:")
    print("  - event_details")
    print("  - fight_details")
    print("  - fight_results")
    print("  - fighter_details")
    print("  - fighter_tott")
    print("  - fight_stats")

    response = input("\nType 'DELETE ALL DATA' to confirm: ")

    if response != "DELETE ALL DATA":
        print("Cancelled - no data was deleted")
        return False

    try:
        with engine.connect() as conn:
            tables = ['fight_stats', 'fight_results', 'fight_details',
                     'fighter_tott', 'fighter_details', 'event_details']

            for table in tables:
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                    print(f"Cleared {table}")
                except Exception as e:
                    print(f"Error clearing {table}: {e}")

            conn.commit()
            print("\nAll tables cleared successfully")
            return True

    except Exception as e:
        logging.error(f"Error clearing database: {e}")
        return False

def main():
    """
    Main entry point with command-line argument handling
    """
    parser = argparse.ArgumentParser(
        description='Full historical UFC data scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python full_historical_scraper.py --dry-run    Preview what will be scraped
  python full_historical_scraper.py --clear-db   Clear DB then scrape
  python full_historical_scraper.py              Start scraping
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be scraped without saving to database')
    parser.add_argument('--clear-db', action='store_true',
                       help='Clear all existing data before scraping')

    args = parser.parse_args()

    # Clear database if requested
    if args.clear_db:
        if not clear_database():
            print("Database clear failed or was cancelled")
            return

    # Create scraper instance
    scraper = FullHistoricalScraper(dry_run=args.dry_run)

    # Run the scrape
    scraper.run_full_scrape()

if __name__ == "__main__":
    main()
