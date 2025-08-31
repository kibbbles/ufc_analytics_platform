"""Test script to verify Greko's scraper functions work."""

import sys
import os

# Add the scraper directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scrape_ufc_stats'))

try:
    # Import Greko's library
    import scrape_ufc_stats_library as greko
    print("[SUCCESS] Greko library imported successfully!")
    
    # Test basic web scraping function
    print("\n[TEST] Testing get_soup function...")
    test_url = "http://ufcstats.com/statistics/events/completed"
    
    try:
        soup = greko.get_soup(test_url)
        print(f"[SUCCESS] Retrieved soup from {test_url}")
        print(f"[INFO] Page title: {soup.title.string if soup.title else 'No title found'}")
        
        # Test if we can find some UFC data
        events = soup.find_all('tr', class_='b-statistics__table-row')
        print(f"[INFO] Found {len(events)} potential event rows")
        
    except Exception as e:
        print(f"[ERROR] get_soup test failed: {e}")
    
except ImportError as e:
    print(f"[ERROR] Could not import Greko library: {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")

print("\nGreko scraper analysis complete!")