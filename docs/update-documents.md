# Documentation Update Guide

Run through this checklist whenever asked to update documentation.
Each section lists the file, what to check, and what to update.

---

## 1. `backend/requirements.txt`

**Check:** Any new packages imported in code that aren't listed.
**Update:** Add the package with its pinned version under the correct section comment.
**How to find new deps:** `grep -r "^import\|^from" backend/ --include="*.py"` and cross-reference with the file.

---

## 2. `CLAUDE.md` (project root)

**Check each section:**

- **Backend Stack** — framework version, new middleware, logging, server config added
- **FastAPI Backend** (or equivalent task section) — update route list if endpoints added/changed, update key files list
- **ETL Pipeline / Data Status** — update row counts if a new scrape ran
- **Database Schema** — update if columns or tables were added

**Do not touch:** Business problem, Three Core Products, Frontend Stack, DB connection strings.

---

## 3. `README.md` (project root)

**Check each section:**

- **Tech Stack** — framework versions, new tools added
- **Getting Started / Backend Setup** — startup commands still accurate
- **API Endpoints table** — add new routes, remove stale ones, verify paths match code
- **Project Status table** — flip task rows from ⏳ to ✅ as tasks complete
- **Project Structure** — add new directories or files that a new reader would need to know about
- **Last Updated** date at the bottom

---

## 4. `.taskmaster/docs/progress.md`

**Check each section:**

- **Overall Status table** — flip task rows from ⏳ to ✅
- **Completed task sections** — add a new `## Completed: Task N — <Name> (date)` block for each finished task, listing what was built and key files
- **Up Next section** — update to reflect the next pending task

---

## 5. `.taskmaster/docs/api-docs.md`

**Update when:** Any endpoint is added, changed, or removed.

**For each changed endpoint, update:**
- Method and path
- Query params table
- Request body example (for POST)
- Response JSON example
- 404 / error conditions

**Also update:** The request/response pattern section at the top if middleware changes.

---

## 6. `docs/codebase-map.md`

**Update when:** New `.py` files are added, files are deleted, or a directory goes from empty to populated.

**For new files:** Add an entry under the appropriate category (CRITICAL / IMPORTANT / the relevant backend section).
**For deleted files:** Move to the DELETED section with a strikethrough and reason.
**For new directories:** Add to the relevant section (e.g., new endpoint files go under the FastAPI Backend section).

**Do not:** Document scraper internals here — that level of detail lives in `database-schema-and-cleaning-guide.md`.

---

## 7. `docs/database-schema-and-cleaning-guide.md`

**Update when:** A column is added, a table is changed, or the ETL pipeline gains a new phase.

**Check:** Row counts in the header summary, column lists per table, FK relationship status table.

---

## Files That Do NOT Need Regular Updates

| File | Why |
|------|-----|
| `docs/data-requirements.md` | ML feature specs — only changes if product requirements change |
| `docs/research-references.md` | External papers — only changes if new research is referenced |
| `docs/sanity-check.md` | One-time verification notes |
| `.taskmaster/CLAUDE.md` | Task Master workflow guide — only changes if tooling changes |
| `.taskmaster/tasks/tasks.json` | Auto-managed by task-master commands |

---

## Order to Run Updates

1. `requirements.txt` — do first, it's the smallest and most mechanical
2. `CLAUDE.md` — do second, it's the source of truth Claude reads at session start
3. `README.md` — mirrors CLAUDE.md but audience is GitHub visitors
4. `.taskmaster/docs/progress.md` — task-level summary
5. `.taskmaster/docs/api-docs.md` — only if endpoints changed
6. `docs/codebase-map.md` — only if files were added or deleted

---

## Commit Message Format

```
docs: update all docs to reflect Task N completion

- README.md: <what changed>
- CLAUDE.md: <what changed>
- docs/codebase-map.md: <what changed>
- .taskmaster/docs/progress.md: <what changed>
- .taskmaster/docs/api-docs.md: <what changed>
- backend/requirements.txt: <what changed>
```
