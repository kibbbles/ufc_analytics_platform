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

**Fight matchup page** (`/upcoming/fights/:id` or `/fights/:id`):
- Clicking a fight row navigates to a dedicated matchup page — no modal, no popup
- Modelled on UFCStats event-detail → fight-detail flow: click a fight row on the upcoming page, land directly on the full matchup view
- Page shows everything in one place (no "view matchup" intermediate step):
  - **Tale of the Tape**: height, weight, reach, age, stance side-by-side
  - **Win probability bar** (the dominant visual, same as the accordion row)
  - **Method breakdown**: KO/TKO / Sub / Decision probabilities
  - **Striking differentials**: sig strikes, accuracy, head/body/leg breakdown
  - **Grappling differentials**: takedown %, submission attempts, control time
  - **Key model features**: the top drivers behind the prediction
- Fighter names are **links** to `/fighters/:id` — same fighter detail page used by the Fighter Lookup section (shows past fight history, tale of the tape, etc.)
- Mobile-first layout: single column, stats as labeled rows with A vs B values

**Events page enhancements** (`/events`):
- A **Completed / Upcoming toggle** at the top — switches between historical events list and the upcoming events list (reuses `/upcoming` data)
- A **search/filter input** that filters the visible event list client-side as the user types

#### Task 23 — Past Predictions (Model Transparency) — pending (stretch)
Show the model's test-set results on completed fights. FiveThirtyEight honesty play — don't just show predictions, show the track record.
- Per-fight: model's predicted winner + confidence %, actual result, correct/incorrect indicator
- Highlight upsets (model confident but wrong)
- Aggregate accuracy stats (overall, by weight class, by confidence tier)
- Needs: `past_predictions` table, one-time backfill script, FastAPI endpoint, UI component on event detail pages

**Not blocking MVP.**

#### Task 24 — Mobile Polish + Deployment Verification — pending
Final pass before MVP sign-off:
- Verify all pages usable at 375px
- Confirm Render + Vercel deploys are clean
- Check cold-start behaviour on Render free tier
- Any remaining layout/spacing issues

#### Task 20 — Integration Testing — pending (last, after 21–24)
End-to-end verification: upcoming scraper → predictions → API → UI all working together correctly after all tasks complete.

---

## UI Changes Required Before MVP

### Navigation (Header) ✅ Done
- Top line: **"Kabe's Maybes — UFC odds, my way"** (desktop) / **"Kabe's Maybes"** (mobile) ✅
- Sub-tagline: removed ✅
- Nav links: **Home, Upcoming, Events, Fighter Lookup, About** ✅ (Predictions + Analytics removed)

### Pages

**Upcoming** (`/upcoming`)
- Live upcoming UFC event card(s) scraped from UFCStats (Task 15)
- **Accordion/dropdown rows** — click an event to expand the fight card inline (no page navigation needed)
- Per-fight rows show: fighter A vs fighter B, win probability bar (dominant visual), top method chip (e.g. "60% Decision"), key stat differentials — all scannable at a glance on mobile
- Tapping a fight row expands for full method breakdown + differentials (depth on demand)
- Stats-forward, no narrative — the numbers tell the story
- UFC-only scope: no other promotions, deeper analytics than a general fight site
- **Inspired by Tapology** (fight card layout, clean row-based presentation) and **Oddschecker** (probability/odds displayed right in the fight row — applied here as model win % instead of Vegas lines)
- The main feature of the site

**Events** (`/events`)
- Already functional ✅
- Add **Completed / Upcoming toggle** at top (UFCStats-inspired) — toggles between `/events` and `/upcoming`
- Add **event name search/filter** input

**Fighter Lookup** (`/fighters` and `/fighters/:id`)
- List and detail pages already functional ✅

**About** (`/about`) ✅ Done
- Content: Introduction to the project — who built it, what it does, how it works
- Tone: casual and personal, not corporate
- Content direction:
  - Hi, I'm Kabe
  - This project scrapes UFC fight data directly from UFCStats.com — no third-party APIs
  - Data covers every UFC event since 1994, updated weekly after each event
  - Uses machine learning models (XGBoost, Random Forest) trained on historical fight data to predict outcomes
  - Each upcoming card shows win probability, method prediction (KO/TKO, Submission, Decision), and the key stats driving each pick
  - Built with FastAPI, React, PostgreSQL (Supabase), hosted on Render + Vercel
  - Open to feedback, built for fun and to sharpen data science + engineering skills

**Home** (`/`)
- Keep for now, design TBD based on evolving preferences

**Predictions, Analytics, Style Evolution, Endurance** (any non-functional routes)
- Show a "currently under development" placeholder

---

## Design Preferences (continuously updated)

*This section will be updated by Kabe as the project progresses.*

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

The MVP is complete when:
- [x] Upcoming page shows next UFC event(s) with accordion fight card — per-fight win probability, method breakdown (Task 21 ✅)
- [x] Fight matchup page — dedicated route per fight with tale of the tape, method breakdown, model feature breakdown, fighter name links (Task 22 ✅)
- [ ] Completed / Upcoming toggle and event name search on Events page (Task 22)
- [x] All non-functional nav items show a "currently under development" placeholder
- [x] About page is live
- [x] Header shows "Kabe's Maybes — UFC odds, my way" on desktop, "Kabe's Maybes" on mobile
- [x] Nav trimmed to: Home, Upcoming, Events, Fighter Lookup, About
- [ ] Site looks acceptable on mobile (375px) and desktop
- [ ] All changes deployed and live at kabes-maybes.vercel.app
- [ ] Ready to migrate hosting to Firebase
- [ ] (stretch) Past predictions visible on completed event pages — model hit/miss per fight, overall accuracy stats

---

## Post-MVP (not blocking)
- Fight Outcome Predictor with interactive sliders (Task 8)
- Style Evolution Timeline (Task 9)
- Fighter Endurance Dashboard (Task 10)
- Custom domain (e.g. kabesmaybes.com)
- Firebase migration
