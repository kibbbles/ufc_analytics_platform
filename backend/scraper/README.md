# UFC Scraper - Live Update System

Clean, minimal UFC scraper system for keeping your database updated with new events.

## 🚀 Quick Start

### **Manual Update Check**
```bash
python live_scraper.py
```

### **Weekly Automated Scraping**
```bash
# Start scheduler (runs in background)
python scheduler.py --action start --daemon

# Run weekly check manually
python scheduler.py --action run-weekly
```

## 📁 Files Overview

### Core Files
- **`live_scraper.py`** - Main scraper that only adds NEW events not in database
- **`scheduler.py`** - Weekly automation system (runs Sundays at 6 AM)
- **`database_integration.py`** - Database connection and operations
- **`scheduler_config.json`** - Configuration settings

## ⚙️ How It Works

### Database Foundation
Your database already contains comprehensive UFC data:
- **744 Events** (1994-2025) 
- **4,429 Fighters**
- **8,287 Fights** 
- **38,958 Fight Statistics**

### Live Updates
1. **Smart Detection** - Compares UFCStats.com events with your database
2. **Incremental Only** - Only scrapes events that don't exist in your database
3. **Respectful Scraping** - 1-3 second delays between requests
4. **Automatic Scheduling** - Weekly checks every Sunday at 6 AM

### Event Detection Process
```
UFCStats.com → Parse Events → Check Database → Scrape New Only → Store Results
```

## 📊 Configuration

Edit `scheduler_config.json` to customize:

```json
{
  "weekly_scrape_day": "sunday",
  "weekly_scrape_time": "06:00", 
  "max_events_per_run": 20,
  "days_back_to_check": 14,
  "retry_failed_jobs": true,
  "max_retries": 3
}
```

## 📈 Current Status

✅ **Database**: 744 events loaded (up to 2025)  
✅ **Live Scraper**: Working with flexible website parsing  
✅ **Weekly Scheduler**: Configured for Sunday 6 AM  
✅ **Rate Limiting**: Respectful 1-3 second delays  

## 🐛 Troubleshooting

**No new events found**: This is normal! Your database has comprehensive data through 2025.

**Website parsing errors**: The scraper uses flexible parsing to handle UFCStats.com structure changes.

**Database connection issues**: Check your `.env` file has correct `DATABASE_URL`.

## 📈 Next Steps

With your clean data foundation, you're ready for:
- ML model development
- Analytics dashboard 
- Fight prediction algorithms

The scraper will automatically keep your data current as new UFC events are added to UFCStats.com.