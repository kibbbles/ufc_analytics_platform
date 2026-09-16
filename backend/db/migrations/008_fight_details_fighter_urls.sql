-- 008_fight_details_fighter_urls.sql
-- Stores each fighter's UFCStats profile URL on the completed fight row, so
-- fight_details.fighter_a_id / fighter_b_id can be resolved by identity rather
-- than by the names in "BOUT".
--
-- Motivation: the completed-event FK resolver (populate_fighter_fks.py) parsed
-- names out of "BOUT" because no fight table stored a fighter URL.  A name
-- shared by two fighters cannot be resolved that way, so it is refused and the
-- FK left NULL.  Noche UFC: Silva vs. Delgado (2026-09-12) hit exactly that:
-- "Jean Silva" belongs to 52ef95b5 and 9211aae0, the main event was stored with
-- fighter_a_id NULL, and the live site showed it with no winner.  The scraper
-- had the right URL in hand from the fight page the whole time and discarded it.
--
-- URLs are recorded as scraped, never derived from an already-resolved FK:
-- copying fighter_details."URL" through a name-resolved id would launder a name
-- guess into something that looks like identity.  Historical rows therefore stay
-- NULL until a fight page is actually read for them.
--
-- Additive and safe: existing rows get NULL, which the resolver treats as
-- "fall back to name resolution", the behaviour before this migration.

ALTER TABLE fight_details
    ADD COLUMN IF NOT EXISTS fighter_a_url TEXT,
    ADD COLUMN IF NOT EXISTS fighter_b_url TEXT;

COMMENT ON COLUMN fight_details.fighter_a_url IS
    'UFCStats profile URL of the first fighter in "BOUT", as scraped from the fight page. Identity key for fighter_a_id.';
COMMENT ON COLUMN fight_details.fighter_b_url IS
    'UFCStats profile URL of the second fighter in "BOUT", as scraped from the fight page. Identity key for fighter_b_id.';
