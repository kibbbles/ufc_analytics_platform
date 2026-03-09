-- Migration 001: Phase 2 upcoming events tables
-- Creates upcoming_events, upcoming_fights, upcoming_predictions

-- ---------------------------------------------------------------------------
-- upcoming_events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS upcoming_events (
    id           VARCHAR(6) PRIMARY KEY,
    event_name   TEXT NOT NULL,
    date_proper  DATE NOT NULL,
    location     TEXT,
    ufcstats_url TEXT UNIQUE NOT NULL,
    is_numbered  BOOLEAN,
    scraped_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_upcoming_events_date
    ON upcoming_events (date_proper);

-- ---------------------------------------------------------------------------
-- upcoming_fights
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS upcoming_fights (
    id             VARCHAR(6) PRIMARY KEY,
    event_id       VARCHAR(6) NOT NULL REFERENCES upcoming_events(id),
    fighter_a_name TEXT,
    fighter_b_name TEXT,
    fighter_a_id   VARCHAR(6) REFERENCES fighter_details(id),  -- nullable: new fighters
    fighter_b_id   VARCHAR(6) REFERENCES fighter_details(id),  -- nullable: new fighters
    fighter_a_url  TEXT,
    fighter_b_url  TEXT,
    weight_class   TEXT,
    is_title_fight BOOLEAN DEFAULT FALSE,
    ufcstats_url   TEXT,
    scraped_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (event_id, fighter_a_url, fighter_b_url)
);

CREATE INDEX IF NOT EXISTS idx_upcoming_fights_event_id
    ON upcoming_fights (event_id);

CREATE INDEX IF NOT EXISTS idx_upcoming_fights_fighter_a_id
    ON upcoming_fights (fighter_a_id);

CREATE INDEX IF NOT EXISTS idx_upcoming_fights_fighter_b_id
    ON upcoming_fights (fighter_b_id);

-- ---------------------------------------------------------------------------
-- upcoming_predictions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS upcoming_predictions (
    id            VARCHAR(6) PRIMARY KEY,
    fight_id      VARCHAR(6) UNIQUE NOT NULL REFERENCES upcoming_fights(id),
    model_version TEXT DEFAULT 'win_loss_v1',
    win_prob_a    FLOAT,
    win_prob_b    FLOAT,
    method_ko_tko FLOAT,
    method_sub    FLOAT,
    method_dec    FLOAT,
    features_json JSONB,
    feature_hash  TEXT,
    predicted_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_upcoming_predictions_fight_id
    ON upcoming_predictions (fight_id);
