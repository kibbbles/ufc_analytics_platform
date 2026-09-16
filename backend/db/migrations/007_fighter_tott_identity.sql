-- 007_fighter_tott_identity.sql
-- Repairs fighter_tott identity and makes the corruption unrepresentable.
--
-- Motivation: fighter_tott.fighter_id was populated by joining on name
-- (populate_foreign_keys.py, pre-007):
--
--     UPDATE fighter_tott ft SET fighter_id = fd.id
--     FROM fighter_details fd
--     WHERE TRIM(ft."FIGHTER") = TRIM(CONCAT(fd."FIRST", ' ', fd."LAST"))
--
-- Names are not identifiers.  Seven UFCStats fighters share a name with another
-- fighter, and UPDATE ... FROM with two matching rows picks one arbitrarily and
-- reports success.  The result was that one person's tale of the tape was filed
-- under the other person's id: Michael McDonald (b. 1965) carried the height,
-- reach and DOB of Michael McDonald (b. 1991), and Jean Silva (b. 1977) carried
-- Jean Silva's (b. 1996).  Coverage checks read 100% throughout, because every
-- row was populated -- just not with the right human's numbers.
--
-- The repair key is fighter_tott.id, which already equals the owning
-- fighter_details.id for 4,428 of the 4,446 rows that have one.  The 18
-- exceptions are precisely the defects: 7 cross-contaminated rows and 11 that
-- the name join never matched at all ("ColleyBradford", "Kwon Won Il" vs
-- "Kwon Wonil", "Shaqueme Rock" vs "Shem Rock").
--
-- Verified against ufcstats.com before writing: after this migration
-- d52ef694 carries dob_date 1965-02-06 and 9211aae0 carries 1977-10-08, both
-- matching their fighter pages.  Three fighters lose populated fields
-- (c8661e20, d52ef694, de277a4a); in every case the removed values belonged to
-- the namesake, and the resulting NULLs match the '--' shown on UFCStats.
--
-- Idempotent: re-running is a no-op once the constraint exists.

BEGIN;

-- Phase 1 - re-link each row to its true owner.
-- Non-destructive.  Fixes the 7 contaminated rows and links the 11 the name
-- join missed.
UPDATE fighter_tott t
SET    fighter_id = t.id
FROM   fighter_details fd
WHERE  fd.id = t.id
  AND  t.fighter_id IS DISTINCT FROM t.id;

-- Phase 2 - collapse duplicates to one row per fighter.
-- Preference order: the canonical row (id = fighter_id) first, then whichever
-- row carries the most populated measurements, then id for determinism.
DELETE FROM fighter_tott t
USING (
    SELECT id,
           row_number() OVER (
               PARTITION BY fighter_id
               ORDER BY (id = fighter_id)          DESC,
                        (dob_date      IS NOT NULL) DESC,
                        (height_inches IS NOT NULL) DESC,
                        (reach_inches  IS NOT NULL) DESC,
                        id
           ) AS rn
    FROM   fighter_tott
    WHERE  fighter_id IS NOT NULL
) d
WHERE t.id = d.id
  AND d.rn > 1;

-- Phase 3 - make it impossible to reintroduce.
-- A duplicate fighter_id is now a write error rather than something a
-- validation run has to notice afterwards.  NULL fighter_id stays permitted:
-- Postgres allows multiple NULLs under a UNIQUE constraint, so tott rows for
-- fighters absent from fighter_details are unaffected.
ALTER TABLE fighter_tott
    DROP CONSTRAINT IF EXISTS fighter_tott_fighter_id_key;

ALTER TABLE fighter_tott
    ADD CONSTRAINT fighter_tott_fighter_id_key UNIQUE (fighter_id);

COMMIT;
