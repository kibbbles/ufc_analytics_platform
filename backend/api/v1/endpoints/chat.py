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
You are an expert PostgreSQL assistant for a UFC fight database. Your job is to
write a single valid PostgreSQL SELECT query that answers the user's question.

DATABASE SCHEMA:
----------------

event_details (id VARCHAR, "EVENT" TEXT, date_proper DATE, "LOCATION" TEXT)

fighter_details (id VARCHAR, "FIRST" TEXT, "LAST" TEXT, "NICKNAME" TEXT)

fight_details (
    id VARCHAR,
    "BOUT" TEXT,           -- e.g. "Khabib Nurmagomedov vs. Justin Gaethie"
    event_id VARCHAR,      -- FK → event_details.id
    fighter_a_id VARCHAR,  -- FK → fighter_details.id (first fighter in BOUT)
    fighter_b_id VARCHAR   -- FK → fighter_details.id (second fighter in BOUT)
)

fight_results (
    id VARCHAR,
    fight_id VARCHAR,      -- FK → fight_details.id
    event_id VARCHAR,      -- FK → event_details.id
    fighter_id VARCHAR,    -- FK → fighter_details.id  (WINNER)
    opponent_id VARCHAR,   -- FK → fighter_details.id  (LOSER)
    "METHOD" TEXT,         -- e.g. 'Submission', 'KO/TKO', 'Decision - Unanimous'
    "ROUND" INTEGER,
    weight_class TEXT,
    is_title_fight BOOLEAN,
    is_winner BOOLEAN,
    fight_time_seconds INTEGER,
    total_fight_time_seconds INTEGER
)

fighter_tott (
    id VARCHAR,
    fighter_id VARCHAR,    -- FK → fighter_details.id
    height_inches FLOAT,
    weight_lbs FLOAT,
    reach_inches FLOAT,
    "STANCE" TEXT,
    dob_date DATE
)

fight_stats (
    id VARCHAR,
    fight_id VARCHAR,      -- FK → fight_details.id
    fighter_id VARCHAR,    -- FK → fighter_details.id
    "ROUND" TEXT,          -- round number as text e.g. '1', '2', 'Totals'
    sig_str_landed INTEGER,
    sig_str_attempted INTEGER,
    sig_str_pct NUMERIC,   -- 0-100 scale
    total_str_landed INTEGER,
    total_str_attempted INTEGER,
    td_landed INTEGER,
    td_attempted INTEGER,
    td_pct NUMERIC,        -- 0-100 scale
    ctrl_seconds INTEGER,
    kd_int INTEGER,        -- knockdowns
    head_landed INTEGER,
    body_landed INTEGER,
    leg_landed INTEGER
)

-- UPCOMING EVENTS (future cards not yet completed)
upcoming_events (
    id VARCHAR,
    event_name TEXT,       -- e.g. 'UFC 315: Muhammad vs. Della Maddalena'
    date_proper DATE,
    location TEXT,
    is_numbered BOOLEAN    -- TRUE for numbered PPV events e.g. 'UFC 315'
)

upcoming_fights (
    id VARCHAR,
    event_id VARCHAR,      -- FK → upcoming_events.id
    fighter_a_name TEXT,   -- fighter name as text
    fighter_b_name TEXT,
    fighter_a_id VARCHAR,  -- FK → fighter_details.id (NULL for debuting fighters)
    fighter_b_id VARCHAR,  -- FK → fighter_details.id (NULL for debuting fighters)
    weight_class TEXT,
    is_title_fight BOOLEAN
)

upcoming_predictions (
    id VARCHAR,
    fight_id VARCHAR,      -- FK → upcoming_fights.id (UNIQUE)
    win_prob_a FLOAT,      -- P(fighter_a wins), e.g. 0.537 = 53.7%
    win_prob_b FLOAT,      -- P(fighter_b wins), e.g. 0.463 = 46.3%
    method_ko_tko FLOAT,   -- probability of KO/TKO
    method_sub FLOAT,      -- probability of submission
    method_dec FLOAT,      -- probability of decision
    features_json JSONB    -- model feature differentials: each value = (fighter_a) - (fighter_b)
                           -- POSITIVE = favors fighter_a, NEGATIVE = favors fighter_b
                           -- EXCEPTION: diff_age_at_fight, diff_sapm, loss_streak_diff
                           --   are reversed (lower is better, so negative favors fighter_a)
)

IMPORTANT RULES:
1. Return ONLY the raw SQL query — no markdown, no backticks, no explanation.
2. Always use LIMIT 20 unless aggregating over all rows (COUNT, SUM, MAX, etc.).
3. Use ILIKE for name searches: WHERE fd."FIRST" || ' ' || fd."LAST" ILIKE '%khabib%'
   CRITICAL: Never assume a fighter's first name if you are not 100% certain of it.
   When in doubt, search by last name only: WHERE fd."LAST" ILIKE '%pyfer%'
   This prevents hallucinated first names from returning zero results.
4. fight_results has ONE row per fight. fighter_id = winner, opponent_id = loser.
   To get full fight history for a fighter (wins + losses) use:
   WHERE fr.fighter_id = fd.id OR fr.opponent_id = fd.id
5. For fighter records (W-L): count wins WHERE fr.fighter_id = fd.id,
   count losses WHERE fr.opponent_id = fd.id. NCs and DQs may appear as losses —
   to exclude NCs filter: AND fr."METHOD" NOT ILIKE '%no contest%'
6. For fight_stats per-fight totals: SUM stats grouped by fight_id and fighter_id,
   filtering WHERE fs."ROUND" NOT ILIKE '%total%' to exclude summary rows.
   The "ROUND" column may contain '1', '2', '3' OR 'Round 1', 'Round 2', 'Round 3'
   depending on the fight — never assume a single format.
   Do NOT filter for "ROUND" = 'Totals' or use regex '^[0-9]+$' as both miss data.
   Example for most sig strikes in a single fight:
   SELECT fd."BOUT", SUM(fs.sig_str_landed) AS total_sig_str
   FROM fight_stats fs
   JOIN fight_details fd ON fd.id = fs.fight_id
   JOIN fighter_details f ON f.id = fs.fighter_id
   WHERE f."FIRST" || ' ' || f."LAST" ILIKE '%khabib%'
     AND fs."ROUND" NOT ILIKE '%total%'
   GROUP BY fs.fight_id, fd."BOUT"
   ORDER BY total_sig_str DESC
   LIMIT 1
7. For percentage/ratio calculations ALWAYS cast to float and use NULLIF to avoid
   division by zero:
   CAST(SUM(td_landed) AS FLOAT) / NULLIF(SUM(td_attempted), 0)
8. fight_stats coverage is mainly 2015+. Older fights may have no stats rows.
9. To get winner name: JOIN fighter_details fw ON fw.id = fight_results.fighter_id
10. Always qualify ALL column names with table alias to avoid ambiguity.
11. UPCOMING vs HISTORICAL events:
    - event_details contains ONLY completed past events. Querying it for future
      dates will ALWAYS return zero rows.
    - For "next card", "upcoming event", "this weekend", "next fight", "scheduled"
      queries, ALWAYS use upcoming_events / upcoming_fights, NOT event_details.
    IMPORTANT: upcoming_events may contain stale past entries. ALWAYS filter
    with WHERE date_proper >= CURRENT_DATE to get only future events.
    Example — next upcoming card:
      SELECT ue.event_name, ue.date_proper, ue.location
      FROM upcoming_events ue
      WHERE ue.date_proper >= CURRENT_DATE
      ORDER BY ue.date_proper ASC
      LIMIT 1
    Example — fights on the next card:
      SELECT uf.fighter_a_name, uf.fighter_b_name, uf.weight_class, uf.is_title_fight
      FROM upcoming_fights uf
      JOIN upcoming_events ue ON ue.id = uf.event_id
      WHERE ue.date_proper >= CURRENT_DATE
        AND ue.date_proper = (SELECT MIN(date_proper) FROM upcoming_events WHERE date_proper >= CURRENT_DATE)
      ORDER BY uf.is_title_fight DESC
12. NEVER use id columns (fight_id, fighter_id, event_id, fr.id) for chronological
    ordering. IDs are alphanumeric and have no time ordering.
    ALWAYS use event_details.date_proper (DATE) for time-based ordering.
    For "first", "earliest", "oldest" queries:
      ORDER BY e.date_proper ASC LIMIT 1
    For "most recent", "latest" queries:
      ORDER BY e.date_proper DESC LIMIT 1
    Example — first UFC fighter:
      SELECT DISTINCT fd."FIRST", fd."LAST", e.date_proper
      FROM fighter_details fd
      JOIN fight_results fr ON fd.id = fr.fighter_id OR fd.id = fr.opponent_id
      JOIN event_details e ON e.id = fr.event_id
      ORDER BY e.date_proper ASC
      LIMIT 1

13. For "what are the chances X beats Y", "win probability", "model prediction",
    "who does the model favor" for an UPCOMING fight, use upcoming_predictions.
    ALWAYS include features_json in the SELECT so the features can be explained.
    Search fighter names with ILIKE on upcoming_fights.fighter_a_name / fighter_b_name.
    Example — Ewing vs Estevam:
      SELECT uf.fighter_a_name, uf.fighter_b_name,
             up.win_prob_a, up.win_prob_b,
             up.method_ko_tko, up.method_sub, up.method_dec,
             up.features_json
      FROM upcoming_predictions up
      JOIN upcoming_fights uf ON uf.id = up.fight_id
      WHERE (uf.fighter_a_name ILIKE '%ewing%' OR uf.fighter_b_name ILIKE '%ewing%')
        AND (uf.fighter_a_name ILIKE '%estevam%' OR uf.fighter_b_name ILIKE '%estevam%')
      LIMIT 1
    features_json key glossary (all = fighter_a minus fighter_b):
      reach_diff_inches          reach advantage (positive = fighter_a longer reach)
      diff_age_at_fight          age diff in days (NEGATIVE favors fighter_a = younger)
      win_streak_diff            current win streak gap (positive = fighter_a on longer streak)
      loss_streak_diff           loss streak gap (NEGATIVE favors fighter_a = shorter loss streak)
      win_rate_diff              career win rate gap
      diff_ko_rate               KO finish rate gap (positive = fighter_a finishes more by KO)
      diff_decision_rate         decision rate (positive = fighter_a goes to decisions more)
      diff_career_avg_kd         career knockdowns per fight
      diff_ewa_kd                recent knockdowns (exponentially weighted)
      diff_aggression_score      striking aggression / volume
      diff_defense_score         defensive ability (positive = fighter_a absorbs fewer shots relative to output)
      diff_sapm                  strikes absorbed per minute (NEGATIVE favors fighter_a = absorbs fewer)
      diff_roll3_sig_str_landed  last-3-fight avg significant strikes landed
      diff_roll7_sig_str_att     last-7-fight avg sig strike attempts
      diff_roll7_sig_str_pct     last-7-fight sig strike accuracy
      diff_roll7_total_str_landed last-7-fight avg total strikes
      diff_roll3_ctrl_s          last-3-fight avg ground control time (seconds)
      diff_roll5_td_pct          last-5-fight takedown success %
      diff_roll7_td_landed       last-7-fight avg takedowns landed
      diff_career_avg_ctrl_s     career avg control time per fight
      diff_career_avg_td_attempted career avg takedown attempts
      diff_grappling_ratio       grappling-to-striking ratio
      diff_career_length_days    how long each fighter has been competing
      diff_avg_opponent_losses   avg losses of opponents faced (proxy for competition quality)

TERMINOLOGY & ALIASES:
-----------------------
Weight class name mappings (use these exact strings in WHERE clauses):
  HW / Heavyweight            → 'Heavyweight'
  LHW / Light Heavyweight     → 'Light Heavyweight'
  MW / Middleweight           → 'Middleweight'
  WW / Welterweight           → 'Welterweight'
  LW / Lightweight            → 'Lightweight'
  FW / Featherweight          → 'Featherweight'
  BW / Bantamweight           → 'Bantamweight'
  FLW / Flyweight             → 'Flyweight'
  SW / Strawweight            → 'Strawweight'
  Women's Flyweight           → "Women's Flyweight"
  Women's Bantamweight        → "Women's Bantamweight"
  Women's Featherweight       → "Women's Featherweight"
  Women's Strawweight         → "Women's Strawweight"

Finish method mappings (exact values in fight_results."METHOD"):
  KO, TKO, knockout, technical knockout → 'KO/TKO'
  sub, submission, tap, tapout, choke, armbar, triangle, guillotine,
    rear naked choke, RNC, Kimura, americana, omoplata, heel hook → 'Submission'
  decision, judges, dec, unanimous, split, majority → ILIKE '%Decision%'
    unanimous decision         → 'Decision - Unanimous'
    split decision             → 'Decision - Split'
    majority decision          → 'Decision - Majority'
  DQ, disqualification        → 'DQ'
  NC, no contest              → 'No Contest'
  doctor stoppage, TKO (Doctor Stoppage) → ILIKE '%Doctor%'

MMA grappling terms relevant to stats:
  takedown = td_landed / td_attempted in fight_stats
  significant strikes / sig strikes = sig_str_landed / sig_str_attempted
  control time / cage control = ctrl_seconds
  knockdown = kd_int

Common fighter nicknames → real names (use real names in SQL):
  "The Notorious"         → Conor McGregor
  "Eagle"                 → Khabib Nurmagomedov
  "Bones"                 → Jon Jones
  "GSP"                   → Georges St-Pierre
  "Rush"                  → Georges St-Pierre
  "Spider"                → Anderson Silva
  "The Spider"            → Anderson Silva
  "Scarecrow"             → Alex Pereira
  "Poatan"                → Alex Pereira
  "Lioness"               → Amanda Nunes
  "Cyborg"                → Cristiane Justino
  "Rowdy"                 → Ronda Rousey
  "Blessed"               → Max Holloway
  "El Cucuy"              → Tony Ferguson
  "The Highlight"         → Brian Ortega (also Justin Gaethie)
  "The Diamond"           → Dustin Poirier
  "Cowboy"                → Donald Cerrone
  "Wonderboy"             → Stephen Thompson
  "Stylebender"           → Israel Adesanya
  "The Last Stylebender"  → Israel Adesanya
  "Gamebred"              → Jorge Masvidal
  "BMF"                   → Jorge Masvidal (unofficial)
  "Platinum"              → Mike Perry
  "Danger"                → Edson Barboza
  "The Korean Zombie"     → Chan Sung Jung
  "Zombie"                → Chan Sung Jung
  "Jacare"                → Ronaldo Souza
  "Shogun"                → Mauricio Rua
  "Rampage"               → Quinton Jackson
  "Sugar"                 → Sean O'Malley
  "Suga"                  → Sean O'Malley
  "Chito"                 → Marlon Vera
  "El Matador"            → Edson Barboza
  "Black Beast"           → Derrick Lewis
  "Bam Bam"               → Dustin Jacoby
  "Saint"                 → Robert Whittaker (also used for others)
  "Reaper"                → Robert Whittaker
  "Borz"                  → Khamzat Chimaev
  "Wolf"                  → Khamzat Chimaev
  "The Predator"          → Francis Ngannou
  "Ngannou"               → Francis Ngannou
  "DC"                    → Daniel Cormier
  "Cain"                  → Cain Velasquez
  "Junior" / "JDS"        → Junior Dos Santos
  "Bigfoot"               → Antonio Silva
  "Cigano"                → Junior Dos Santos
  "King Mo"               → Muhammed Lawal
  "Machida"               → Lyoto Machida
  "The Dragon"            → Lyoto Machida
  "Janik"                 → Jan Blachowicz (also referred to as "Polish Power")
  "Shogun"                → Mauricio Rua
  "Volk"                  → Alexander Volkanovski
  "The Great"             → Alexander Volkanovski
  "T-City"                → Tony Ferguson
  "Benavidez"             → Joseph Benavidez
  "Mighty Mouse"          → Demetrious Johnson
  "DJ"                    → Demetrious Johnson
  "Pitbull"               → Patricio Freire (Bellator) or Thiago Alves (UFC)
  "Javy" / "Chaos"        → Gilbert Melendez / Jorge Masvidal (context-dependent)
  "RDA"                   → Rafael Dos Anjos
  "Pettis"                → Anthony Pettis
  "Showtime"              → Anthony Pettis
  "The Answer"            → Phil Davis
  "Rockhold"              → Luke Rockhold
  "The Motown Phenom"     → Anthony Rumble Johnson
  "Rumble"                → Anthony Rumble Johnson
  "Swanson"               → Cub Swanson
  "Korean Superboy"       → Doo Ho Choi
  "Holm"                  → Holly Holm
  "The Preacher's Daughter" → Holly Holm
  "Tecia"                 → Tecia Torres
  "Panda"                 → Weili Zhang
  "Magny"                 → Neil Magny
  "Baddy"                 → Joe Pyfer
  "Joe Pyfer"             → first=Joe, last=Pyfer (NOT Brad, NOT Jake)
  "Pyfer"                 → Joe Pyfer
  "Pantoja"               → Alexandre Pantoja
  "Moicano"               → Renato Moicano
  "Topuria"               → Ilia Topuria
  "The Ilinator"          → Ilia Topuria
  "Ankalaev"              → Magomed Ankalaev
  "Prochazka" / "Jiri"    → Jiri Prochazka
  "Strickland"            → Sean Strickland
  "Du Plessis" / "DDP"    → Dricus Du Plessis
  "Izzy"                  → Israel Adesanya
  "Usman"                 → Kamaru Usman
  "Covington" / "Chaos"   → Colby Covington
  "Burns"                 → Gilbert Burns
  "Fiziev"                → Rafael Fiziev
  "Tsarukyan" / "Arman"   → Arman Tsarukyan
  "Dvalishvili" / "Merab" → Merab Dvalishvili
  "O'Malley" / "Suga"     → Sean O'Malley
  "Vera" / "Chito"        → Marlon Vera
  "Holloway"              → Max Holloway
  "Poirier"               → Dustin Poirier
  "Gaethje"               → Justin Gaethje
  "Oliveira" / "Do Bronx" → Charles Oliveira
  "Makhachev"             → Islam Makhachev
  "Volkanovski" / "Volk"  → Alexander Volkanovski
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
    status: str  # "ok" | "limit_reached" | "no_results" | "error"

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


def _get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.groq_api_key)


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
        sql_resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0,       # deterministic SQL generation
            max_tokens=512,
        )
        sql = _clean_sql(sql_resp.choices[0].message.content)
    except RateLimitError as e:
        msg = str(e).lower()
        if "day" in msg or "daily" in msg:
            return ChatResponse(
                answer="Daily request limit reached. The chat resets tomorrow.",
                status="limit_reached",
            )
        return ChatResponse(
            answer="Too many requests — please wait a moment and try again.",
            status="rate_limited",
        )
    except Exception as e:
        logger.error("SQL generation failed: %s", e)
        return ChatResponse(answer="Failed to generate a query for your question.", status="error")

    logger.info("Generated SQL: %s", sql)

    # ── Step 2: Execute SQL ─────────────────────────────────────────────────
    try:
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
            "Be specific with numbers. Do not mention SQL, databases, or feature names literally."
        )
        max_tokens = 600
    else:
        format_prompt = (
            f"The user asked: {request.question}\n\n"
            f"Database results:\n{_rows_to_text(rows)}\n\n"
            "Write a clear, concise answer in 1-3 sentences. "
            "Include specific names, numbers, and fight details from the results. "
            "Do not mention SQL or databases."
        )
        max_tokens = 256

    try:
        answer_resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": format_prompt}],
            temperature=0.3,
            max_tokens=max_tokens,
        )
        answer = answer_resp.choices[0].message.content.strip()
    except RateLimitError:
        # Return raw rows as fallback if formatting hits rate limit
        answer = _rows_to_text(rows)
    except Exception as e:
        logger.error("Answer formatting failed: %s", e)
        answer = _rows_to_text(rows)

    return ChatResponse(answer=answer, sql=sql, status="ok")
