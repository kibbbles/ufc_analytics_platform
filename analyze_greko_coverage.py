"""Deep analysis of Greko's data coverage and column completeness."""

import pandas as pd
import numpy as np
from datetime import datetime
import re

print("=" * 80)
print("DEEP ANALYSIS OF GREKO'S DATA COVERAGE")
print("=" * 80)

# Load all CSV files
csv_files = {
    'events': 'scrape_ufc_stats/ufc_event_details.csv',
    'fight_details': 'scrape_ufc_stats/ufc_fight_details.csv',
    'fight_results': 'scrape_ufc_stats/ufc_fight_results.csv',
    'fight_stats': 'scrape_ufc_stats/ufc_fight_stats.csv',
    'fighters': 'scrape_ufc_stats/ufc_fighter_details.csv',
    'fighter_tott': 'scrape_ufc_stats/ufc_fighter_tott.csv'
}

data = {}
for name, path in csv_files.items():
    try:
        df = pd.read_csv(path)
        data[name] = df
        print(f"\n[SUCCESS] Loaded {name}: {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"[ERROR] Error loading {name}: {e}")

print("\n" + "=" * 80)
print("1. HISTORICAL DATA COVERAGE ANALYSIS")
print("=" * 80)

# Analyze events data for historical coverage
if 'events' in data:
    events_df = data['events']
    print(f"\nEVENTS ANALYSIS:")
    print(f"Total events: {len(events_df)}")
    
    # Try to parse dates to find date range
    date_patterns = []
    sample_dates = events_df['DATE'].head(10).tolist()
    print(f"Sample dates: {sample_dates}")
    
    # Try to extract years from dates
    years = []
    for date_str in events_df['DATE'].dropna():
        # Try to extract year using regex
        year_match = re.search(r'(19|20)\d{2}', str(date_str))
        if year_match:
            years.append(int(year_match.group()))
    
    if years:
        print(f"Date range: {min(years)} - {max(years)}")
        print(f"Total years covered: {max(years) - min(years) + 1}")
        
        # Year distribution
        year_counts = pd.Series(years).value_counts().sort_index()
        print(f"\nTop 10 years by event count:")
        print(year_counts.head(10))
        print(f"\nBottom 10 years by event count:")
        print(year_counts.tail(10))
        
        # Check for very early UFC events
        early_events = events_df[events_df['DATE'].str.contains('199', na=False)]
        print(f"\n1990s events: {len(early_events)}")
        if len(early_events) > 0:
            print("Sample 1990s events:")
            print(early_events[['EVENT', 'DATE']].head())

print("\n" + "=" * 80)
print("2. COLUMN COMPLETENESS ANALYSIS")
print("=" * 80)

for name, df in data.items():
    print(f"\n{name.upper()} COLUMNS ({len(df.columns)} total):")
    print("=" * 50)
    print("Columns:", list(df.columns))
    
    # Check data completeness
    print("\nData completeness:")
    for col in df.columns:
        null_pct = (df[col].isnull().sum() / len(df)) * 100
        unique_vals = df[col].nunique()
        print(f"  {col}: {100-null_pct:.1f}% filled, {unique_vals} unique values")
        
        # Show sample values for first few columns
        if col in list(df.columns)[:3]:
            sample_vals = df[col].dropna().head(3).tolist()
            print(f"    Sample: {sample_vals}")

print("\n" + "=" * 80)
print("3. FIGHT STATS DETAIL ANALYSIS")
print("=" * 80)

# Deep dive into fight stats - this is the most detailed data
if 'fight_stats' in data:
    stats_df = data['fight_stats']
    print(f"\nFIGHT STATS DETAILED ANALYSIS:")
    print(f"Total records: {len(stats_df)}")
    print(f"Columns: {len(stats_df.columns)}")
    
    print(f"\nAll columns in fight_stats:")
    for i, col in enumerate(stats_df.columns, 1):
        print(f"{i:2d}. {col}")
    
    # Check what kind of strike data is available
    strike_columns = [col for col in stats_df.columns if 'STR' in col.upper() or 'STRIKE' in col.upper()]
    print(f"\nStrike-related columns ({len(strike_columns)}):")
    for col in strike_columns:
        print(f"  - {col}")
    
    # Sample fight stats record
    print(f"\nSample fight stats record:")
    if len(stats_df) > 0:
        sample = stats_df.iloc[0]
        for col, val in sample.items():
            print(f"  {col}: {val}")

print("\n" + "=" * 80)
print("4. COMPARISON WITH UFC STATS WEBSITE")
print("=" * 80)

print("""
To determine if Greko is capturing ALL available data, we should check:

1. UFC Stats website structure - what columns are available
2. Compare with Greko's extracted columns
3. Check if any detailed stats are missing

Key questions:
- Does UFC stats have more detailed striking data by body part?
- Are submission attempt details captured?
- Are judge scorecards included?
- Are there fighter physical measurements beyond basic tale of the tape?
""")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)