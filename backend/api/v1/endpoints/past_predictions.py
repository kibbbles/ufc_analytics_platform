"""api/v1/endpoints/past_predictions.py — Model scorecard endpoint.

Routes:
    GET /past-predictions                          Summary stats + recent predictions list
    GET /past-predictions/events                   Paginated event list with accuracy per event
    GET /past-predictions/events/{event_id}        All fight predictions for a given event
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

_METRICS_PATH = Path(__file__).parent.parent.parent.parent / "models" / "metrics.json"


def _test_date_from() -> str:
    """Return the test-set start date from the latest model metrics, or empty string."""
    try:
        m = json.loads(_METRICS_PATH.read_text())
        return m["test_date_range"][0]
    except Exception:
        return ""

from api.dependencies import get_db
from schemas.past_prediction import (
    PastPredictionItem,
    PastPredictionSummary,
    PastPredictionsResponse,
    PastPredictionEventItem,
    PastPredictionEventsResponse,
    PastPredictionEventDetail,
    PastPredictionFightsResponse,
    ConfBucket,
    WeightClassStat,
    ModalStatsSection,
    PastPredictionModalStats,
    VegasComparison,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PastPredictionsResponse,
    summary="Model scorecard — summary accuracy + recent prediction outcomes",
)
def get_past_predictions(
    limit: int = Query(default=20, ge=1, le=200, description="Number of recent predictions to return"),
    db: Session = Depends(get_db),
) -> PastPredictionsResponse:
    # ---- Summary row --------------------------------------------------------
    summary_row = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (fight_id) *
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT
            COUNT(*) FILTER (WHERE is_correct IS NOT NULL)                    AS total_fights,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)                      AS correct,
            SUM(CASE WHEN confidence >= 0.65 THEN 1 ELSE 0 END)              AS high_conf_fights,
            SUM(CASE WHEN is_correct AND confidence >= 0.65 THEN 1 ELSE 0 END) AS high_conf_correct,
            AVG(confidence) FILTER (WHERE is_correct IS NOT NULL)             AS avg_confidence,
            MAX(event_date)                                                   AS date_to
        FROM best
    """)).mappings().first()

    total_fights     = int(summary_row["total_fights"] or 0)
    correct          = int(summary_row["correct"] or 0)
    high_conf_fights = int(summary_row["high_conf_fights"] or 0)
    high_conf_correct= int(summary_row["high_conf_correct"] or 0)
    avg_confidence   = float(summary_row["avg_confidence"] or 0.0)

    accuracy          = correct / total_fights if total_fights > 0 else 0.0
    high_conf_accuracy= high_conf_correct / high_conf_fights if high_conf_fights > 0 else 0.0

    date_from_val = _test_date_from()
    date_to_val   = summary_row["date_to"]

    years_rows = db.execute(text("""
        SELECT DISTINCT EXTRACT(YEAR FROM event_date)::int AS yr
        FROM past_predictions
        WHERE event_date IS NOT NULL
        ORDER BY yr DESC
    """)).scalars().all()  # all rows fine here — just listing years

    # ---- Pre-fight only stats (prediction_source = 'pre_fight_archive') ------
    pf_row = db.execute(text("""
        SELECT
            COUNT(*)                                                            AS total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)                        AS correct,
            AVG(confidence)                                                     AS avg_confidence,
            SUM(CASE WHEN confidence >= 0.65 THEN 1 ELSE 0 END)               AS high_conf_fights,
            SUM(CASE WHEN is_correct AND confidence >= 0.65 THEN 1 ELSE 0 END) AS high_conf_correct
        FROM past_predictions
        WHERE prediction_source = 'pre_fight_archive'
          AND is_correct IS NOT NULL
    """)).mappings().first()

    pf_total          = int(pf_row["total"] or 0)
    pf_correct        = int(pf_row["correct"] or 0)
    pf_avg_conf       = float(pf_row["avg_confidence"] or 0.0)
    pf_hc_fights      = int(pf_row["high_conf_fights"] or 0)
    pf_hc_correct     = int(pf_row["high_conf_correct"] or 0)
    pf_accuracy       = pf_correct / pf_total if pf_total > 0 else 0.0
    pf_hc_accuracy    = pf_hc_correct / pf_hc_fights if pf_hc_fights > 0 else 0.0

    summary = PastPredictionSummary(
        total_fights=total_fights,
        correct=correct,
        accuracy=accuracy,
        avg_confidence=avg_confidence,
        high_conf_fights=high_conf_fights,
        high_conf_correct=high_conf_correct,
        high_conf_accuracy=high_conf_accuracy,
        date_from=date_from_val,
        date_to=str(date_to_val) if date_to_val else "",
        available_years=[int(y) for y in years_rows],
        pre_fight_total=pf_total,
        pre_fight_correct=pf_correct,
        pre_fight_accuracy=pf_accuracy,
        pre_fight_avg_confidence=pf_avg_conf,
        pre_fight_high_conf_fights=pf_hc_fights,
        pre_fight_high_conf_correct=pf_hc_correct,
        pre_fight_high_conf_accuracy=pf_hc_accuracy,
    )

    # ---- Recent predictions -------------------------------------------------
    if total_fights == 0:
        return PastPredictionsResponse(summary=summary, recent=[])

    recent_rows = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (fight_id)
                fight_id, event_id, event_name, event_date,
                fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
                weight_class, win_prob_a, win_prob_b,
                pred_method_ko_tko, pred_method_sub, pred_method_dec,
                predicted_winner_id, predicted_method,
                actual_winner_id, actual_method,
                is_correct, confidence, is_upset,
                prediction_source, pre_fight_predicted_at
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT * FROM best
        ORDER BY event_date DESC, fight_id
        LIMIT :limit
    """), {"limit": limit}).mappings().all()

    recent = [PastPredictionItem(**dict(r)) for r in recent_rows]

    return PastPredictionsResponse(summary=summary, recent=recent)


@router.get(
    "/events",
    response_model=PastPredictionEventsResponse,
    summary="Paginated list of events that have model predictions, most recent first",
)
def list_past_prediction_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    search: str | None = Query(None),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
) -> PastPredictionEventsResponse:
    params: dict = {}
    conditions: list[str] = []

    if search:
        conditions.append("LOWER(event_name) LIKE LOWER(:search)")
        params["search"] = f"%{search}%"
    if year:
        conditions.append("EXTRACT(YEAR FROM event_date) = :year")
        params["year"] = year

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total: int = db.execute(text(f"""
        WITH best AS (
            SELECT DISTINCT ON (fight_id) *
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT COUNT(DISTINCT event_id)
        FROM best
        {where}
    """), params).scalar() or 0

    params["limit"]  = page_size
    params["offset"] = (page - 1) * page_size

    rows = db.execute(text(f"""
        WITH best AS (
            SELECT DISTINCT ON (fight_id) *
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT
            event_id,
            MAX(event_name)   AS event_name,
            MAX(event_date)   AS event_date,
            COUNT(*) FILTER (WHERE is_correct IS NOT NULL) AS fight_count,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)  AS correct_count
        FROM best
        {where}
        GROUP BY event_id
        ORDER BY MAX(event_date) DESC
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    items = [
        PastPredictionEventItem(
            event_id=r["event_id"],
            event_name=r["event_name"],
            event_date=r["event_date"],
            fight_count=int(r["fight_count"]),
            correct_count=int(r["correct_count"]),
            accuracy=int(r["correct_count"]) / int(r["fight_count"]) if r["fight_count"] else 0.0,
        )
        for r in rows
    ]

    return PastPredictionEventsResponse(
        data=items,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=PastPredictionEventDetail,
    summary="All model predictions for a specific past event",
)
def get_past_prediction_event(
    event_id: str,
    db: Session = Depends(get_db),
) -> PastPredictionEventDetail:
    rows = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (fight_id)
                fight_id, event_id, event_name, event_date,
                fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
                weight_class, win_prob_a, win_prob_b,
                pred_method_ko_tko, pred_method_sub, pred_method_dec,
                predicted_winner_id, predicted_method,
                actual_winner_id, actual_method,
                is_correct, confidence, is_upset,
                prediction_source, pre_fight_predicted_at
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT best.*
        FROM best
        LEFT JOIN fight_details fd ON fd.id = best.fight_id
        LEFT JOIN LATERAL (
            SELECT position FROM upcoming_fights uf
            WHERE (
                (uf.fighter_a_id = best.fighter_a_id AND uf.fighter_b_id = best.fighter_b_id)
                OR
                (uf.fighter_a_id = best.fighter_b_id AND uf.fighter_b_id = best.fighter_a_id)
            )
            ORDER BY uf.scraped_at DESC
            LIMIT 1
        ) uf_pos ON TRUE
        WHERE best.event_id = :event_id
        ORDER BY COALESCE(uf_pos.position, fd.position, 999) ASC
    """), {"event_id": event_id}).mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No predictions found for event '{event_id}'")

    fights = [PastPredictionItem(**dict(r)) for r in rows]
    predicted = [f for f in fights if f.is_correct is not None]
    correct_count = sum(1 for f in predicted if f.is_correct)
    sample = fights[0]

    return PastPredictionEventDetail(
        event_id=event_id,
        event_name=sample.event_name,
        event_date=sample.event_date,
        fight_count=len(predicted),
        correct_count=correct_count,
        accuracy=correct_count / len(predicted) if predicted else 0.0,
        fights=fights,
    )


_FIGHT_COLS = """
    fight_id, event_id, event_name, event_date,
    fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
    weight_class, model_version, win_prob_a, win_prob_b,
    pred_method_ko_tko, pred_method_sub, pred_method_dec,
    predicted_winner_id, predicted_method,
    actual_winner_id, actual_method,
    is_correct, confidence, is_upset,
    features_json,
    prediction_source, pre_fight_predicted_at
"""

# CTE that deduplicates past_predictions to one row per fight, preferring
# pre_fight_archive over backfill so the scorecard shows leakage-free numbers.
_DEDUP_CTE = """
    WITH best AS (
        SELECT DISTINCT ON (fight_id)
            fight_id, event_id, event_name, event_date,
            fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
            weight_class, model_version, win_prob_a, win_prob_b,
            pred_method_ko_tko, pred_method_sub, pred_method_dec,
            predicted_winner_id, predicted_method,
            actual_winner_id, actual_method,
            is_correct, confidence, is_upset,
            features_json,
            prediction_source, pre_fight_predicted_at
        FROM past_predictions
        ORDER BY fight_id,
                 CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
    )
"""


@router.get(
    "/stats",
    response_model=PastPredictionModalStats,
    summary="Conviction bucket and weight class accuracy breakdown for scorecard modals",
)
def get_past_prediction_stats(
    db: Session = Depends(get_db),
) -> PastPredictionModalStats:
    _BUCKET_CASE = """
        CASE
            WHEN confidence >= 0.65 THEN '30%+'
            WHEN confidence >= 0.60 THEN '20-30%'
            ELSE 'Under 20%'
        END
    """

    # ── All predictions (dedup) ──────────────────────────────────────────────
    all_bucket_rows = db.execute(text(f"""
        WITH best AS (
            SELECT DISTINCT ON (fight_id) confidence, is_correct, weight_class
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT {_BUCKET_CASE} AS bucket,
               COUNT(*) AS fights,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::int AS correct
        FROM best
        WHERE confidence IS NOT NULL AND is_correct IS NOT NULL
        GROUP BY bucket
        ORDER BY MIN(confidence) DESC
    """)).mappings().all()

    _WC_ORDER = """
        CASE weight_class
            WHEN 'Heavyweight'            THEN 1
            WHEN 'Light Heavyweight'      THEN 2
            WHEN 'Middleweight'           THEN 3
            WHEN 'Welterweight'           THEN 4
            WHEN 'Lightweight'            THEN 5
            WHEN 'Featherweight'          THEN 6
            WHEN 'Bantamweight'           THEN 7
            WHEN 'Flyweight'              THEN 8
            WHEN 'Women''s Featherweight' THEN 9
            WHEN 'Women''s Bantamweight'  THEN 10
            WHEN 'Women''s Flyweight'     THEN 11
            WHEN 'Women''s Strawweight'   THEN 12
            ELSE 99
        END ASC
    """

    all_wc_rows = db.execute(text(f"""
        WITH best AS (
            SELECT DISTINCT ON (fight_id) weight_class, is_correct
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT weight_class,
               COUNT(*) AS fights,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::int AS correct
        FROM best
        WHERE weight_class IS NOT NULL AND is_correct IS NOT NULL
        GROUP BY weight_class
        ORDER BY {_WC_ORDER}
    """)).mappings().all()

    # ── Pre-fight only ───────────────────────────────────────────────────────
    pf_bucket_rows = db.execute(text(f"""
        SELECT {_BUCKET_CASE} AS bucket,
               COUNT(*) AS fights,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::int AS correct
        FROM past_predictions
        WHERE prediction_source = 'pre_fight_archive'
          AND confidence IS NOT NULL AND is_correct IS NOT NULL
        GROUP BY bucket
        ORDER BY MIN(confidence) DESC
    """)).mappings().all()

    pf_wc_rows = db.execute(text(f"""
        SELECT weight_class,
               COUNT(*) AS fights,
               SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::int AS correct
        FROM past_predictions
        WHERE prediction_source = 'pre_fight_archive'
          AND weight_class IS NOT NULL AND is_correct IS NOT NULL
        GROUP BY weight_class
        ORDER BY {_WC_ORDER}
    """)).mappings().all()

    # ── Raw rows for Python-computed metrics (calibration, Brier, ROC-AUC) ────
    all_raw = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (fight_id)
                confidence, is_correct, win_prob_a, win_prob_b,
                actual_winner_id, fighter_a_id
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT * FROM best
        WHERE confidence IS NOT NULL AND is_correct IS NOT NULL
          AND win_prob_a IS NOT NULL AND win_prob_b IS NOT NULL
          AND actual_winner_id IS NOT NULL AND fighter_a_id IS NOT NULL
    """)).mappings().all()

    pf_raw = db.execute(text("""
        SELECT confidence, is_correct, win_prob_a, win_prob_b,
               actual_winner_id, fighter_a_id
        FROM past_predictions
        WHERE prediction_source = 'pre_fight_archive'
          AND confidence IS NOT NULL AND is_correct IS NOT NULL
          AND win_prob_a IS NOT NULL AND win_prob_b IS NOT NULL
          AND actual_winner_id IS NOT NULL AND fighter_a_id IS NOT NULL
    """)).mappings().all()

    def _roc_auc(y_true: list, y_score: list) -> float | None:
        n_pos = sum(y_true)
        n_neg = len(y_true) - n_pos
        if n_pos == 0 or n_neg == 0:
            return None
        pairs = sorted(zip(y_score, y_true), key=lambda x: x[0], reverse=True)
        auc = 0.0
        pos_seen = 0
        i = 0
        while i < len(pairs):
            j = i
            while j < len(pairs) and pairs[j][0] == pairs[i][0]:
                j += 1
            group_pos = sum(1 for _, lbl in pairs[i:j] if lbl == 1)
            group_neg = (j - i) - group_pos
            auc += group_neg * pos_seen + 0.5 * group_pos * group_neg
            pos_seen += group_pos
            i = j
        return auc / (n_pos * n_neg)

    def _section_metrics(rows) -> tuple:
        conf_correct, conf_incorrect, brier_vals, y_true, y_score = [], [], [], [], []
        for r in rows:
            is_correct = bool(r["is_correct"])
            conf = float(r["confidence"])
            (conf_correct if is_correct else conf_incorrect).append(conf)
            a_won = str(r["actual_winner_id"]) == str(r["fighter_a_id"])
            y_true.append(1 if a_won else 0)
            y_score.append(float(r["win_prob_a"]))
            brier_vals.append((float(r["win_prob_a"]) - (1.0 if a_won else 0.0)) ** 2)
        avg_correct   = sum(conf_correct)   / len(conf_correct)   if conf_correct   else None
        avg_incorrect = sum(conf_incorrect) / len(conf_incorrect) if conf_incorrect else None
        brier = sum(brier_vals) / len(brier_vals) if brier_vals else None
        auc   = _roc_auc(y_true, y_score)
        bss = (1.0 - brier / 0.25) if brier is not None else None
        return avg_correct, avg_incorrect, brier, bss, auc

    def _buckets(rows: list) -> list[ConfBucket]:
        out = []
        for r in rows:
            f = int(r["fights"])
            c = int(r["correct"])
            out.append(ConfBucket(label=r["bucket"], fights=f, correct=c,
                                  accuracy=c / f if f else 0.0))
        return out

    def _wc(rows: list) -> list[WeightClassStat]:
        out = []
        for r in rows:
            f = int(r["fights"])
            c = int(r["correct"])
            out.append(WeightClassStat(weight_class=r["weight_class"], fights=f, correct=c,
                                       accuracy=c / f if f else 0.0))
        return out

    all_avg_correct, all_avg_incorrect, all_brier, all_bss, all_auc = _section_metrics(all_raw)
    pf_avg_correct,  pf_avg_incorrect,  pf_brier,  pf_bss,  pf_auc  = _section_metrics(pf_raw)

    # ── vs-Vegas comparison ───────────────────────────────────────────────────
    vegas_row = db.execute(text("""
        WITH best AS (
            SELECT DISTINCT ON (fight_id)
                implied_prob_a, win_prob_a, actual_winner_id, fighter_a_id
            FROM past_predictions
            ORDER BY fight_id,
                     CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
        )
        SELECT
            COUNT(*) AS sample_size,
            SUM(CASE WHEN
                (implied_prob_a > 0.5 AND actual_winner_id = fighter_a_id)
                OR (implied_prob_a <= 0.5 AND actual_winner_id != fighter_a_id)
                THEN 1 ELSE 0 END) AS vegas_correct,
            SUM(CASE WHEN
                (win_prob_a >= 0.5 AND actual_winner_id = fighter_a_id)
                OR (win_prob_a < 0.5 AND actual_winner_id != fighter_a_id)
                THEN 1 ELSE 0 END) AS model_correct,
            SUM(CASE WHEN
                (win_prob_a >= 0.5) != (implied_prob_a > 0.5)
                THEN 1 ELSE 0 END) AS disagree_count,
            SUM(CASE WHEN
                (win_prob_a >= 0.5) != (implied_prob_a > 0.5)
                AND ((win_prob_a >= 0.5 AND actual_winner_id = fighter_a_id)
                     OR (win_prob_a < 0.5 AND actual_winner_id != fighter_a_id))
                THEN 1 ELSE 0 END) AS disagree_correct
        FROM best
        WHERE implied_prob_a IS NOT NULL
          AND actual_winner_id IS NOT NULL
    """)).mappings().first()

    vegas_cmp = None
    if vegas_row and int(vegas_row["sample_size"]) > 0:
        n = int(vegas_row["sample_size"])
        vc = int(vegas_row["vegas_correct"])
        mc = int(vegas_row["model_correct"])
        dc = int(vegas_row["disagree_count"])
        dcc = int(vegas_row["disagree_correct"])
        vegas_cmp = VegasComparison(
            sample_size=n,
            vegas_accuracy=vc / n,
            model_accuracy=mc / n,
            disagree_count=dc,
            disagree_accuracy=(dcc / dc) if dc > 0 else None,
        )

    return PastPredictionModalStats(
        all=ModalStatsSection(
            conf_buckets=_buckets(all_bucket_rows),
            weight_classes=_wc(all_wc_rows),
            avg_conf_correct=all_avg_correct,
            avg_conf_incorrect=all_avg_incorrect,
            brier_score=all_brier,
            brier_skill_score=all_bss,
            roc_auc=all_auc,
        ),
        pre_fight=ModalStatsSection(
            conf_buckets=_buckets(pf_bucket_rows),
            weight_classes=_wc(pf_wc_rows),
            avg_conf_correct=pf_avg_correct,
            avg_conf_incorrect=pf_avg_incorrect,
            brier_score=pf_brier,
            brier_skill_score=pf_bss,
            roc_auc=pf_auc,
        ),
        vegas=vegas_cmp,
    )


@router.get(
    "/fights",
    response_model=PastPredictionFightsResponse,
    summary="Search past predictions by fighter name",
)
def search_past_prediction_fights(
    search: str | None = Query(None, description="Fighter name search term (optional)"),
    year: int | None = Query(None, description="Filter by year"),
    prediction_source: str | None = Query(None, description="Filter by prediction_source (e.g. 'pre_fight_archive')"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PastPredictionFightsResponse:
    params: dict = {}
    conditions: list[str] = []

    if search:
        conditions.append(
            "(LOWER(fighter_a_name) LIKE LOWER(:search) OR LOWER(fighter_b_name) LIKE LOWER(:search))"
        )
        params["search"] = f"%{search}%"
    if year:
        conditions.append("EXTRACT(YEAR FROM event_date) = :year")
        params["year"] = year

    if prediction_source:
        # Direct query — pre_fight_archive rows are already 1-per-fight by construction
        params["prediction_source"] = prediction_source
        source_conditions = ["prediction_source = :prediction_source"] + conditions
        where = "WHERE " + " AND ".join(source_conditions)

        total: int = db.execute(text(f"""
            SELECT COUNT(*) FROM past_predictions {where}
        """), params).scalar() or 0

        params["limit"]  = page_size
        params["offset"] = (page - 1) * page_size

        rows = db.execute(text(f"""
            SELECT {_FIGHT_COLS}
            FROM past_predictions
            {where}
            ORDER BY event_date DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()
    else:
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        total = db.execute(text(f"""
            WITH best AS (
                SELECT DISTINCT ON (fight_id) *
                FROM past_predictions
                ORDER BY fight_id,
                         CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
            )
            SELECT COUNT(*) FROM best {where}
        """), params).scalar() or 0

        params["limit"]  = page_size
        params["offset"] = (page - 1) * page_size

        rows = db.execute(text(f"""
            WITH best AS (
                SELECT DISTINCT ON (fight_id)
                    fight_id, event_id, event_name, event_date,
                    fighter_a_id, fighter_b_id, fighter_a_name, fighter_b_name,
                    weight_class, win_prob_a, win_prob_b,
                    pred_method_ko_tko, pred_method_sub, pred_method_dec,
                    predicted_winner_id, predicted_method,
                    actual_winner_id, actual_method,
                    is_correct, confidence, is_upset,
                    prediction_source, pre_fight_predicted_at
                FROM past_predictions
                ORDER BY fight_id,
                         CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
            )
            SELECT best.*
            FROM best
            LEFT JOIN fight_details fd ON fd.id = best.fight_id
            {where}
            ORDER BY best.event_date DESC, COALESCE(fd.position, 999) ASC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

    return PastPredictionFightsResponse(
        data=[PastPredictionItem(**dict(r)) for r in rows],
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/fights/{fight_id}",
    response_model=PastPredictionItem,
    summary="Single past prediction by fight ID",
)
def get_past_prediction_fight(
    fight_id: str,
    db: Session = Depends(get_db),
) -> PastPredictionItem:
    row = db.execute(text(f"""
        SELECT DISTINCT ON (fight_id) {_FIGHT_COLS}
        FROM past_predictions
        WHERE fight_id = :fight_id
        ORDER BY fight_id,
                 CASE WHEN prediction_source = 'pre_fight_archive' THEN 0 ELSE 1 END
    """), {"fight_id": fight_id}).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail=f"No prediction found for fight '{fight_id}'")

    return PastPredictionItem(**dict(row))
