"""Detailed test to understand Greko's scraping coverage."""

import sys
import os
import pandas as pd

# Add the scraper directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scrape_ufc_stats'))

import scrape_ufc_stats_library as greko

print("=" * 60)
print("ANALYZING GREKO'S SCRAPER COVERAGE")
print("=" * 60)

# Test 1: Check the events page
print("\n[TEST 1] Checking events page structure...")
events_url = "http://ufcstats.com/statistics/events/completed"
soup = greko.get_soup(events_url)

# Find all event rows
all_rows = soup.find_all('tr', class_='b-statistics__table-row')
print(f"Found {len(all_rows)} rows with class 'b-statistics__table-row'")

# Try different selectors
all_links = soup.find_all('a', class_='b-link')
print(f"Found {len(all_links)} links with class 'b-link'")

# Check if there's pagination
pagination = soup.find_all(['button', 'a'], string=lambda text: 'Next' in text if text else False)
print(f"Pagination elements found: {len(pagination)}")

# Test 2: Check the actual CSV files Greko already scraped
print("\n[TEST 2] Checking existing CSV files...")
csv_files = {
    'events': 'scrape_ufc_stats/ufc_event_details.csv',
    'fights': 'scrape_ufc_stats/ufc_fight_details.csv',
    'fight_results': 'scrape_ufc_stats/ufc_fight_results.csv',
    'fight_stats': 'scrape_ufc_stats/ufc_fight_stats.csv',
    'fighters': 'scrape_ufc_stats/ufc_fighter_details.csv'
}

for name, path in csv_files.items():
    try:
        df = pd.read_csv(path)
        print(f"\n{name.upper()}:")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {list(df.columns)[:5]}{'...' if len(df.columns) > 5 else ''}")
        
        if name == 'events':
            # Check unique events
            if 'EVENT' in df.columns:
                unique_events = df['EVENT'].nunique()
                print(f"  - Unique events: {unique_events}")
                # Show some event names
                print(f"  - Sample events: {df['EVENT'].head(3).tolist()}")
                print(f"  - Latest event: {df['EVENT'].iloc[-1] if len(df) > 0 else 'N/A'}")
        
        if name == 'fighters':
            print(f"  - Unique fighters: {len(df)}")
            
    except Exception as e:
        print(f"{name}: Error reading CSV - {e}")

# Test 3: Check if Greko's function gets all events
print("\n[TEST 3] Testing Greko's parse_event_details function...")
try:
    # This should use Greko's actual parsing function
    event_df = greko.parse_event_details(soup)
    print(f"Greko's parse_event_details returned {len(event_df)} events")
    if len(event_df) > 0:
        print(f"First event: {event_df.iloc[0].to_dict()}")
except Exception as e:
    print(f"Error calling parse_event_details: {e}")

# Test 4: Manual count of event links
print("\n[TEST 4] Manual inspection of page...")
event_links = soup.find_all('a', href=lambda x: x and '/event-details/' in x)
print(f"Found {len(event_links)} event links containing '/event-details/'")

# Check if there's a "View More" or similar
all_text = soup.get_text()
if "Load More" in all_text or "Show More" in all_text:
    print("⚠️  Page has 'Load More' functionality - may need JavaScript!")
    
print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)