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
    except RateLimitError:
        return ChatResponse(
            answer="The chat assistant has reached its daily limit. Please try again tomorrow.",
            status="limit_reached",
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
    format_prompt = (
        f"The user asked: {request.question}\n\n"
        f"Database results:\n{_rows_to_text(rows)}\n\n"
        "Write a clear, concise answer in 1-3 sentences. "
        "Include specific names, numbers, and fight details from the results. "
        "Do not mention SQL or databases."
    )

    try:
        answer_resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": format_prompt}],
            temperature=0.3,
            max_tokens=256,
        )
        answer = answer_resp.choices[0].message.content.strip()
    except RateLimitError:
        # Return raw rows as fallback if formatting hits rate limit
        answer = _rows_to_text(rows)
    except Exception as e:
        logger.error("Answer formatting failed: %s", e)
        answer = _rows_to_text(rows)

    return ChatResponse(answer=answer, sql=sql, status="ok")
