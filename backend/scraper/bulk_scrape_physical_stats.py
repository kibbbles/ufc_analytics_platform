"""
ONE-TIME BULK SCRAPER: Populate missing physical statistics for fighters

This script scrapes HEIGHT, REACH, WEIGHT, STANCE, DOB from UFCStats.com
fighter profile pages for fighters with missing data.

Priority: REACH (58.5% missing), HEIGHT (19.9%), DOB (20%), STANCE (33.5%)

Expected runtime: 2-3 hours (with 2-4 second delays between requests)
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime
from sqlalchemy import text

# Add parent directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

from db.database import engine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_physical_stats_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class BulkPhysicalStatsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'already_complete': 0,
            'partial_update': 0
        }

    def scrape_fighter_physical_stats(self, fighter_url):
        """
        Scrape physical statistics from fighter profile page

        Returns dict with keys:
            - height: Height (e.g., "5' 10\"")
            - weight: Weight (e.g., "170 lbs.")
            - reach: Reach (e.g., "74\"")
            - stance: Stance (e.g., "Orthodox", "Southpaw")
            - dob: Date of Birth (e.g., "Jan 01, 1990")
        """
        try:
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

                    # Only store if not empty or "--"
                    if value and value != '--':
                        stats[label] = value

            # Map UFC labels to database columns
            return {
                'height': stats.get('Height'),
                'weight': stats.get('Weight'),
                'reach': stats.get('Reach'),
                'stance': stats.get('STANCE'),
                'dob': stats.get('DOB')
            }

        except Exception as e:
            logging.error(f"Error scraping {fighter_url}: {e}")
            return None

    def update_fighter_physical_stats(self, fighter_id, current_data, new_stats):
        """
        Update fighter_tott with physical statistics
        Only updates fields that are currently missing or "--"
        """
        try:
            # Build update dict - only update missing fields
            updates = {}
            fields_updated = []

            # Check each field and only update if currently missing
            if (not current_data['HEIGHT'] or current_data['HEIGHT'] == '--') and new_stats.get('height'):
                updates['HEIGHT'] = new_stats['height']
                fields_updated.append('HEIGHT')

            if (not current_data['WEIGHT'] or current_data['WEIGHT'] == '--') and new_stats.get('weight'):
                updates['WEIGHT'] = new_stats['weight']
                fields_updated.append('WEIGHT')

            if (not current_data['REACH'] or current_data['REACH'] == '--') and new_stats.get('reach'):
                updates['REACH'] = new_stats['reach']
                fields_updated.append('REACH')

            if (not current_data['STANCE'] or current_data['STANCE'] == '--') and new_stats.get('stance'):
                updates['STANCE'] = new_stats['stance']
                fields_updated.append('STANCE')

            if (not current_data['DOB'] or current_data['DOB'] == '--') and new_stats.get('dob'):
                updates['DOB'] = new_stats['dob']
                fields_updated.append('DOB')

            # If nothing to update, skip
            if not updates:
                return False, []

            # Build dynamic UPDATE query with lowercase parameter names
            set_clause = ', '.join([f'"{key}" = :{key.lower()}' for key in updates.keys()])
            update_sql = f'UPDATE fighter_tott SET {set_clause} WHERE id = :fighter_id'

            # Convert keys to lowercase for parameter binding
            params = {key.lower(): value for key, value in updates.items()}
            params['fighter_id'] = fighter_id

            with engine.connect() as conn:
                conn.execute(text(update_sql), params)
                conn.commit()
                return True, fields_updated

        except Exception as e:
            logging.error(f"Error updating fighter {fighter_id}: {e}")
            return False, []

    def get_fighters_needing_stats(self, resume_from_id=None):
        """Get fighters that have missing physical stats"""
        try:
            with engine.connect() as conn:
                if resume_from_id:
                    query = text('''
                        SELECT id, "FIGHTER", "URL", "HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB"
                        FROM fighter_tott
                        WHERE "URL" IS NOT NULL
                        AND id >= :resume_id
                        ORDER BY id
                    ''')
                    result = conn.execute(query, {'resume_id': resume_from_id})
                else:
                    # Prioritize fighters with missing REACH (biggest gap)
                    query = text('''
                        SELECT id, "FIGHTER", "URL", "HEIGHT", "WEIGHT", "REACH", "STANCE", "DOB"
                        FROM fighter_tott
                        WHERE "URL" IS NOT NULL
                        ORDER BY
                            CASE WHEN "REACH" IS NULL OR "REACH" = '--' THEN 0 ELSE 1 END,
                            CASE WHEN "HEIGHT" IS NULL OR "HEIGHT" = '--' THEN 0 ELSE 1 END,
                            CASE WHEN "STANCE" IS NULL OR "STANCE" = '--' THEN 0 ELSE 1 END,
                            CASE WHEN "DOB" IS NULL OR "DOB" = '--' THEN 0 ELSE 1 END,
                            id
                    ''')
                    result = conn.execute(query)

                fighters = []
                for row in result:
                    # Only include if at least one field is missing
                    has_missing = (
                        not row[3] or row[3] == '--' or  # HEIGHT
                        not row[4] or row[4] == '--' or  # WEIGHT
                        not row[5] or row[5] == '--' or  # REACH
                        not row[6] or row[6] == '--' or  # STANCE
                        not row[7] or row[7] == '--'     # DOB
                    )

                    if has_missing:
                        fighters.append({
                            'id': row[0],
                            'name': row[1],
                            'url': row[2],
                            'current': {
                                'HEIGHT': row[3],
                                'WEIGHT': row[4],
                                'REACH': row[5],
                                'STANCE': row[6],
                                'DOB': row[7]
                            }
                        })

                return fighters

        except Exception as e:
            logging.error(f"Error getting fighters: {e}")
            return []

    def run_bulk_scrape(self, resume_from_id=None, max_fighters=None):
        """Main scraping loop"""
        print("="*80)
        print("BULK PHYSICAL STATS SCRAPER")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        fighters = self.get_fighters_needing_stats(resume_from_id)

        if not fighters:
            print("No fighters found with missing physical stats!")
            return

        self.stats['total'] = len(fighters)

        if max_fighters:
            fighters = fighters[:max_fighters]
            print(f"\nLIMIT: Processing first {max_fighters} fighters (test mode)")

        print(f"\nTotal fighters to process: {len(fighters)}")
        print(f"Estimated time: {len(fighters) * 3 / 60:.0f} minutes ({len(fighters) * 3 / 3600:.1f} hours)")
        print("\nStarting in 5 seconds... (Ctrl+C to cancel)")
        time.sleep(5)

        start_time = datetime.now()
        last_save_id = None

        for i, fighter in enumerate(fighters, 1):
            try:
                fighter_id = fighter['id']
                fighter_name = fighter['name']
                fighter_url = fighter['url']
                current_data = fighter['current']

                # Show what's missing for this fighter
                missing = []
                if not current_data['HEIGHT'] or current_data['HEIGHT'] == '--':
                    missing.append('H')
                if not current_data['WEIGHT'] or current_data['WEIGHT'] == '--':
                    missing.append('W')
                if not current_data['REACH'] or current_data['REACH'] == '--':
                    missing.append('R')
                if not current_data['STANCE'] or current_data['STANCE'] == '--':
                    missing.append('S')
                if not current_data['DOB'] or current_data['DOB'] == '--':
                    missing.append('D')

                print(f"[{i}/{len(fighters)}] {fighter_name:30s} Missing:[{','.join(missing)}] ", end='')

                # Scrape physical stats
                stats = self.scrape_fighter_physical_stats(fighter_url)

                if stats:
                    # Update database (only missing fields)
                    success, updated_fields = self.update_fighter_physical_stats(
                        fighter_id, current_data, stats
                    )

                    if success:
                        self.stats['success'] += 1
                        self.stats['partial_update'] += 1
                        print(f"[OK] Updated: {', '.join(updated_fields)}")
                        last_save_id = fighter_id
                    else:
                        self.stats['already_complete'] += 1
                        print("[SKIP] No updates needed")
                else:
                    self.stats['failed'] += 1
                    print("[FAILED] No stats found")

                # Progress report every 100 fighters
                if i % 100 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    remaining = (len(fighters) - i) / rate if rate > 0 else 0

                    print("\n" + "="*80)
                    print(f"PROGRESS: {i}/{len(fighters)} ({i/len(fighters)*100:.1f}%)")
                    print(f"Success: {self.stats['success']}, Failed: {self.stats['failed']}, Already complete: {self.stats['already_complete']}")
                    print(f"Rate: {rate*60:.1f} fighters/min")
                    print(f"Est. remaining: {remaining/60:.0f} minutes")
                    print(f"Last saved: {last_save_id}")
                    print("="*80 + "\n")

            except KeyboardInterrupt:
                print("\n\n" + "="*80)
                print("INTERRUPTED BY USER")
                print(f"Last saved fighter ID: {last_save_id}")
                print(f"To resume: python bulk_scrape_physical_stats.py --resume {last_save_id}")
                print("="*80)
                break

            except Exception as e:
                logging.error(f"Unexpected error processing {fighter_name}: {e}")
                self.stats['failed'] += 1

        # Final report
        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "="*80)
        print("BULK SCRAPING COMPLETE!")
        print("="*80)
        print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration}")
        print(f"\nResults:")
        print(f"  Total fighters:       {self.stats['total']}")
        print(f"  Successfully updated: {self.stats['success']}")
        print(f"  Failed:               {self.stats['failed']}")
        print(f"  Already complete:     {self.stats['already_complete']}")

        if self.stats['success'] + self.stats['failed'] > 0:
            success_rate = self.stats['success']/(self.stats['success']+self.stats['failed'])*100
            print(f"  Success rate:         {success_rate:.1f}%")
        print("="*80)

        # Verify database
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN "HEIGHT" != '--' AND "HEIGHT" IS NOT NULL THEN 1 END) as has_height,
                    COUNT(CASE WHEN "REACH" != '--' AND "REACH" IS NOT NULL THEN 1 END) as has_reach,
                    COUNT(CASE WHEN "WEIGHT" != '--' AND "WEIGHT" IS NOT NULL THEN 1 END) as has_weight,
                    COUNT(CASE WHEN "STANCE" != '--' AND "STANCE" IS NOT NULL THEN 1 END) as has_stance,
                    COUNT(CASE WHEN "DOB" != '--' AND "DOB" IS NOT NULL THEN 1 END) as has_dob
                FROM fighter_tott
                WHERE "URL" IS NOT NULL
            ''')).fetchone()

            print(f"\nDatabase verification:")
            print(f"  Total fighters with URLs: {result[0]}")
            print(f"  Has HEIGHT: {result[1]} ({result[1]/result[0]*100:.1f}%)")
            print(f"  Has REACH:  {result[2]} ({result[2]/result[0]*100:.1f}%)")
            print(f"  Has WEIGHT: {result[3]} ({result[3]/result[0]*100:.1f}%)")
            print(f"  Has STANCE: {result[4]} ({result[4]/result[0]*100:.1f}%)")
            print(f"  Has DOB:    {result[5]} ({result[5]/result[0]*100:.1f}%)")

        print("\nLog file: bulk_physical_stats_scraper.log")
        print("="*80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Bulk scrape fighter physical statistics')
    parser.add_argument('--resume', type=str, help='Resume from fighter ID')
    parser.add_argument('--test', type=int, help='Test mode: only scrape N fighters')

    args = parser.parse_args()

    scraper = BulkPhysicalStatsScraper()
    scraper.run_bulk_scrape(
        resume_from_id=args.resume,
        max_fighters=args.test
    )


if __name__ == "__main__":
    main()
