"""api/v1/endpoints/chat.py — Text-to-SQL chat assistant.

Routes:
    POST /chat    Accepts a natural language question, generates SQL via Groq,
                  executes it against the UFC database, and returns a formatted answer.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends
from groq import Groq, RateLimitError
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schema — sent to the LLM as context so it knows the table structure
# ---------------------------------------------------------------------------

SCHEMA = """
You are an expert PostgreSQL assistant for a UFC fight database. Write a single valid PostgreSQL SELECT query answering the user's question.

DATABASE SCHEMA:
event_details      (id VARCHAR, "EVENT" TEXT, date_proper DATE, "LOCATION" TEXT)
fighter_details    (id VARCHAR, "FIRST" TEXT, "LAST" TEXT, "NICKNAME" TEXT)
fight_details      (id VARCHAR, "BOUT" TEXT, event_id VARCHAR, fighter_a_id VARCHAR, fighter_b_id VARCHAR)
fight_results      (id VARCHAR, fight_id VARCHAR, event_id VARCHAR,
                    fighter_id VARCHAR,   -- WINNER FK → fighter_details
                    opponent_id VARCHAR,  -- LOSER  FK → fighter_details
                    "METHOD" TEXT, "ROUND" INTEGER, weight_class TEXT,
                    is_title_fight BOOLEAN, fight_time_seconds INTEGER, total_fight_time_seconds INTEGER)
fighter_tott       (id VARCHAR, fighter_id VARCHAR, height_inches FLOAT, weight_lbs FLOAT,
                    reach_inches FLOAT, "STANCE" TEXT, dob_date DATE)
                    -- STANCE stores only 'Orthodox'/'Southpaw'/'Switch' — NOT fighting style (wrestler/boxer/etc.)
fight_stats        (id VARCHAR, fight_id VARCHAR, fighter_id VARCHAR,
                    "ROUND" TEXT,           -- '1','2','3' OR 'Round 1','Round 2' — format varies
                    sig_str_landed INT, sig_str_attempted INT, sig_str_pct NUMERIC,
                    total_str_landed INT, total_str_attempted INT,
                    td_landed INT, td_attempted INT, td_pct NUMERIC,
                    ctrl_seconds INT, kd_int INT, head_landed INT, body_landed INT, leg_landed INT)
upcoming_events    (id VARCHAR, event_name TEXT, date_proper DATE, location TEXT, is_numbered BOOLEAN)
upcoming_fights    (id VARCHAR, event_id VARCHAR, fighter_a_name TEXT, fighter_b_name TEXT,
                    fighter_a_id VARCHAR, fighter_b_id VARCHAR, weight_class TEXT, is_title_fight BOOLEAN)
upcoming_predictions (id VARCHAR, fight_id VARCHAR,
                    win_prob_a FLOAT, win_prob_b FLOAT,   -- e.g. 0.537 = 53.7%
                    method_ko_tko FLOAT, method_sub FLOAT, method_dec FLOAT,
                    features_json JSONB)  -- (fighter_a)-(fighter_b); POSITIVE=favors a, NEGATIVE=favors b

RULES:
1. Return ONLY raw SQL starting with SELECT or WITH — no markdown, no backticks, no explanation, no prose.
   Any question about a fighter's fights, record, stats, measurements or events is answered with SQL.
2. Default LIMIT 20 unless aggregating (COUNT, SUM, MAX, etc.).
3. Name search - many fighters share a last name (Jones, Pereira, Shevchenko, Nurmagomedov, Silva),
   so a last-name-only search mixes different people's fights together.
   When the question (or the conversation so far) gives a full name, match the full name exactly:
     WHERE fd."FIRST" || ' ' || fd."LAST" ILIKE 'first last'   (the fighter's real first and last name)
   Only when just one name is known, search it alone - never guess a first name:
     WHERE fd."LAST" ILIKE 'pyfer'
   Follow-up questions ("he", "his", "they") refer to the full name used earlier in the conversation.
4. fight_results: ONE row per fight. fighter_id=WINNER, opponent_id=LOSER. Pick the join by what is asked:
   - All of a fighter's fights (fight count, history, opponents, dates):
       JOIN fighter_details fd ON (fr.fighter_id=fd.id OR fr.opponent_id=fd.id)
   - Wins only (how many wins, KO wins, submission wins):
       JOIN fighter_details fd ON fr.fighter_id=fd.id
   - Losses only:
       JOIN fighter_details fd ON fr.opponent_id=fd.id
   COUNT(*) over the all-fights join counts fights, NOT wins.
   Fight count example ("how many UFC fights does X have?"):
     SELECT COUNT(*) FROM fight_results fr
     JOIN fighter_details fd ON (fr.fighter_id=fd.id OR fr.opponent_id=fd.id)
     WHERE fd."FIRST" || ' ' || fd."LAST" ILIKE 'first last'
   Win count example ("how many fights has X won?"):
     SELECT COUNT(*) FROM fight_results fr
     JOIN fighter_details fd ON fr.fighter_id=fd.id
     WHERE fd."FIRST" || ' ' || fd."LAST" ILIKE 'first last' AND fr."METHOD" NOT ILIKE '%no contest%'
5. Fighter W-L record: both counts in one query.
   Exclude NCs: AND fr."METHOD" NOT ILIKE '%no contest%'
   Record example ("what is X's record?"):
     SELECT SUM(CASE WHEN fr.fighter_id=fd.id THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN fr.opponent_id=fd.id THEN 1 ELSE 0 END) AS losses
     FROM fight_results fr
     JOIN fighter_details fd ON (fr.fighter_id=fd.id OR fr.opponent_id=fd.id)
     WHERE fd."FIRST" || ' ' || fd."LAST" ILIKE 'first last' AND fr."METHOD" NOT ILIKE '%no contest%'
6. fight_stats totals: ALWAYS include WHERE fs."ROUND" NOT ILIKE '%total%' — fight_stats has per-round rows
   AND a duplicate "Totals" row per fight; omitting this filter double-counts every stat.
   ROUND format varies ('1' or 'Round 1') — never filter by exact format or regex.
   fight_stats has its own fighter_id — use fs.fighter_id=fd.id directly, never the fight_results OR join.
7. Ratio calculations: CAST(SUM(x) AS FLOAT) / NULLIF(SUM(y), 0)
   Always add NULLS LAST when ordering by a computed or aggregated column DESC — PostgreSQL sorts NULLs first otherwise.
   Accuracy/rate queries MUST add a minimum sample size to exclude statistical noise from fighters with few attempts:
   HAVING SUM(fs.sig_str_attempted) >= 100  -- for striking accuracy
   HAVING SUM(fs.td_attempted) >= 20         -- for takedown accuracy
   HAVING COUNT(DISTINCT fs.fight_id) >= 5   -- for per-fight averages
8. fight_stats mainly covers 2015+. Older fights may have no stats rows.
   When aggregating stats BY weight_class (e.g. finish rates, averages), filter to current
   UFC weight classes to exclude historical non-divisions like 'Open Weight'/'Super Heavyweight':
   WHERE fr.weight_class IN ('Heavyweight','Light Heavyweight','Middleweight','Welterweight',
     'Lightweight','Featherweight','Bantamweight','Flyweight','Strawweight',
     'Women''s Strawweight','Women''s Flyweight','Women''s Bantamweight','Women''s Featherweight')
9. Always qualify ALL column names with table alias.
10. UPCOMING vs HISTORICAL: event_details has ONLY past events — never query for future dates.
    For "next card"/"upcoming"/"this weekend"/"scheduled" use upcoming_events/upcoming_fights.
    upcoming_events may have stale entries — ALWAYS filter WHERE date_proper >= CURRENT_DATE.
    Next event subquery: ue.date_proper = (SELECT MIN(date_proper) FROM upcoming_events WHERE date_proper >= CURRENT_DATE)
10b. Event names include a subtitle: "UFC 300: Pereira vs. Hill", "UFC Fight Night: Allen vs. Duncan".
    Numbered event: WHERE ed."EVENT" ILIKE 'UFC 300:%'  (the colon keeps UFC 30 from matching UFC 300)
11. Chronological ordering: ALWAYS use date_proper (DATE). Never use id columns for ordering.
    NEVER order by fight_time_seconds or total_fight_time_seconds for recency — those are fight durations, not dates.
    fight_results has NO date column — dates are ONLY on event_details.date_proper.
    Any "most recent" query must JOIN event_details and ORDER BY ed.date_proper DESC.
12. Win probability questions — choose based on scope:
    a) CARD OVERVIEW ("next card", "this weekend's picks", "model favorites on Saturday"):
       omit features_json, LIMIT 6, ORDER BY is_title_fight DESC
      SELECT uf.fighter_a_name, uf.fighter_b_name, uf.weight_class, uf.is_title_fight,
             up.win_prob_a, up.win_prob_b, up.method_ko_tko, up.method_sub, up.method_dec
      FROM upcoming_predictions up
      JOIN upcoming_fights uf ON uf.id=up.fight_id
      JOIN upcoming_events ue ON ue.id=uf.event_id
      WHERE ue.date_proper >= CURRENT_DATE
        AND ue.date_proper = (SELECT MIN(date_proper) FROM upcoming_events WHERE date_proper >= CURRENT_DATE)
      ORDER BY uf.is_title_fight DESC LIMIT 6
    b) SPECIFIC FIGHT ("chances X beats Y", "model on [fighter] vs [fighter]"):
       include features_json
      SELECT uf.fighter_a_name, uf.fighter_b_name, up.win_prob_a, up.win_prob_b,
             up.method_ko_tko, up.method_sub, up.method_dec, up.features_json
      FROM upcoming_predictions up JOIN upcoming_fights uf ON uf.id=up.fight_id
      WHERE (uf.fighter_a_name ILIKE '%x%' OR uf.fighter_b_name ILIKE '%x%')
        AND (uf.fighter_a_name ILIKE '%y%' OR uf.fighter_b_name ILIKE '%y%') LIMIT 1
    features_json keys (all = fighter_a minus fighter_b; REVERSED means negative favors fighter_a):
      reach_diff_inches, diff_age_at_fight (REVERSED=younger better), win_streak_diff,
      loss_streak_diff (REVERSED=shorter better), diff_ko_rate, diff_decision_rate,
      diff_career_avg_kd, diff_ewa_kd, diff_aggression_score, diff_defense_score,
      diff_sapm (REVERSED=absorbs less better), diff_roll3_sig_str_landed, diff_roll7_sig_str_att,
      diff_roll7_sig_str_pct, diff_roll7_total_str_landed, diff_roll3_ctrl_s, diff_roll5_td_pct,
      diff_roll7_td_landed, diff_career_avg_ctrl_s, diff_career_avg_td_attempted,
      diff_grappling_ratio, diff_career_length_days, diff_avg_opponent_losses

TERMINOLOGY:
Weight classes (exact strings for WHERE clauses):
  HW=Heavyweight, LHW=Light Heavyweight, MW=Middleweight, WW=Welterweight,
  LW=Lightweight, FW=Featherweight, BW=Bantamweight, FLW=Flyweight, SW=Strawweight
  Women's divisions: "Women's Strawweight/Flyweight/Bantamweight/Featherweight"
Methods: KO/TKO → 'KO/TKO'; sub/submission/choke/armbar/triangle/guillotine/RNC/heel hook/kimura → 'Submission';
  decision/unanimous/split/majority → ILIKE '%Decision%'; DQ → 'DQ'; NC → 'No Contest'
Stats: TD=takedown (td_landed/td_attempted), sig str=sig_str_landed, ctrl=ctrl_seconds,
  KD=kd_int, head/body/leg=head_landed/body_landed/leg_landed, accuracy=sig_str_pct/td_pct

Nicknames → real names (search the full name; one per line):
  Eagle/Khabib → Khabib Nurmagomedov
  Bones → Jon Jones
  DC → Daniel Cormier
  GSP/Rush → Georges St-Pierre
  Izzy/Stylebender → Israel Adesanya
  Poatan → Alex Pereira
  DJ/Mighty Mouse → Demetrious Johnson
  Korean Zombie → Chan Sung Jung
  Jacare → Ronaldo Souza
  Shogun → Mauricio Rua
  Rampage → Quinton Jackson
  Do Bronx → Charles Oliveira
  RDA → Rafael Dos Anjos
  JDS → Junior Dos Santos
  Baddy/Pyfer → Joe Pyfer (FIRST=Joe LAST=Pyfer — never guess a different first name)
  Moicano → Renato Moicano
  Volk → Alexander Volkanovski
  Chito → Marlon Vera
  Makhachev → Islam Makhachev
  Topuria → Ilia Topuria
  Ankalaev → Magomed Ankalaev
  Tsarukyan/Arman → Arman Tsarukyan
  Dvalishvili/Merab → Merab Dvalishvili
  Du Plessis/DDP → Dricus Du Plessis
  Prochazka/Jiri → Jiri Prochazka
  Fiziev → Rafael Fiziev
  Pantoja → Alexandre Pantoja
  Borz → Khamzat Chimaev

FINAL RULE — output exactly NO_SQL (nothing else) ONLY for:
- Clearly hypothetical questions: explicit fantasy matchups ("who would win a trilogy",
  "if X fought Y someday"), pure opinion with no factual DB answer ("who has better technique"),
  or questions about fighting style/approach (wrestler, boxer, grappler, striker, kickboxer, etc.)
  since MMA style is not stored in any table — STANCE is Orthodox/Southpaw only.
- Current champion questions ("who is the X champion", "who holds the X belt", "current X champ"):
  the database may contain non-UFC events with mislabeled title fights, making champion lookups
  unreliable. Use NO_SQL so general knowledge can answer accurately instead.
NEVER NO_SQL for counts or stats about real fights - knockdowns, strikes, takedowns, control time,
records, finishes, heights, reaches and dates are all stored; write SQL for them.
When in doubt, write SQL.
"""

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    answer: str
    sql: str | None = None
    status: str        # "ok" | "rate_limited" | "no_results" | "error"
    source: str | None = None  # "model_data" | "general_knowledge"
    retry_after: int | None = None  # seconds to wait before retrying

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM SQL output."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:sql)?", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return raw


def _rows_to_text(rows: list[dict[str, Any]]) -> str:
    """Convert DB rows to a compact text block for the LLM."""
    if not rows:
        return "(no rows)"
    lines = []
    for row in rows[:20]:
        lines.append(", ".join(f"{k}: {v}" for k, v in row.items()))
    return "\n".join(lines)


# Groq retired llama-3.3-70b-versatile; every chat call returned 404 until
# 2026-10-10. gpt-oss-120b is a reasoning model: its hidden reasoning tokens
# count against max_completion_tokens, so the budgets below cover reasoning plus
# the visible answer. Low effort keeps reasoning short - SQL here is templated
# by the schema prompt, not puzzled out. Measured by backend/scripts/eval_chat.py.
CHAT_MODEL = "openai/gpt-oss-120b"
REASONING_EFFORT = "low"
SQL_TOKEN_BUDGET = 2048
ANSWER_TOKEN_BUDGET = 1536


def _complete(client: Groq, messages: list[dict], temperature: float, budget: int):
    return client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=budget,
        reasoning_effort=REASONING_EFFORT,
    )


def _get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.groq_api_key, max_retries=0)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse, summary="UFC chat assistant")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        client = _get_groq_client()
    except RuntimeError as e:
        return ChatResponse(answer=str(e), status="error")

    # ── Step 1: Generate SQL ────────────────────────────────────────────────
    # Only send last 4 history turns to keep context window small
    history_turns = request.history[-4:] if request.history else []
    messages: list[dict] = [{"role": "system", "content": SCHEMA}]
    for turn in history_turns:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": f"Question: {request.question}\nSQL:"})

    try:
        # gpt-oss occasionally returns an empty completion; one retry recovers it.
        for _ in range(2):
            sql_resp = _complete(client, messages, temperature=0,   # deterministic SQL generation
                                 budget=SQL_TOKEN_BUDGET)
            sql = _clean_sql(sql_resp.choices[0].message.content or "")
            if sql:
                break
    except RateLimitError as e:
        retry_after = 60
        try:
            retry_after = int(e.response.headers.get("retry-after", 60))
        except (AttributeError, ValueError, TypeError):
            pass
        wait_msg = f"{retry_after // 60} min" if retry_after >= 60 else f"{retry_after}s"
        return ChatResponse(
            answer=f"Rate limit reached — please try again in {wait_msg}.",
            status="rate_limited",
            retry_after=retry_after,
        )
    except Exception as e:
        logger.error("SQL generation failed: %s", e)
        return ChatResponse(answer="Failed to generate a query for your question.", status="error")

    if not sql:
        logger.warning("Model returned empty SQL for question: %s", request.question)
        return ChatResponse(answer="I couldn't generate a query for that question. Try rephrasing it.", status="error")

    # ── NO_SQL path: hypothetical / general knowledge ───────────────────────
    if sql.strip().upper() == "NO_SQL":
        logger.info("Model signalled NO_SQL — answering from general knowledge")
        freeform_messages: list[dict] = [
            {"role": "system", "content": (
                "You are a knowledgeable UFC analyst. Answer the user's question using your general MMA knowledge. "
                "Be concise (2-4 sentences). If asked about a hypothetical matchup, give a thoughtful analysis "
                "based on fighting styles and known history. "
                "Do not invent specific statistics you cannot verify. "
                "Do not mention databases, SQL, or prediction models. "
                "Do not use gendered pronouns (he/she/him/her/his/hers) — refer to fighters by name only."
            )},
        ]
        for turn in history_turns:
            freeform_messages.append({"role": turn.role, "content": turn.content})
        freeform_messages.append({"role": "user", "content": request.question})
        try:
            freeform_resp = _complete(client, freeform_messages, temperature=0.5,
                                      budget=ANSWER_TOKEN_BUDGET)
            answer = freeform_resp.choices[0].message.content.strip()
            return ChatResponse(answer=answer, sql=None, status="ok", source="general_knowledge")
        except RateLimitError as e:
            retry_after = 60
            try:
                retry_after = int(e.response.headers.get("retry-after", 60))
            except (AttributeError, ValueError, TypeError):
                pass
            wait_msg = f"{retry_after // 60} min" if retry_after >= 60 else f"{retry_after}s"
            return ChatResponse(
                answer=f"Rate limit reached — please try again in {wait_msg}.",
                status="rate_limited",
                retry_after=retry_after,
            )
        except Exception as e:
            logger.error("Free-form answer failed: %s", e)
            return ChatResponse(answer="I couldn't answer that question right now.", status="error")

    if not re.match(r"(select|with)\b", sql, re.IGNORECASE):
        logger.warning("Model returned non-SQL for question %r: %s", request.question, sql[:200])
        return ChatResponse(answer="I couldn't generate a query for that question. Try rephrasing it.", status="error")

    logger.info("Generated SQL: %s", sql)

    # ── Step 2: Execute SQL ─────────────────────────────────────────────────
    # The SQL is written by a model from user text, so it runs read-only and
    # time-boxed: a prompt that talks the model into DELETE, UPDATE or DROP
    # fails here, as does a query that would tie up the database.
    try:
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(text("SET LOCAL statement_timeout = '5s'"))
        rows = db.execute(text(sql)).mappings().all()
        rows = [dict(r) for r in rows]
    except Exception as e:
        logger.warning("SQL execution failed: %s | SQL: %s", e, sql)
        return ChatResponse(
            answer="I couldn't find an answer to that question. Try rephrasing it.",
            sql=sql,
            status="error",
        )

    if not rows:
        return ChatResponse(
            answer="No results found for that question.",
            sql=sql,
            status="no_results",
        )

    # ── Step 3: Format answer ───────────────────────────────────────────────
    has_features = any('features_json' in row and row['features_json'] for row in rows)
    is_card_overview = (
        len(rows) > 1
        and 'win_prob_a' in rows[0]
        and not has_features
    )

    if has_features:
        format_prompt = (
            f"The user asked: {request.question}\n\n"
            f"Database results:\n{_rows_to_text(rows)}\n\n"
            "The results include win probabilities and a features_json dict of model feature differentials.\n"
            "Each feature value = (fighter_a stat) - (fighter_b stat).\n"
            "POSITIVE = favors fighter_a. NEGATIVE = favors fighter_b.\n"
            "EXCEPTIONS where NEGATIVE favors fighter_a: diff_age_at_fight (younger is better), "
            "diff_sapm (fewer strikes absorbed is better), loss_streak_diff (shorter loss streak is better).\n\n"
            "Write a response that:\n"
            "1. States each fighter's win probability as a percentage\n"
            "2. States the most likely method (KO/TKO, submission, or decision)\n"
            "3. Lists the 3-4 most significant features that favor the predicted winner, "
            "with specific numbers and a plain-English explanation of why each matters\n"
            "4. Lists 2 features that favor the other fighter for balance\n"
            "5. One sentence concluding why the model leans the way it does\n"
            "Use fighter names throughout (not 'fighter_a'/'fighter_b'). "
            "Be specific with numbers. Do not mention SQL, databases, or feature names literally. "
            "Do not use gendered pronouns (he/she/him/her/his/hers) — refer to fighters by name only."
        )
    elif is_card_overview:
        format_prompt = (
            f"The user asked: {request.question}\n\n"
            f"Database results:\n{_rows_to_text(rows)}\n\n"
            "Write a fight card preview. For each fight, one line:\n"
            "'Fighter A vs Fighter B — [favored fighter] favored at X% (most likely: METHOD)'\n"
            "List title fights first. Use fighter names only (not 'fighter_a'/'fighter_b'). "
            "Do not mention SQL or databases. Keep it concise. "
            "Do not use gendered pronouns (he/she/him/her/his/hers) — refer to fighters by name only."
        )
    else:
        format_prompt = (
            f"The user asked: {request.question}\n\n"
            f"Database results:\n{_rows_to_text(rows)}\n\n"
            "Write a clear, concise answer in 1-3 sentences. "
            "Include specific names, numbers, and fight details from the results. "
            "Use only facts that appear in the results - do not add opponents, dates or details "
            "from memory. "
            "Do not mention SQL or databases. "
            "Do not use gendered pronouns (he/she/him/her/his/hers) — refer to fighters by name only."
        )

    def _card_fallback(rows: list[dict]) -> str:
        """Clean fallback for card overview when LLM formatting fails."""
        lines = []
        for row in rows:
            a = row.get('fighter_a_name', '')
            b = row.get('fighter_b_name', '')
            prob_a = row.get('win_prob_a')
            prob_b = row.get('win_prob_b')
            if a and b and prob_a is not None:
                pct_a = round(float(prob_a) * 100, 1)
                pct_b = round(float(prob_b) * 100, 1) if prob_b is not None else round(100 - pct_a, 1)
                favored, pct = (a, pct_a) if pct_a >= pct_b else (b, pct_b)
                lines.append(f"{a} vs {b} — {favored} favored at {pct}%")
        return "\n".join(lines) if lines else _rows_to_text(rows)

    try:
        answer_resp = _complete(client, [{"role": "user", "content": format_prompt}],
                                temperature=0.3, budget=ANSWER_TOKEN_BUDGET)
        answer = answer_resp.choices[0].message.content.strip()
    except RateLimitError as e:
        retry_after = 60
        try:
            retry_after = int(e.response.headers.get("retry-after", 60))
        except (AttributeError, ValueError, TypeError):
            pass
        if is_card_overview:
            answer = _card_fallback(rows)
        else:
            return ChatResponse(
                answer=f"Rate limit reached — please try again in {retry_after // 60} min." if retry_after >= 60 else f"Rate limit reached — please try again in {retry_after}s.",
                status="rate_limited",
                retry_after=retry_after,
            )
    except Exception as e:
        logger.error("Answer formatting failed: %s", e)
        answer = _card_fallback(rows) if is_card_overview else _rows_to_text(rows)

    return ChatResponse(answer=answer, sql=sql, status="ok", source="model_data")
