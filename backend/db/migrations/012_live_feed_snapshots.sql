-- 012_live_feed_snapshots.sql
-- Raw fight-night recordings for Phase 0 of the live-results work.
--
-- record_live_feeds.py polls UFC.com's event feed and ESPN's UFC scoreboard
-- once a minute through one event and writes a row per source per poll. The
-- recording answers what a completed event cannot: which in-progress status
-- values the feeds use, how soon a result appears after the fight ends, and
-- how corrections and cancellations show up.
--
-- One row per fetch, including failures and unchanged responses, so the
-- polling record itself is complete. The body is stored only when it changed
-- since the previous fetch from the same source, gzip-compressed, which keeps
-- one event to a few megabytes.
--
-- Nothing reads this table at runtime and nothing in features/ or ml/ may.

BEGIN;

CREATE TABLE IF NOT EXISTS live_feed_snapshots (
    id          BIGSERIAL PRIMARY KEY,
    recording   TEXT        NOT NULL,   -- e.g. 'ufc-1352', one recording per event
    source      TEXT        NOT NULL,   -- 'ufc_feed' | 'espn_scoreboard'
    fetched_at  TIMESTAMPTZ NOT NULL,
    http_status INTEGER,                -- NULL when the request never completed
    latency_ms  INTEGER,
    sha256      TEXT,                   -- of the decompressed body; NULL on failure
    changed     BOOLEAN     NOT NULL DEFAULT FALSE,
    body_gz     BYTEA,                  -- gzip of the body, only when changed
    summary     JSONB,                  -- bout status counts parsed at fetch time
    error       TEXT
);

CREATE INDEX IF NOT EXISTS live_feed_snapshots_recording_idx
    ON live_feed_snapshots (recording, source, fetched_at);

COMMENT ON TABLE live_feed_snapshots IS
    'Phase 0 fight-night recordings (record_live_feeds.py). Raw research data; never read by the app or training.';

COMMIT;
