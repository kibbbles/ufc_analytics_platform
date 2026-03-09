# MVP Point — Pre-Firebase Milestone

This document defines the minimum viable product state the site must reach before migrating hosting to Firebase. Everything listed here must be complete and presentable before that switch happens.

---

## Goal

A publicly shareable, visually polished portfolio piece that demonstrates:
- Real ML-powered fight predictions with interactive controls
- Live upcoming UFC event data (auto-updated)
- Clean data journalism aesthetic (FiveThirtyEight-style)
- Mobile-first, works great on a phone

---

## Tasks Included in MVP

### Already Done
- ✅ Task 4 — FastAPI backend (all core endpoints)
- ✅ Task 6 — ML models (XGBoost + RF ensemble, fight outcome predictions)
- ✅ Task 7 — React frontend foundation (routing, state, API layer, Events + Fighters pages)

### Remaining for MVP

#### Task 8 — Fight Outcome Predictor UI
The interactive prediction tool. Users select two fighters, adjust physical attributes via sliders, and see win probability update in real time. Method prediction (KO/TKO, Submission, Decision) shown with confidence scores. This is the centrepiece feature of the site.

#### Tasks 11–15 — Upcoming Events (Phase 2 scraper + API + UI)
- Task 11: Create upcoming_events, upcoming_fights, upcoming_predictions tables in Supabase
- Task 12: Build upcoming_scraper.py — scrapes UFCStats /upcoming page
- Task 13: FastAPI endpoints — GET /api/v1/upcoming/events, /upcoming/events/{id}, /upcoming/fights/{id}
- Task 14: POST /api/v1/admin/refresh-upcoming — manual re-scrape + prediction recompute trigger
- Task 15: Upcoming Events UI — next card, fight list, pre-computed predictions per bout

---

## UI Changes Required Before MVP

### Navigation (Header)
- Top line (site name/tagline): **"Kabe's Maybes — UFC odds, our way"**
- Below logo / sub-tagline: **"Fight predictions, by the numbers"**
- Keep these nav links: **Home, Predictions, Upcoming, Events, Fighter Lookup**
- Remove: **Analytics** (style evolution and endurance are post-MVP, not in top nav)
- Add: **About**

### Pages

**Predictions** (`/predictions`)
- Full interactive predictor UI (Task 8)
- Must be functional with real ML model responses

**Upcoming** (`/upcoming`)
- Live upcoming UFC event card scraped from UFCStats (Task 15)
- Pre-computed predictions per announced fight

**Events** (`/events`)
- Already functional ✅

**Fighter Lookup** (`/fighters` and `/fighters/:id`)
- List and detail pages already functional ✅
- Currently goes to a placeholder that says "Fighter Lookup — currently under development" until the detail page design is polished enough for MVP

**About** (`/about`)
- New page
- Content: Introduction to the project — who built it, what it does, how it works
- Tone: casual and personal, not corporate
- Content direction:
  - Hi, I'm Kabe
  - This project scrapes UFC fight data directly from UFCStats.com — no third-party APIs
  - Data covers every UFC event since 1994, updated weekly after each event
  - Uses machine learning models (XGBoost, Random Forest) trained on historical fight data to predict outcomes
  - The predictor shows win probability and method prediction (KO/TKO, Submission, Decision)
  - Built with FastAPI, React, PostgreSQL (Supabase), hosted on Render + Vercel
  - Open to feedback, built for fun and to sharpen data science + engineering skills

**Home** (`/`)
- Keep for now, design TBD based on evolving preferences

**Analytics, Style Evolution, Endurance** (any other routes)
- Show a placeholder: "Currently under development" with a brief description of what will be here

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

---

## Definition of Done

The MVP is complete when:
- [ ] Predictions page works end-to-end with real ML responses
- [ ] Upcoming page shows the next real UFC event with pre-computed predictions
- [ ] All non-functional nav items either work or show a "currently under development" placeholder
- [ ] About page is live
- [ ] Header says "Kabe's Maybes" and nav is trimmed to the approved links
- [ ] Site looks acceptable on mobile (375px) and desktop
- [ ] All changes deployed and live at kabes-maybes.vercel.app
- [ ] Ready to migrate hosting to Firebase

---

## Post-MVP (not blocking)
- Style Evolution Timeline (Task 9)
- Fighter Endurance Dashboard (Task 10)
- Custom domain (e.g. kabesmaybes.com)
- Firebase migration
