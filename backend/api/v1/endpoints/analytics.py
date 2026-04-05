"""api/v1/endpoints/analytics.py — Analytics endpoints.

Routes:
    GET /analytics/style-evolution              Finish rates by year (Product 2)
    GET /analytics/fighter-endurance/{id}       Round-by-round performance (Product 3)
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from schemas.analytics import (
    AgeByWeightClassPoint,
    EnduranceRoundData,
    FighterEnduranceResponse,
    FighterOutputPoint,
    FighterStatsByWeightClass,
    PhysicalStatPoint,
    RoundDistributionPoint,
    StyleEvolutionPoint,
    StyleEvolutionResponse,
    StyleStatsByWeightClassPoint,
    WeightClassYearPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Current UFC weight classes — used to exclude historical non-divisions
_UFC_WEIGHT_CLASSES = (
    "'Heavyweight','Light Heavyweight','Middleweight','Welterweight',"
    "'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',"
    "'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight'"
)


@router.get(
    "/style-evolution",
    response_model=StyleEvolutionResponse,
    summary="Style evolution timeline",
)
def style_evolution(
    weight_class: str | None = Query(None, description="Filter by weight class"),
    db: Session = Depends(get_db),
):
    params: dict = {}
    wc_filter_fr = ""
    wc_filter_fs = ""
    if weight_class:
        wc_filter_fr = "AND fr.weight_class = :weight_class"
        wc_filter_fs = "AND fr.weight_class = :weight_class"
        params["weight_class"] = weight_class

    # ── Query 1: finish rates by year (all years, weight class filter optional) ──
    finish_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            COUNT(*)                               AS total_fights,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS ko_tko_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS submission_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS decision_rate
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
          {wc_filter_fr}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

    # ── Query 2: avg fighter outputs per fight by year (fight_stats, 2015+) ──────
    output_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int          AS year,
            COUNT(DISTINCT per_fighter.fight_id)            AS total_fights,
            ROUND(AVG(per_fighter.sig_str_total)::numeric, 1)::float
                                                            AS avg_sig_str_per_fight,
            ROUND(AVG(per_fighter.td_attempted_total)::numeric, 1)::float
                                                            AS avg_td_attempts_per_fight,
            ROUND(AVG(per_fighter.ctrl_seconds_total)::numeric, 0)::float
                                                            AS avg_ctrl_seconds_per_fight
        FROM (
            SELECT
                fs.fight_id,
                fs.fighter_id,
                SUM(fs.sig_str_landed)  AS sig_str_total,
                SUM(fs.td_attempted)    AS td_attempted_total,
                SUM(fs.ctrl_seconds)    AS ctrl_seconds_total
            FROM fight_stats fs
            WHERE fs."ROUND" NOT ILIKE '%total%'
              AND fs.sig_str_landed IS NOT NULL
            GROUP BY fs.fight_id, fs.fighter_id
        ) per_fighter
        JOIN fight_details fdet ON fdet.id = per_fighter.fight_id
        JOIN fight_results fr   ON fr.fight_id = per_fighter.fight_id
        JOIN event_details ed   ON ed.id = fdet.event_id
        WHERE ed.date_proper >= '2015-01-01'
          {wc_filter_fs}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

    # ── Query 3: finish round distribution by year (weight class filter optional) ─
    round_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            COUNT(*)                               AS total_finishes,
            ROUND(
                COUNT(CASE WHEN fr."ROUND" = 1 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS r1_pct,
            ROUND(
                COUNT(CASE WHEN fr."ROUND" = 2 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS r2_pct,
            ROUND(
                COUNT(CASE WHEN fr."ROUND" = 3 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS r3_pct,
            ROUND(
                COUNT(CASE WHEN fr."ROUND" >= 4 THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS r4plus_pct
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
          AND fr."METHOD" NOT ILIKE '%decision%'
          AND fr."METHOD" NOT ILIKE '%no contest%'
          AND fr."METHOD" NOT ILIKE '%dq%'
          AND fr."ROUND" IS NOT NULL
          {wc_filter_fr}
        GROUP BY year
        ORDER BY year
    """), params).mappings().all()

    # ── Query 4: finish rates by weight class × year (heatmap, always all wcs) ───
    heatmap_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            fr.weight_class,
            COUNT(*)                               AS total_fights,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%KO%' OR fr."METHOD" ILIKE '%TKO%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS ko_tko_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Submission%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS submission_rate,
            ROUND(
                COUNT(CASE WHEN fr."METHOD" ILIKE '%Decision%'
                           THEN 1 END)::numeric / NULLIF(COUNT(*), 0), 4
            )::float                               AS decision_rate
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
          AND fr.weight_class IN ({_UFC_WEIGHT_CLASSES})
        GROUP BY year, fr.weight_class
        ORDER BY year, fr.weight_class
    """)).mappings().all()

    # ── Query 5: avg height/reach by weight class × year (always all wcs) ────────
    physical_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int          AS year,
            fr.weight_class,
            ROUND(AVG(ft.height_inches)::numeric, 1)::float AS avg_height_inches,
            ROUND(AVG(ft.reach_inches)::numeric, 1)::float  AS avg_reach_inches,
            COUNT(DISTINCT fr.fighter_id)                   AS fighter_count
        FROM fight_results fr
        JOIN event_details ed   ON ed.id = fr.event_id
        JOIN fighter_tott ft    ON ft.fighter_id = fr.fighter_id
        WHERE ft.height_inches IS NOT NULL
          AND ft.reach_inches IS NOT NULL
          AND fr.weight_class IN ({_UFC_WEIGHT_CLASSES})
        GROUP BY year, fr.weight_class
        HAVING COUNT(DISTINCT fr.fighter_id) >= 5
        ORDER BY year, fr.weight_class
    """)).mappings().all()

    # ── Query 6: avg fighter age by weight class × year (always all wcs) ─────────
    age_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            fr.weight_class,
            ROUND(AVG(
                EXTRACT(YEAR FROM AGE(ed.date_proper, ft.dob_date)) +
                EXTRACT(MONTH FROM AGE(ed.date_proper, ft.dob_date)) / 12.0
            )::numeric, 1)::float                  AS avg_age,
            COUNT(DISTINCT fr.fighter_id)          AS fighter_count
        FROM fight_results fr
        JOIN event_details ed ON ed.id = fr.event_id
        JOIN fighter_tott ft  ON ft.fighter_id = fr.fighter_id
        WHERE ft.dob_date IS NOT NULL
          AND ed.date_proper IS NOT NULL
          AND fr.weight_class IN ({_UFC_WEIGHT_CLASSES})
        GROUP BY year, fr.weight_class
        HAVING COUNT(DISTINCT fr.fighter_id) >= 5
        ORDER BY year, fr.weight_class
    """)).mappings().all()

    # ── Query 7: career stats by weight class (always all wcs) ───────────────────
    # str_acc / str_def / td_acc / td_def stored as "41%" text — strip % and cast
    stats_rows = db.execute(text(f"""
        SELECT
            fr.weight_class,
            ROUND(AVG(ft.slpm)::numeric,  2)::float AS avg_slpm,
            ROUND(AVG(NULLIF(REPLACE(ft.str_acc, '%', ''), '')::numeric / 100), 4)::float AS avg_str_acc,
            ROUND(AVG(ft.sapm)::numeric,  2)::float AS avg_sapm,
            ROUND(AVG(NULLIF(REPLACE(ft.str_def, '%', ''), '')::numeric / 100), 4)::float AS avg_str_def,
            ROUND(AVG(ft.td_avg)::numeric, 2)::float AS avg_td_avg,
            ROUND(AVG(NULLIF(REPLACE(ft.td_acc, '%', ''), '')::numeric / 100), 4)::float AS avg_td_acc,
            ROUND(AVG(NULLIF(REPLACE(ft.td_def, '%', ''), '')::numeric / 100), 4)::float AS avg_td_def,
            ROUND(AVG(ft.sub_avg)::numeric, 2)::float AS avg_sub_avg,
            COUNT(DISTINCT fr.fighter_id)             AS fighter_count
        FROM fight_results fr
        JOIN fighter_tott ft ON ft.fighter_id = fr.fighter_id
        WHERE ft.slpm IS NOT NULL
          AND fr.weight_class IN ({_UFC_WEIGHT_CLASSES})
        GROUP BY fr.weight_class
        HAVING COUNT(DISTINCT fr.fighter_id) >= 10
        ORDER BY fr.weight_class
    """)).mappings().all()

    # ── Query 8: per-year style metrics by weight class from fight_stats ─────────
    style_rows = db.execute(text(f"""
        SELECT
            EXTRACT(YEAR FROM ed.date_proper)::int AS year,
            fr.weight_class,
            ROUND(AVG(
                pf.sig_str_landed::float / NULLIF(fr.total_fight_time_seconds / 60.0, 0)
            )::numeric, 2)::float AS avg_slpm,
            ROUND(AVG(
                CASE WHEN pf.sig_str_attempted > 0
                     THEN pf.sig_str_landed::float / pf.sig_str_attempted
                     ELSE NULL END
            )::numeric, 4)::float AS avg_str_acc,
            ROUND(AVG(pf.td_landed)::numeric, 2)::float AS avg_td_per_fight,
            ROUND(AVG(
                CASE WHEN pf.td_attempted > 0
                     THEN pf.td_landed::float / pf.td_attempted
                     ELSE NULL END
            )::numeric, 4)::float AS avg_td_acc,
            ROUND(AVG(pf.ctrl_seconds_total)::numeric, 0)::float AS avg_ctrl_seconds,
            COUNT(DISTINCT pf.fight_id) AS fight_count
        FROM (
            SELECT
                fs.fight_id,
                fs.fighter_id,
                SUM(fs.sig_str_landed)    AS sig_str_landed,
                SUM(fs.sig_str_attempted) AS sig_str_attempted,
                SUM(fs.td_landed)         AS td_landed,
                SUM(fs.td_attempted)      AS td_attempted,
                SUM(fs.ctrl_seconds)      AS ctrl_seconds_total
            FROM fight_stats fs
            WHERE fs."ROUND" NOT ILIKE '%total%'
              AND fs.sig_str_landed IS NOT NULL
            GROUP BY fs.fight_id, fs.fighter_id
        ) pf
        JOIN fight_results fr ON fr.fight_id = pf.fight_id
        JOIN event_details ed  ON ed.id = fr.event_id
        WHERE ed.date_proper IS NOT NULL
          AND fr.total_fight_time_seconds > 0
          AND fr.weight_class IN ({_UFC_WEIGHT_CLASSES})
        GROUP BY year, fr.weight_class
        HAVING COUNT(DISTINCT pf.fight_id) >= 10
        ORDER BY year, fr.weight_class
    """)).mappings().all()

    current_year = date.today().year
    return StyleEvolutionResponse(
        data=[
            StyleEvolutionPoint(
                year=r["year"],
                ko_tko_rate=r["ko_tko_rate"] or 0.0,
                submission_rate=r["submission_rate"] or 0.0,
                decision_rate=r["decision_rate"] or 0.0,
                finish_rate=round((r["ko_tko_rate"] or 0.0) + (r["submission_rate"] or 0.0), 4),
                total_fights=r["total_fights"],
                is_partial_year=r["year"] == current_year,
                weight_class=weight_class,
            )
            for r in finish_rows
        ],
        fighter_outputs=[
            FighterOutputPoint(
                year=r["year"],
                avg_sig_str_per_fight=r["avg_sig_str_per_fight"] or 0.0,
                avg_td_attempts_per_fight=r["avg_td_attempts_per_fight"] or 0.0,
                avg_ctrl_seconds_per_fight=r["avg_ctrl_seconds_per_fight"] or 0.0,
                total_fights=r["total_fights"],
                is_partial_year=r["year"] == current_year,
            )
            for r in output_rows
        ],
        round_distribution=[
            RoundDistributionPoint(
                year=r["year"],
                r1_pct=r["r1_pct"] or 0.0,
                r2_pct=r["r2_pct"] or 0.0,
                r3_pct=r["r3_pct"] or 0.0,
                r4plus_pct=r["r4plus_pct"] or 0.0,
                total_finishes=r["total_finishes"],
                is_partial_year=r["year"] == current_year,
            )
            for r in round_rows
        ],
        heatmap_data=[
            WeightClassYearPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                finish_rate=round((r["ko_tko_rate"] or 0.0) + (r["submission_rate"] or 0.0), 4),
                ko_tko_rate=r["ko_tko_rate"] or 0.0,
                submission_rate=r["submission_rate"] or 0.0,
                decision_rate=r["decision_rate"] or 0.0,
                total_fights=r["total_fights"],
            )
            for r in heatmap_rows
        ],
        physical_stats=[
            PhysicalStatPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_height_inches=r["avg_height_inches"] or 0.0,
                avg_reach_inches=r["avg_reach_inches"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in physical_rows
        ],
        age_data=[
            AgeByWeightClassPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_age=r["avg_age"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in age_rows
        ],
        fighter_stats=[
            FighterStatsByWeightClass(
                weight_class=r["weight_class"],
                avg_slpm=r["avg_slpm"] or 0.0,
                avg_str_acc=r["avg_str_acc"] or 0.0,
                avg_sapm=r["avg_sapm"] or 0.0,
                avg_str_def=r["avg_str_def"] or 0.0,
                avg_td_avg=r["avg_td_avg"] or 0.0,
                avg_td_acc=r["avg_td_acc"] or 0.0,
                avg_td_def=r["avg_td_def"] or 0.0,
                avg_sub_avg=r["avg_sub_avg"] or 0.0,
                fighter_count=r["fighter_count"],
            )
            for r in stats_rows
        ],
        style_stats=[
            StyleStatsByWeightClassPoint(
                year=r["year"],
                weight_class=r["weight_class"],
                avg_slpm=r["avg_slpm"] or 0.0,
                avg_str_acc=r["avg_str_acc"] or 0.0,
                avg_td_per_fight=r["avg_td_per_fight"] or 0.0,
                avg_td_acc=r["avg_td_acc"] or 0.0,
                avg_ctrl_seconds=r["avg_ctrl_seconds"] or 0.0,
                fight_count=r["fight_count"],
            )
            for r in style_rows
        ],
        weight_class=weight_class,
    )


@router.get(
    "/fighter-endurance/{fighter_id}",
    response_model=FighterEnduranceResponse,
    summary="Fighter endurance profile",
)
def fighter_endurance(fighter_id: str, db: Session = Depends(get_db)):
    fighter = db.execute(text("""
        SELECT
            fd.id,
            fd."FIRST" || ' ' || fd."LAST" AS full_name
        FROM fighter_details fd
        WHERE fd.id = :fighter_id
    """), {"fighter_id": fighter_id}).mappings().first()

    if fighter is None:
        raise HTTPException(status_code=404, detail=f"Fighter '{fighter_id}' not found")

    rows = db.execute(text("""
        SELECT
            "ROUND"::int                           AS round,
            ROUND(AVG(sig_str_landed)::numeric, 2)::float
                                                   AS avg_sig_str_landed,
            ROUND(
                AVG(
                    CASE WHEN sig_str_attempted > 0
                         THEN sig_str_landed::float / sig_str_attempted
                         ELSE NULL END
                )::numeric, 4
            )::float                               AS avg_sig_str_pct,
            ROUND(AVG(ctrl_seconds)::numeric, 2)::float
                                                   AS avg_ctrl_seconds,
            ROUND(AVG(kd_int)::numeric, 4)::float  AS avg_kd,
            COUNT(*)::int                          AS fight_count
        FROM fight_stats
        WHERE fighter_id = :fighter_id
          AND "ROUND" ~ '^[0-9]+$'
        GROUP BY "ROUND"::int
        ORDER BY "ROUND"::int
    """), {"fighter_id": fighter_id}).mappings().all()

    note = None
    if not rows:
        note = "No detailed round-by-round stats available (pre-2015 career or no fight_stats data)"

    return FighterEnduranceResponse(
        fighter_id=fighter_id,
        fighter_name=fighter["full_name"],
        rounds=[EnduranceRoundData(**dict(r)) for r in rows],
        note=note,
    )
