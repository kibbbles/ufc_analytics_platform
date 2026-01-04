"""
ONE-TIME BULK SCRAPER: Populate career statistics for all existing fighters

This script scrapes career stats from UFCStats.com fighter profile pages
for all ~4,400 fighters currently in the database.

Expected runtime: 3-4 hours (with 2-4 second delays between requests)
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
        logging.FileHandler('bulk_career_stats_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class BulkCareerStatsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'already_populated': 0,
            'no_url': 0
        }

    def scrape_fighter_career_stats(self, fighter_url):
        """Scrape career statistics from fighter profile page"""
        try:
            time.sleep(random.uniform(2, 4))

            response = self.session.get(fighter_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            items = soup.find_all('li', class_='b-list__box-list-item')

            stats = {}
            for item in items:
                label_elem = item.find('i', class_='b-list__box-item-title')
                if label_elem:
                    label = label_elem.text.strip().rstrip(':')
                    full_text = item.get_text()
                    value = full_text.replace(label_elem.text, '').strip()
                    if value:
                        stats[label] = value

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
            logging.error(f"Error scraping {fighter_url}: {e}")
            return None

    def update_fighter_stats(self, fighter_id, stats):
        """Update fighter_tott with career statistics"""
        try:
            with engine.connect() as conn:
                update_sql = text('''
                    UPDATE fighter_tott
                    SET slpm = :slpm,
                        str_acc = :str_acc,
                        sapm = :sapm,
                        str_def = :str_def,
                        td_avg = :td_avg,
                        td_acc = :td_acc,
                        td_def = :td_def,
                        sub_avg = :sub_avg
                    WHERE id = :fighter_id
                ''')

                conn.execute(update_sql, {
                    'fighter_id': fighter_id,
                    'slpm': stats.get('slpm'),
                    'str_acc': stats.get('str_acc'),
                    'sapm': stats.get('sapm'),
                    'str_def': stats.get('str_def'),
                    'td_avg': stats.get('td_avg'),
                    'td_acc': stats.get('td_acc'),
                    'td_def': stats.get('td_def'),
                    'sub_avg': stats.get('sub_avg')
                })
                conn.commit()
                return True

        except Exception as e:
            logging.error(f"Error updating fighter {fighter_id}: {e}")
            return False

    def get_fighters_to_scrape(self, resume_from_id=None):
        """Get fighters that need career stats scraped"""
        try:
            with engine.connect() as conn:
                if resume_from_id:
                    # Resume from specific fighter (in case of interruption)
                    query = text('''
                        SELECT id, "FIGHTER", "URL"
                        FROM fighter_tott
                        WHERE "URL" IS NOT NULL
                        AND id >= :resume_id
                        ORDER BY id
                    ''')
                    result = conn.execute(query, {'resume_id': resume_from_id})
                else:
                    # Get all fighters (prioritize those without stats)
                    query = text('''
                        SELECT id, "FIGHTER", "URL"
                        FROM fighter_tott
                        WHERE "URL" IS NOT NULL
                        ORDER BY
                            CASE WHEN slpm IS NULL THEN 0 ELSE 1 END,
                            id
                    ''')
                    result = conn.execute(query)

                return [(row[0], row[1], row[2]) for row in result]

        except Exception as e:
            logging.error(f"Error getting fighters: {e}")
            return []

    def run_bulk_scrape(self, resume_from_id=None, max_fighters=None):
        """Main scraping loop"""
        print("="*80)
        print("BULK CAREER STATS SCRAPER")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        fighters = self.get_fighters_to_scrape(resume_from_id)

        if not fighters:
            print("No fighters found to scrape!")
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

        for i, (fighter_id, fighter_name, fighter_url) in enumerate(fighters, 1):
            try:
                # Check if already has stats
                with engine.connect() as conn:
                    check = conn.execute(text('''
                        SELECT slpm, str_acc, sapm
                        FROM fighter_tott
                        WHERE id = :id
                    '''), {'id': fighter_id}).fetchone()

                    if check and all([check[0], check[1], check[2]]):
                        self.stats['already_populated'] += 1
                        if i % 50 == 0:
                            print(f"[{i}/{len(fighters)}] {fighter_name:30s} - Already has stats (skipping)")
                        continue

                # Scrape career stats
                print(f"[{i}/{len(fighters)}] {fighter_name:30s} ", end='')

                stats = self.scrape_fighter_career_stats(fighter_url)

                if stats and stats.get('slpm'):
                    # Update database
                    if self.update_fighter_stats(fighter_id, stats):
                        self.stats['success'] += 1
                        print(f"[OK] SLpM={stats.get('slpm')}, SApM={stats.get('sapm')}")
                        last_save_id = fighter_id
                    else:
                        self.stats['failed'] += 1
                        print("[FAILED] Database update error")
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
                    print(f"Success: {self.stats['success']}, Failed: {self.stats['failed']}, Already populated: {self.stats['already_populated']}")
                    print(f"Rate: {rate*60:.1f} fighters/min")
                    print(f"Est. remaining: {remaining/60:.0f} minutes")
                    print(f"Last saved: {last_save_id}")
                    print("="*80 + "\n")

            except KeyboardInterrupt:
                print("\n\n" + "="*80)
                print("INTERRUPTED BY USER")
                print(f"Last saved fighter ID: {last_save_id}")
                print(f"To resume: python bulk_scrape_career_stats.py --resume {last_save_id}")
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
        print(f"  Total fighters:      {self.stats['total']}")
        print(f"  Successfully scraped: {self.stats['success']}")
        print(f"  Failed:              {self.stats['failed']}")
        print(f"  Already populated:   {self.stats['already_populated']}")
        print(f"  Success rate:        {self.stats['success']/(self.stats['success']+self.stats['failed'])*100:.1f}%")
        print("="*80)

        # Verify database
        with engine.connect() as conn:
            result = conn.execute(text('''
                SELECT
                    COUNT(*) as total,
                    COUNT(slpm) as has_slpm,
                    COUNT(sapm) as has_sapm,
                    COUNT(str_def) as has_str_def
                FROM fighter_tott
                WHERE "URL" IS NOT NULL
            '''))
            row = result.fetchone()

            print(f"\nDatabase verification:")
            print(f"  Total fighters with URLs: {row[0]}")
            print(f"  Has SLpM:  {row[1]} ({row[1]/row[0]*100:.1f}%)")
            print(f"  Has SApM:  {row[2]} ({row[2]/row[0]*100:.1f}%)")
            print(f"  Has Str.Def: {row[3]} ({row[3]/row[0]*100:.1f}%)")

        print("\nLog file: bulk_career_stats_scraper.log")
        print("="*80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Bulk scrape fighter career statistics')
    parser.add_argument('--resume', type=str, help='Resume from fighter ID')
    parser.add_argument('--test', type=int, help='Test mode: only scrape N fighters')

    args = parser.parse_args()

    scraper = BulkCareerStatsScraper()
    scraper.run_bulk_scrape(
        resume_from_id=args.resume,
        max_fighters=args.test
    )


if __name__ == "__main__":
    main()
