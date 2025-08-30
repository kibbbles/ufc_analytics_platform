-- UFC Analytics Platform Database Schema
-- Designed to match Greco's CSV data structure

-- Table for UFC fighters basic info (from ufc_fighter_details.csv)
CREATE TABLE IF NOT EXISTS fighters (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    nickname VARCHAR(100),
    url VARCHAR(500) UNIQUE,
    -- Additional fields from fighter_tott (Tale of the Tape)
    height VARCHAR(20),  -- Stored as string initially (e.g., "5'11"")
    weight VARCHAR(20),  -- Stored as string initially (e.g., "185 lbs")
    reach VARCHAR(20),   -- Stored as string initially (e.g., "75"")
    stance VARCHAR(50),
    dob VARCHAR(50),     -- Date of birth as string initially
    -- Calculated fields for ML
    height_cm FLOAT,     -- Converted from height string
    weight_lbs FLOAT,    -- Converted from weight string  
    reach_inches FLOAT,  -- Converted from reach string
    date_of_birth DATE,  -- Converted from dob string
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for UFC events (from ufc_events.csv)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date DATE,
    location VARCHAR(255),
    url VARCHAR(500) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for fight results (from ufc_fight_results.csv)
CREATE TABLE IF NOT EXISTS fights (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    fighter_a_name VARCHAR(255),
    fighter_b_name VARCHAR(255),
    fighter_a_id INTEGER REFERENCES fighters(id) ON DELETE SET NULL,
    fighter_b_id INTEGER REFERENCES fighters(id) ON DELETE SET NULL,
    winner_name VARCHAR(255),
    winner_id INTEGER REFERENCES fighters(id) ON DELETE SET NULL,
    method VARCHAR(100),
    round INTEGER,
    time VARCHAR(20),
    weight_class VARCHAR(100),
    title_fight BOOLEAN DEFAULT FALSE,
    bout_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for detailed fight statistics (from ufc_fight_stats.csv)
CREATE TABLE IF NOT EXISTS fight_stats (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(255),
    bout VARCHAR(500),
    round INTEGER,
    fighter_name VARCHAR(255),
    fighter_id INTEGER REFERENCES fighters(id) ON DELETE SET NULL,
    fight_id INTEGER REFERENCES fights(id) ON DELETE CASCADE,
    -- Strike statistics
    kd INTEGER,                    -- Knockdowns
    sig_str VARCHAR(20),           -- Significant strikes (e.g., "9 of 22")
    sig_str_pct VARCHAR(10),       -- Significant strike percentage
    total_str VARCHAR(20),         -- Total strikes
    td VARCHAR(20),                -- Takedowns (e.g., "0 of 2")
    td_pct VARCHAR(10),            -- Takedown percentage
    sub_att INTEGER,               -- Submission attempts
    rev INTEGER,                   -- Reversals
    ctrl VARCHAR(20),              -- Control time (e.g., "0:39")
    -- Strike location breakdown
    head VARCHAR(20),              -- Head strikes
    body VARCHAR(20),              -- Body strikes
    leg VARCHAR(20),               -- Leg strikes
    distance VARCHAR(20),          -- Distance strikes
    clinch VARCHAR(20),            -- Clinch strikes
    ground VARCHAR(20),            -- Ground strikes
    -- Calculated fields for analysis
    sig_str_landed INTEGER,        -- Extracted from sig_str
    sig_str_attempted INTEGER,     -- Extracted from sig_str
    total_str_landed INTEGER,      -- Extracted from total_str
    total_str_attempted INTEGER,   -- Extracted from total_str
    td_landed INTEGER,             -- Extracted from td
    td_attempted INTEGER,          -- Extracted from td
    ctrl_time_seconds INTEGER,     -- Converted from ctrl
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw data tables to store original CSV imports
CREATE TABLE IF NOT EXISTS raw_fighter_details (
    id SERIAL PRIMARY KEY,
    data JSONB,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_fight_stats (
    id SERIAL PRIMARY KEY,
    data JSONB,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_fighters_name ON fighters(first_name, last_name);
CREATE INDEX idx_fighters_url ON fighters(url);
CREATE INDEX idx_events_date ON events(date);
CREATE INDEX idx_events_url ON events(url);
CREATE INDEX idx_fights_event_id ON fights(event_id);
CREATE INDEX idx_fights_fighters ON fights(fighter_a_id, fighter_b_id);
CREATE INDEX idx_fight_stats_fight_id ON fight_stats(fight_id);
CREATE INDEX idx_fight_stats_fighter_id ON fight_stats(fighter_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_fighters_updated_at BEFORE UPDATE ON fighters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fights_updated_at BEFORE UPDATE ON fights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fight_stats_updated_at BEFORE UPDATE ON fight_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();