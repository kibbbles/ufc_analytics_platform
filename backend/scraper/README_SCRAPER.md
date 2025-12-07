# UFC Full Historical Scraper

## Overview
Complete scraper that populates all database tables with UFC historical data from UFCStats.com.

## What It Scrapes
- **event_details**: All UFC events (1994-present)
- **fighter_details**: Fighter profiles
- **fighter_tott**: Tale of the Tape (height, weight, reach, stance, DOB)
- **fight_details**: Fight matchups
- **fight_results**: Outcomes, methods, rounds
- **fight_stats**: Round-by-round statistics (2015+)

## Usage

### 1. Preview First (Recommended)
```bash
cd backend/scraper
python full_historical_scraper.py --dry-run
```
Shows what will be scraped without touching the database.

### 2. Clear Old Data (Optional)
```bash
python full_historical_scraper.py --clear-db
```
Prompts for confirmation before clearing existing data.
**WARNING**: This deletes all UFC data from your database!

### 3. Run Full Scrape
```bash
python full_historical_scraper.py
```
Starts the complete historical scrape.

## Expected Runtime
- **Without --clear-db**: Skips existing events, only scrapes new ones
- **Full scrape from scratch**: 8-12 hours (756 events with detailed stats)
- Progress is saved incrementally, can resume if interrupted

## Progress Tracking
1. **Console Output**: Real-time "[15/756] Processing: UFC 300" updates
2. **Log File**: Detailed logs saved to `full_scraper.log`
3. **Periodic Updates**: Summary every 10 events
4. **Statistics**: Events, fights, fighters, errors tracked throughout

## Rate Limiting
- 1.5-3 second delays between requests
- Respectful to UFCStats.com servers
- Can be run overnight without issues

## Resuming Interrupted Scrapes
The scraper automatically skips events already in the database:
- If interrupted, just run again
- It will pick up where it left off
- No duplicate data will be created

## After Completion
Check your database for:
- Complete Petr Yan record (25 fights instead of 8)
- All fighter physical stats
- Round-by-round statistics for modern fights
- Complete UFC event history

## Troubleshooting

### "Connection timeout"
- Check internet connection
- UFCStats.com might be down temporarily
- Wait and retry

### "Database connection error"
- Verify DATABASE_URL in .env file
- Check Supabase connection
- Ensure tables exist (run migrations if needed)

### "Missing dependencies"
```bash
pip install requests beautifulsoup4 pandas sqlalchemy tqdm
```

## Output Example
```
============================================================
Starting Full Historical UFC Scrape
============================================================
Loaded 756 existing IDs from database
Found 0 events already in database
Total events available: 756
Events to scrape: 756
Beginning event scraping with detailed fight stats...
NOTE: This will take several hours due to detailed scraping

[1/756] Processing: UFC 323: Dvalishvili vs. Yan 2
  Found 13 fights
    Fight 5/13 processed
    Fight 10/13 processed
[2/756] Processing: UFC Fight Night: Tsarukyan vs. Hooker
  Found 11 fights
...
Progress: 10/756 events processed
  Total fights: 127
  Fighters added: 34
  Errors: 2
...
============================================================
Scraping Complete!
Events processed: 756
Fights processed: 8287
Fighters added: 4429
Errors encountered: 12
============================================================
Database now contains complete UFC historical data!
```

## Next Steps
After scraping completes, you can:
1. Query Petr Yan's complete record in Supabase
2. Build ML models with comprehensive data
3. Use `live_scraper.py` for future event updates
