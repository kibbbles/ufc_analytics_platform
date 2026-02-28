# UFC Analytics Platform — API Documentation

**Base URLs**
- Development: `http://localhost:8000` (run `python run_dev.py` from `backend/`)
- Production: `gunicorn api.main:app -c gunicorn.conf.py` from `backend/`

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Request / Response Pattern

Every request flows through:
1. CORS middleware — sets cross-origin headers for the React frontend
2. RequestIDMiddleware — stamps `X-Request-ID` header with a UUID
3. TimingMiddleware — logs method, path, status, duration on response
4. Route handler — opens DB session via `get_db()`, runs raw SQL, returns Pydantic model
5. Error handler — any unhandled exception returns structured JSON (never an HTML stack trace)

---

## Health Endpoints

### GET /health
Liveness check. Always returns 200.

```json
{
  "status": "ok",
  "environment": "development",
  "version": "1.0.0",
  "timestamp": "2026-02-28T12:00:00+00:00"
}
```

### GET /health/db
Readiness check. Runs `SELECT 1` against the database.

**200 — connected:**
```json
{ "status": "ok", "db": "connected" }
```

**503 — unreachable:**
```json
{ "status": "error", "db": "connection refused" }
```

---

## Fighters  `/api/v1/fighters`

### GET /api/v1/fighters
Paginated fighter list.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 20 | Results per page (max 100) |
| search | string | — | Partial name match |

**Response:**
```json
{
  "data": [
    {
      "id": "abc123",
      "first_name": "Conor",
      "last_name": "McGregor",
      "nickname": "The Notorious",
      "weight_class": "Lightweight",
      "wins": 22,
      "losses": 6
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 4449, "total_pages": 223 }
}
```

### GET /api/v1/fighters/{id}
Full fighter profile.

**Response:** All fields from `fighter_details` + `fighter_tott` physical and career stats + computed record.
```json
{
  "id": "abc123",
  "first_name": "Conor",
  "last_name": "McGregor",
  "nickname": "The Notorious",
  "height_inches": 69.0,
  "weight_lbs": 155.0,
  "reach_inches": 74.0,
  "stance": "Southpaw",
  "dob_date": "1988-07-14",
  "slpm": 5.32,
  "str_acc": "51%",
  "sapm": 4.53,
  "str_def": "54%",
  "td_avg": 0.68,
  "td_acc": "53%",
  "td_def": "66%",
  "sub_avg": 0.5,
  "wins": 22,
  "losses": 6,
  "draws": 0,
  "no_contests": 1
}
```

**404** if fighter not found.

---

## Fights  `/api/v1/fights`

### GET /api/v1/fights
Paginated fight list.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| page / page_size | int | Pagination |
| event_id | string | Filter by event |
| fighter_id | string | Fights involving this fighter |
| weight_class | string | Exact weight class match |
| method | string | Partial method match (e.g. "KO", "Submission") |

### GET /api/v1/fights/{id}
Fight detail with round-by-round stats for both fighters.

**Response includes:** `fighter_a_id`, `fighter_b_id`, `winner_id`, `method`, `round`, `time`,
`is_title_fight`, `total_fight_time_seconds`, and a `stats` array with per-round
`sig_str_landed`, `td_landed`, `ctrl_seconds`, `kd_int`, etc.

**404** if fight not found.

---

## Events  `/api/v1/events`

### GET /api/v1/events
Paginated event list, ordered newest first.

**Query params:** `page`, `page_size`, `year` (e.g. `?year=2023`)

### GET /api/v1/events/{id}
Event detail with full fight card.

**Response:**
```json
{
  "id": "xyz789",
  "name": "UFC 300",
  "event_date": "2024-04-13",
  "location": "Las Vegas, Nevada, USA",
  "fights": [ ... ]
}
```

**404** if event not found.

---

## Predictions  `/api/v1/predictions`

### POST /api/v1/predictions/fight-outcome
Predict the outcome of a matchup.

> **Note:** Returns a stub 50/50 response until the ML model is integrated in Task 6.

**Request:**
```json
{
  "fighter_a_id": "abc123",
  "fighter_b_id": "def456",
  "fighter_a_age": 30,
  "fighter_a_reach_inches": 74.0,
  "fighter_b_weight_lbs": 155.0
}
```
`fighter_a_id` and `fighter_b_id` are required. All slider override fields are optional.

**Response:**
```json
{
  "fighter_a_id": "abc123",
  "fighter_b_id": "def456",
  "predicted_winner_id": "abc123",
  "win_probability": 0.5,
  "confidence": 0.0,
  "method_probabilities": {
    "ko_tko": 0.33,
    "submission": 0.33,
    "decision": 0.34
  },
  "similar_fight_ids": []
}
```

**404** if either fighter ID is not found.

---

## Analytics  `/api/v1/analytics`

### GET /api/v1/analytics/style-evolution
Finish rates (KO/TKO, Submission, Decision) by year across UFC history.

**Query params:** `weight_class` (optional — filters to one division)

**Response:**
```json
{
  "data": [
    {
      "year": 2023,
      "ko_tko_rate": 0.28,
      "submission_rate": 0.18,
      "decision_rate": 0.54,
      "total_fights": 312,
      "weight_class": null
    }
  ],
  "weight_class": null
}
```

### GET /api/v1/analytics/fighter-endurance/{id}
Round-by-round average performance for a fighter across all their fights.

> Detailed stats only available for fights from ~2015 onward. Fighters with earlier careers
> will receive a `note` field explaining limited data.

**Response:**
```json
{
  "fighter_id": "abc123",
  "fighter_name": "Conor McGregor",
  "rounds": [
    {
      "round": 1,
      "avg_sig_str_landed": 17.4,
      "avg_sig_str_pct": 0.48,
      "avg_ctrl_seconds": 12.0,
      "avg_kd": 0.21,
      "fight_count": 14
    }
  ],
  "note": null
}
```

**404** if fighter not found.

---

## Error Responses

All errors return structured JSON (never HTML):

```json
{
  "error": "Fighter 'xyz' not found",
  "status_code": 404,
  "request_id": "a1b2c3d4-..."
}
```

The `request_id` matches the `X-Request-ID` response header, making it easy to
correlate a frontend error with the server log entry.
