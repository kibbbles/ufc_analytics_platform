-- 010_tina_black_identity.sql
-- Renames one fighter row to the name UFCStats now lists for its URL.
--
-- Found by the "name matches none of the fighter's own bouts" check added in
-- validate_etl.py, which failed the Post-Scrape ETL on 2026-09-27 and
-- 2026-10-04 and so blocked the pre-fight prediction archive both weeks.
--
-- Ground truth, read from ufcstats.com on 2026-10-10:
--
--   .../fighter-details/a1a91dbf41a029c4
--       Tina Black, no nickname, 17-4-0 (1 NC), 5' 4", 115 lbs, reach 63",
--       orthodox, DOB May 06 1996.  Holds one UFC fight: Tina Black vs.
--       Melissa Amaya, UFC Fight Night: Rosas Jr. vs. Barcelos, Sep 26 2026,
--       plus a 2021 Dana White's Contender Series bout.
--
-- fighter_details held this row as FIRST 'Valesca', LAST 'Machado', NICKNAME
-- 'Tina Black' - an older listing that carried her ring name as a nickname.
-- UFCStats has since renamed the profile, so every bout and the tale-of-the-tape
-- row read 'Tina Black' while the fighter row did not.  The id, URL and every FK
-- already agree, so this is a rename only: no fight is filed under the wrong
-- person and no fight_details, fight_results or fight_stats row changes.
--
-- The tale-of-the-tape row already carries the right name and URL but no
-- measurements.  Refill it from the live page afterwards:
--
--     python backend/scraper/refresh_fighter_tott.py a1a91dbf
--     python backend/scraper/post_scrape_clean.py --phase 3

BEGIN;

UPDATE fighter_details
SET    "FIRST" = 'Tina', "LAST" = 'Black', "NICKNAME" = NULL
WHERE  id = 'a1a91dbf'
  AND  "URL" = 'http://ufcstats.com/fighter-details/a1a91dbf41a029c4';

COMMIT;
