-- 009_montanha_identity.sql
-- Repairs two fighter rows that carry each other's names, and the one fight
-- that was filed under the wrong man as a result.
--
-- Found by the check added with migration 008: fight_details now stores each
-- fighter's UFCStats URL, so a fighter FK can be compared with the fighter that
-- URL belongs to.  One fight out of 8,875 disagreed.
--
-- Ground truth, read from ufcstats.com on 2026-09-18:
--
--   .../fighter-details/1f8cd7634e8286ff
--       Jose Montanha, no nickname, 7-1-0, 6' 4", 259 lbs, reach 76",
--       orthodox, DOB Aug 25 1996.  Holds one UFC fight: Louie Sutherland vs.
--       Jose Montanha, UFC Fight Night: Gamrot vs. Salkilld, Aug 08 2026.
--
--   .../fighter-details/4e30f2761b6bd3b5
--       Henrique Da Silva Lopes, nickname "Montanha", 5-2-0, height and reach
--       unlisted, 265 lbs, orthodox, DOB Mar 08 1985.  No UFC fights.
--
-- fighter_details had the two names and both nicknames exchanged.  Each row's
-- id and URL agree with each other, so the corruption is in the names alone:
-- id 1f8cd763 (Montanha's URL) was named Henrique Da Silva Lopes and carried
-- his nickname, and id 4e30f276 (Da Silva Lopes's URL) was named Jose Montanha.
--
-- The cost of that swap: fight_details, fight_results and fight_stats resolve
-- fighters by name, so Montanha's only UFC fight - a win over Louie Sutherland
-- - was recorded as a win for Da Silva Lopes, who has never fought in the UFC.
--
-- Both tale-of-the-tape rows are also wrong: each holds the other fighter's
-- height, weight, DOB and record, and some of it is stale (6' 3" / 240 lbs
-- matches neither man's page today).  This migration restores each row's
-- identity - its name and its own URL - and clears the measurements rather
-- than swapping them, because swapping would preserve values that are wrong in
-- a second way.  A NULL is a gap validation can see; a swapped-but-stale
-- number is not.  The measurements are refilled from the live fighter pages
-- immediately afterwards:
--
--     python backend/scraper/refresh_fighter_tott.py 1f8cd763 4e30f276
--     python backend/scraper/post_scrape_clean.py --phase 3

BEGIN;

-- 1. Names and nicknames, each row set from its own URL's page.
UPDATE fighter_details
SET    "FIRST" = 'Jose', "LAST" = 'Montanha', "NICKNAME" = NULL
WHERE  id = '1f8cd763'
  AND  "URL" = 'http://ufcstats.com/fighter-details/1f8cd7634e8286ff';

UPDATE fighter_details
SET    "FIRST" = 'Henrique', "LAST" = 'Da Silva Lopes', "NICKNAME" = 'Montanha'
WHERE  id = '4e30f276'
  AND  "URL" = 'http://ufcstats.com/fighter-details/4e30f2761b6bd3b5';

-- 2. The fight itself. Keyed on the stored UFCStats URL, not on the name that
--    caused the defect, so this is a no-op if the FK is already right.
UPDATE fight_details
SET    fighter_b_id = '1f8cd763'
WHERE  id = 'MHJXSS'
  AND  fighter_b_url = 'http://ufcstats.com/fighter-details/1f8cd7634e8286ff'
  AND  fighter_b_id  = '4e30f276';

-- Montanha won, so he is fight_results.fighter_id (winner), not opponent_id.
UPDATE fight_results
SET    fighter_id = '1f8cd763'
WHERE  fight_id = 'MHJXSS'
  AND  fighter_id = '4e30f276';

UPDATE fight_stats
SET    fighter_id = '1f8cd763'
WHERE  fight_id = 'MHJXSS'
  AND  fighter_id = '4e30f276'
  AND  "FIGHTER" = 'Jose Montanha';

-- 3. Tale of the tape. Identity comes from the fighter row, which step 1 just
--    corrected; every measurement is cleared for the refresh above. The URL
--    matters beyond identity: both bulk stat scrapers select on it, so a row
--    with no URL would be invisible to the tools that refill it.
UPDATE fighter_tott ft
SET    "FIGHTER" = trim(fd."FIRST" || ' ' || fd."LAST"),
       "URL"    = fd."URL",
       "HEIGHT" = NULL, "WEIGHT" = NULL, "REACH" = NULL,
       "STANCE" = NULL, "DOB" = NULL,
       height_inches = NULL, weight_lbs = NULL, reach_inches = NULL,
       dob_date = NULL,
       career_wins = NULL, career_losses = NULL, career_draws = NULL,
       slpm = NULL, str_acc = NULL, sapm = NULL, str_def = NULL,
       td_avg = NULL, td_acc = NULL, td_def = NULL, sub_avg = NULL
FROM   fighter_details fd
WHERE  ft.fighter_id = fd.id
  AND  ft.fighter_id IN ('1f8cd763', '4e30f276');

COMMIT;
