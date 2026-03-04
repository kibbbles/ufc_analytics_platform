"""
Live UFC scraper for new events after Greko's comprehensive data load
Only scrapes events that aren't already in the database
"""

import sys
import os
import re
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
        """Scrape the main UFC events page to find new events.

        Mirrors Greco's parse_event_details selectors exactly:
          - EVENT/URL: <a class="b-link b-link_style_black">
          - DATE:      <span class="b-statistics__date"> (Greco's exact class)
          - LOCATION:  <td class="b-statistics__table-col
                           b-statistics__table-col_style_big-top-padding">

        Guard: UFCStats always lists the upcoming (not-yet-completed) event
        first. Greco explicitly drops the first DATE and LOCATION element.
        We skip the first data row to match that behaviour.
        """
        url = "http://ufcstats.com/statistics/events/completed?page=all"

        try:
            logging.info(f"Scraping events from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            events = []

            tbody = soup.find('tbody')
            if not tbody:
                logging.warning("Could not find events table tbody")
                return events

            rows = tbody.find_all('tr', class_='b-statistics__table-row')
            if not rows:
                logging.warning("Could not find event rows")
                return events

            # Greco drops the first element of DATE and LOCATION lists because
            # the first row is always the upcoming (not yet completed) event.
            rows = rows[1:]

            for row in rows:
                try:
                    # EVENT name + URL — Greco: <a class="b-link b-link_style_black">
                    event_link = row.find('a', class_='b-link b-link_style_black')
                    if not event_link:
                        continue

                    event_name = event_link.text.strip()
                    event_url  = event_link.get('href')

                    # DATE — Greco: <span class="b-statistics__date">
                    date_span = row.find('span', class_='b-statistics__date')
                    date_text = date_span.text.strip() if date_span else ''

                    # LOCATION — Greco: <td class="...b-statistics__table-col_style_big-top-padding">
                    location_td = row.find(
                        'td',
                        class_='b-statistics__table-col b-statistics__table-col_style_big-top-padding'
                    )
                    location_text = location_td.text.strip() if location_td else ''

                    event_date = None
                    if date_text:
                        try:
                            event_date = pd.to_datetime(date_text).date()
                        except Exception:
                            pass

                    events.append({
                        'name':     event_name,
                        'url':      event_url,
                        'date':     event_date,
                        'location': location_text,
                    })

                except Exception as e:
                    logging.warning(f"Error parsing event row: {e}")
                    continue

            logging.info(f"Found {len(events)} completed events on page")
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
        """Scrape fight URLs and outcomes from the event listing page.

        Returns minimal stubs only — fight_url and outcome.
        All other metadata (fighter names, weight class, method, round, time)
        is sourced from individual fight detail pages (Greco's approach).

        fight_url: from data-link attribute on <tr> (Greco's exact selector)
        outcome:   from b-flag CSS class on the flag anchor in cells[0]
        """
        try:
            logging.info(f"Scraping fights from: {event_url}")
            time.sleep(random.uniform(1, 3))

            response = self.session.get(event_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            stubs = []

            # Greco's exact row selector — only clickable fight rows
            for row in soup.find_all('tr', class_='b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click'):
                try:
                    fight_url = row.get('data-link')
                    if not fight_url:
                        continue

                    cells = row.find_all('td', class_='b-fight-details__table-col')
                    if not cells:
                        continue

                    fight_link = cells[0].find('a', class_='b-flag')
                    if not fight_link:
                        continue

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

                    stubs.append({'fight_url': fight_url, 'outcome': outcome})

                except Exception as e:
                    logging.warning(f"Error parsing fight row: {e}")
                    continue

            logging.info(f"Found {len(stubs)} fight stubs for event")
            return stubs

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

    def _parse_fight_meta(self, soup):
        """Parse fight metadata from an individual fight detail page.

        Implements Greco's parse_fight_results selectors exactly:
          - Fighter names/URLs: <a class="b-link b-fight-details__person-link">
          - OUTCOME:            <div class="b-fight-details__person"> [0,1]
                                  -> find_all('i')[0].text  ("W"/"L"/"D"/"NC")
                                  -> joined as "W/L", "L/W", "D/D", "NC/NC"
          - WEIGHTCLASS:        <div class="b-fight-details__fight-head">
          - METHOD:             <i class="b-fight-details__text-item_first">  (label stripped)
          - ROUND / TIME:       <p class="b-fight-details__text">[0]
                                  -> <i class="b-fight-details__text-item">  (label stripped)

        Cleaning mirrors Greco: .replace('\\n', '').replace('  ', '')
        Label stripping: re.sub('^(.+?): ?', '', text)
        """
        meta = {}

        def clean(text):
            return text.replace('\n', '').replace('  ', '').strip()

        def strip_label(text):
            return re.sub(r'^(.+?): ?', '', text).strip()

        try:
            # Fighter names and profile URLs (Greco: b-fight-details__person-link)
            fighter_links = soup.find_all('a', class_='b-link b-fight-details__person-link')
            if len(fighter_links) >= 1:
                meta['fighter_a_name'] = fighter_links[0].text.strip()
                meta['fighter_a_url']  = fighter_links[0].get('href')
            if len(fighter_links) >= 2:
                meta['fighter_b_name'] = fighter_links[1].text.strip()
                meta['fighter_b_url']  = fighter_links[1].get('href')

            # Outcome (Greco: b-fight-details__person divs, first <i> text per div)
            # UFCStats event listing always puts winner first so the flag is always green.
            # The fight detail page has the true per-fighter outcome in each person div.
            person_divs = soup.find_all('div', class_='b-fight-details__person')
            if len(person_divs) >= 2:
                i_tags_a = person_divs[0].find_all('i')
                i_tags_b = person_divs[1].find_all('i')
                if i_tags_a and i_tags_b:
                    outcome_a = i_tags_a[0].text.strip()  # "W", "L", "D", or "NC"
                    outcome_b = i_tags_b[0].text.strip()
                    if outcome_a and outcome_b:
                        meta['outcome'] = outcome_a + '/' + outcome_b

            # Weight class (Greco: b-fight-details__fight-head)
            # Raw text is e.g. "Flyweight Bout" — strip " Bout" for DB consistency
            fight_head = soup.find('div', class_='b-fight-details__fight-head')
            if fight_head:
                raw_wc = clean(fight_head.get_text())
                meta['weight_class'] = re.sub(r'\s+Bout$', '', raw_wc, flags=re.IGNORECASE)

            # Method (Greco: b-fight-details__text-item_first, then strip label)
            method_elem = soup.find('i', class_='b-fight-details__text-item_first')
            if method_elem:
                meta['method'] = strip_label(clean(method_elem.get_text()))

            # Round and Time (Greco: first b-fight-details__text p, then b-fight-details__text-item i tags)
            text_sections = soup.find_all('p', class_='b-fight-details__text')
            if text_sections:
                for i_tag in text_sections[0].find_all('i', class_='b-fight-details__text-item'):
                    raw = clean(i_tag.get_text())
                    lower = raw.lower()
                    if lower.startswith('round:'):
                        meta['round'] = strip_label(raw)
                    elif lower.startswith('time:') and not lower.startswith('time format:'):
                        meta['time'] = strip_label(raw)

        except Exception as e:
            logging.warning(f"Error parsing fight meta: {e}")

        return meta

    def _parse_stat_table_by_parity(self, table, col_names):
        """
        Extract per-fighter, per-round stats from a UFC stat table.

        UFCStats puts both fighters' values inside the same <td> as two <p> tags:
            <td><p>Fighter A value</p><p>Fighter B value</p></td>

        Using <p>-tag index parity (Greco's approach) we cleanly separate them
        without any newline-merging artefacts.

        Row 0 of each tbody is an "All Rounds" summary — always skipped.
        Subsequent rows are Round 1, Round 2, ... assigned by position.

        Returns (fighter_a_rounds, fighter_b_rounds) — lists of dicts.
        """
        results_a, results_b = [], []
        tbody = table.find('tbody')
        if not tbody:
            return results_a, results_b

        round_num = 0
        for i, row in enumerate(tbody.find_all('tr')):
            if i == 0:
                continue  # "All Rounds" summary row — skip
            round_num += 1

            cells = row.find_all('td', class_='b-fight-details__table-col')
            if not cells:
                cells = row.find_all('td')
            if not cells:
                continue

            vals_a = {'round': str(round_num)}
            vals_b = {'round': str(round_num)}

            for j, cell in enumerate(cells):
                p_tags = cell.find_all('p')
                val_a = p_tags[0].text.strip() if p_tags else cell.text.strip()
                val_b = p_tags[1].text.strip() if len(p_tags) > 1 else val_a

                if j == 0:
                    vals_a['fighter'] = val_a
                    vals_b['fighter'] = val_b
                elif j - 1 < len(col_names):
                    vals_a[col_names[j - 1]] = val_a
                    vals_b[col_names[j - 1]] = val_b

            results_a.append(vals_a)
            results_b.append(vals_b)

        return results_a, results_b

    def scrape_fight_detail_stats(self, fight_url):
        """Visit an individual fight page and scrape TOTT + round-by-round stats.

        UFCStats fight pages have two stat tables per fight:
          - Totals        (columns: KD, SIG.STR., SIG.STR.%, TOTAL STR., TD, TD%, SUB.ATT, REV., CTRL)
          - Sig. Strikes  (columns: SIG.STR., SIG.STR.%, HEAD, BODY, LEG, DISTANCE, CLINCH, GROUND)

        We detect each table by its header row, parse both with <p>-tag parity,
        then merge them into one row per fighter per round.
        """
        empty = {'fighter_a_tott': {}, 'fighter_b_tott': {}, 'round_stats': [], 'fight_meta': {}}
        try:
            time.sleep(random.uniform(1.5, 3.0))
            response = self.session.get(fight_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            result = {'fighter_a_tott': {}, 'fighter_b_tott': {}, 'round_stats': []}

            # --- Tale of the Tape (unchanged) ---
            tott_section = soup.find('div', class_='b-fight-details__persons')
            if tott_section:
                fighters = tott_section.find_all('div', class_='b-fight-details__person')
                if len(fighters) >= 2:
                    result['fighter_a_tott'] = self._parse_fighter_tott(fighters[0])
                    result['fighter_b_tott'] = self._parse_fighter_tott(fighters[1])

            # --- Round-by-round stats ---
            TOTALS_COLS = ['kd', 'sig_str', 'sig_str_pct', 'total_str',
                           'td', 'td_pct', 'sub_att', 'rev', 'ctrl']
            SIG_COLS    = ['sig_str', 'sig_str_pct',
                           'head', 'body', 'leg', 'distance', 'clinch', 'ground']

            totals_a, totals_b = {}, {}
            sig_a,    sig_b    = {}, {}

            for table in soup.find_all('table', class_='b-fight-details__table'):
                thead = table.find('thead')
                if not thead:
                    continue
                header_text = thead.get_text().upper()

                if 'KD' in header_text:
                    a_rounds, b_rounds = self._parse_stat_table_by_parity(table, TOTALS_COLS)
                    for r in a_rounds:
                        totals_a[r['round']] = r
                    for r in b_rounds:
                        totals_b[r['round']] = r

                elif 'HEAD' in header_text:
                    a_rounds, b_rounds = self._parse_stat_table_by_parity(table, SIG_COLS)
                    for r in a_rounds:
                        sig_a[r['round']] = r
                    for r in b_rounds:
                        sig_b[r['round']] = r

            # Merge totals + sig strikes; emit Fighter A then Fighter B per round
            all_rounds = sorted(
                set(list(totals_a.keys()) + list(sig_a.keys())),
                key=lambda x: int(x) if x.isdigit() else 0
            )

            for rnd in all_rounds:
                stats_a = {**totals_a.get(rnd, {}), **sig_a.get(rnd, {}), 'round': rnd}
                stats_b = {**totals_b.get(rnd, {}), **sig_b.get(rnd, {}), 'round': rnd}
                if stats_a.get('fighter'):
                    result['round_stats'].append(stats_a)
                if stats_b.get('fighter'):
                    result['round_stats'].append(stats_b)

            # Fight metadata from this same page (Greco's parse_fight_results selectors)
            result['fight_meta'] = self._parse_fight_meta(soup)

            logging.info(f"Parsed {len(result['round_stats'])} round-stat rows from {fight_url}")
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

                # Step 1 — get fight URLs + outcomes from event listing page
                fight_stubs = self.scrape_event_fights(event['url'])
                if not fight_stubs:
                    print(f"   WARNING: No fights found for this event")
                    continue

                print(f"   Found {len(fight_stubs)} fights — visiting each fight page...")

                # Step 2 — visit each individual fight page (Greco's approach)
                # get fight_meta (names, weight class, method, round, time) + stats + tott
                full_fights = []
                fight_details_map = {}
                for stub in fight_stubs:
                    detail = self.scrape_fight_detail_stats(stub['fight_url'])
                    fight_data = {
                        'fight_url': stub['fight_url'],
                        'outcome':   stub['outcome'],
                        **detail.get('fight_meta', {}),
                    }
                    full_fights.append(fight_data)
                    fight_details_map[stub['fight_url']] = detail

                # Step 3 — store fight_details + fight_results with accurate metadata
                stored_fights = self.store_new_fights(full_fights, event['name'], event_id)
                total_fights += len(stored_fights)
                print(f"   Stored {len(stored_fights)} fights — saving stats...")

                # Step 4 — store stats + tott (data already in memory from Step 2)
                for fight_data, fight_id in stored_fights:
                    bout_str = (
                        f"{fight_data.get('fighter_a_name', '')} vs. "
                        f"{fight_data.get('fighter_b_name', '')}"
                    )
                    detail = fight_details_map.get(fight_data['fight_url'], {})

                    if detail.get('round_stats'):
                        self.store_fight_stats(
                            event_id, event['name'], fight_id,
                            bout_str, detail['round_stats']
                        )

                    if detail.get('fighter_a_tott'):
                        self.store_fighter_tott(
                            fight_data.get('fighter_a_name', ''), detail['fighter_a_tott']
                        )
                    if detail.get('fighter_b_tott'):
                        self.store_fighter_tott(
                            fight_data.get('fighter_b_name', ''), detail['fighter_b_tott']
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