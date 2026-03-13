# MVP Point — Pre-Firebase Milestone

This document defines the minimum viable product state the site must reach before migrating hosting to Firebase. Everything listed here must be complete and presentable before that switch happens.

---

## Goal

A publicly shareable, visually polished portfolio piece that demonstrates:
- Live upcoming UFC event predictions with per-fight analysis (the centrepiece)
- Clean data journalism aesthetic (FiveThirtyEight-style)
- Mobile-first, works great on a phone

---

## Tasks Included in MVP

### Already Done
- ✅ Task 4 — FastAPI backend (all core endpoints)
- ✅ Task 6 — ML models (XGBoost + RF ensemble, fight outcome predictions)
- ✅ Task 7 — React frontend foundation (routing, state, API layer, Events + Fighters pages)
- ✅ Task 11 — upcoming_events, upcoming_fights, upcoming_predictions tables created in Supabase
- ✅ Task 12 — upcoming_scraper.py: scrapes UFCStats /upcoming, matches fighters by URL, idempotent upserts; 9 events, 79 fights, 77/79 fighters matched (2 debuting fighters skipped)
- ✅ Task 13 — FastAPI endpoints: GET /api/v1/upcoming/events, /upcoming/events/{id}, /upcoming/fights/{id} with Pydantic schemas
- ✅ Task 14 — compute_predictions.py: builds ML features + runs model for all matched fights, upserts into upcoming_predictions with feature hash for staleness detection; 77 predictions written
- ✅ Task 15 — run_upcoming.py entry point (scraper → predictions in sequence) + GitHub Actions workflow scheduled Friday 12:00 UTC

### Task Progress (21–25)

#### ✅ Task 21 — Upcoming Events UI (`/upcoming`) — DONE
The centrepiece of the site. Accordion event rows expand to show the full fight card. Per-fight rows show fighter names, win probabilities (1 decimal), method breakdown (KO/TKO / Sub / Dec), and weight class. Winner indicated by bold/full-contrast name vs muted loser. Auto-updates every Friday via GitHub Actions.

What's in:
- Lazy-fetch accordion: fights only load when you open an event (no page-load blast)
- NEXT badge on the soonest upcoming event; Numbered badge on UFC numbered cards (desktop only)
- Badges always on their own line above the event name — consistent on all screen sizes
- Date + location on line 2, bout count always on line 3 (no wrapping)
- Centered layout on desktop (max-w-[1100px]), single-column on mobile
- Predictions show 1 decimal place (e.g. 57.1%)
- Subtitle notes Friday automated refresh

Also included in Task 21 (already done, keep):
- Age and all days-based features now display as years (e.g. "29.4 yrs" instead of raw days)
- Rolling window features surfaced in the feature breakdown

#### ✅ Task 22 — Fight Matchup Page + Events Page Enhancements — DONE

**Fight matchup page** (`/upcoming/fights/:id`):
- Clicking a fight row navigates to a dedicated matchup page — no modal, no popup
- Page shows everything in one place: Tale of the Tape, win probability bar, method breakdown, striking differentials, grappling differentials, key model features, recent fights for each fighter
- Fighter names are links to `/fighters/:id`
- Mobile-first single-column layout

**Events page enhancements** (`/events`):
- Completed / Upcoming toggle at the top
- Event name search/filter input

#### ✅ Task 23 — Past Predictions (Model Transparency) — DONE

Show the model's test-set results on completed fights. FiveThirtyEight honesty play — don't just show predictions, show the track record.

**What's built:**
- `past_predictions` table (VARCHAR(8) IDs/FKs — fight IDs are 8-char hex)
- `compute_past_predictions.py` backfill: 1716 fights from Jan 2022 → present using training_data.parquet; 62.4% accuracy overall, 84.2% when ≥65% confident
- `GET /api/v1/past-predictions` — summary stats + recent fights
- `GET /api/v1/past-predictions/events` — paginated event list with search + year filter
- `GET /api/v1/past-predictions/events/{event_id}` — all fights for a given event
- `GET /api/v1/past-predictions/fights` — fighter name search, optional, defaults to 10 most recent
- `GET /api/v1/past-predictions/fights/{fight_id}` — single fight detail
- Home page `ModelScorecard` card: compact stats line, model description, Events | Fight Search tabs
- Events tab: paginated event browser with search + year filter — matches Events page UX
- Fight Search tab: defaults to 10 most recent, search by fighter name, year filter
- `PastPredictionEventPage` (`/past-predictions/events/:event_id`): all fight predictions for an event, centered, fights clickable
- `PastPredictionFightPage` (`/past-predictions/fights/:fight_id`): mirrors UpcomingFightPage exactly (tale of tape, prediction card, striking, grappling, recent fights) + ActualResultCard (green correct / red incorrect / amber upset)

**Key bug fixes during Task 23:**
- VARCHAR(6) → VARCHAR(8) for fight_id FKs (fight IDs are 8-char not 6)
- Removed unused TS variables to fix Vercel TS6133 build errors
- Fixed nested `<Link>` inside `<a>` (invalid HTML) — replaced outer with `div+onClick`
- Fixed `[object Object]` error: FastAPI 422 returns `detail` as array; Axios interceptor now guards `typeof rawDetail === 'string'`
- Fixed debounce with `useRef` (closure-based approach broke across renders)
- Added `available_years` to summary endpoint (dynamic year dropdown, no hardcoded years)
- Made `search` optional in `/fights` endpoint (was accidentally required → caused 422 on load)

#### ✅ Task 24 — Mobile Polish + Deployment Verification — DONE

All pages verified usable on mobile. Render + Vercel deploys clean. Render free tier cold-start (~30s) is accepted tradeoff for portfolio project. No blocking layout issues found.

**What Task 24 actually means** (for reference):
- Every page checked at 375px viewport — no horizontal scroll, touch targets ≥44px, stats readable
- Header hamburger menu works on small screens
- Accordion fight cards on `/upcoming` expand cleanly on mobile tap
- Fight matchup page single-column on mobile (tale of tape as labeled rows, not side-by-side)
- Vercel auto-deploys on push to `main`; Render deploys on Docker image rebuild
- Cold-start mitigation: Render free tier sleeps after 15 min inactivity, wakes on next request (~30s). Accepted for now. Upgrade to $7/month paid tier or Firebase to eliminate

#### ✅ Task 20 — Integration Testing — DONE (implicit)
The full pipeline runs end-to-end: UFCStats scraper → ETL → feature engineering → model retrain → upcoming predictions → API → UI. Manual verification confirms all data flowing correctly.

#### Task 25 — Firebase / Cloud Run Migration — Post-MVP
Not blocking. See Post-MVP section.

---

## UI Changes Required Before MVP

### Navigation (Header) ✅ Done
- Top line: **"Kabe's Maybes — UFC odds, my way"** (desktop) / **"Kabe's Maybes"** (mobile) ✅
- Sub-tagline: removed ✅
- Nav links: **Home, Upcoming, Events, Fighter Lookup, About** ✅ (Predictions + Analytics removed)

### Pages

**Upcoming** (`/upcoming`) ✅
- Live upcoming UFC event card(s) scraped from UFCStats (Task 15)
- Accordion/dropdown rows — click an event to expand the fight card inline
- Per-fight rows show win probability bar, method breakdown, key stat differentials
- Tapping a fight row → full matchup page

**Events** (`/events`) ✅
- Completed / Upcoming toggle ✅
- Event name search/filter ✅

**Fighter Lookup** (`/fighters` and `/fighters/:id`) ✅

**About** (`/about`) ✅

**Home** (`/`) ✅ — ModelScorecard with Events | Fight Search tabs

---

## Design Preferences (continuously updated)

- Aesthetic: data journalism (FiveThirtyEight / The Pudding style) — not a commercial app
- Mobile-first, works well on 375px screens
- Dark mode default, light mode equally polished
- UFC red (`#e63946`) for active states and key callouts only — not decorative
- Monospace/tabular numbers for all stats
- No hero sections, no marketing copy, no "Get Started" CTAs
- Every page should feel like a well-crafted data analysis, not a product landing page

### UI Inspiration
- **Tapology** — fight card row layout, clean mobile presentation; UFC-only scope here, with deeper analytics than a general combat sports site
- **Oddschecker** — odds/probability shown directly in the fight row without clicking through; applied here as model win % (no Vegas lines, our own model outputs)
- **FiveThirtyEight sports predictions** (archived) — gold standard for sports probability on mobile: one dominant number per item, everything else secondary

---

## Definition of Done

**MVP is complete ✅**

- [x] Upcoming page shows next UFC event(s) with accordion fight card — per-fight win probability, method breakdown (Task 21 ✅)
- [x] Fight matchup page — dedicated route per fight with tale of the tape, method breakdown, model feature breakdown, fighter name links (Task 22 ✅)
- [x] Completed / Upcoming toggle and event name search on Events page (Task 22 ✅)
- [x] Past predictions scorecard with Events + Fight Search tabs (Task 23 ✅)
- [x] Fight detail page for past predictions mirroring upcoming matchup page (Task 23 ✅)
- [x] All non-functional nav items show a "currently under development" placeholder
- [x] About page is live
- [x] Header shows "Kabe's Maybes — UFC odds, my way" on desktop, "Kabe's Maybes" on mobile
- [x] Nav trimmed to: Home, Upcoming, Events, Fighter Lookup, About
- [x] Site looks acceptable on mobile (375px) and desktop
- [x] All changes deployed and live at kabes-maybes.vercel.app
- [x] Ready to migrate hosting to Firebase

---

## Post-MVP (not blocking)

- Task 25 — Firebase / Cloud Run migration (backend off Render, faster cold starts)
- Fight Outcome Predictor with interactive sliders (Task 8)
- Style Evolution Timeline (Task 9)
- Fighter Endurance Dashboard (Task 10)
- Custom domain (e.g. kabesmaybes.com)
