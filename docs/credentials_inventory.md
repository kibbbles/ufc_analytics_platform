# Credentials and Secrets Inventory

This document lists every place a credential or secret lives for this project, and the exact steps to rotate each one.
It exists because a Supabase password rotation in July 2026 updated two of the three stores that hold the database credential and missed the third (GitHub Actions), which silently broke the entire automation chain for a week and permanently cost one event's pre-fight prediction.
A missed store does not error at rotation time; it only fails later, when a consumer runs. This document is the checklist that prevents that.

## The one that bit us

The Supabase database password lives in **three** separate `DATABASE_URL` stores, and two of them use a different host than the third.
Rotating the password means updating all three, and the GitHub one must keep the pooler host rather than a copy-paste of the direct-host string from `.env`.

| Store | Host used | Notes |
|---|---|---|
| Local `.env` | direct: `db.mklpmbqpegbsistkoskm.supabase.co:5432` | developer machine only |
| GitHub Actions secret `DATABASE_URL` | pooler: `aws-1-us-east-1.pooler.supabase.com:5432` | the one missed in July 2026 |
| Google Cloud Secret Manager `DATABASE_URL` | direct: `db.mklpmbqpegbsistkoskm.supabase.co:5432` | Cloud Run reads version `:latest` |

All three authenticate as user `postgres` with the same password. Only the host and port-routing differ.

## Full inventory of secret stores

### 1. Local `.env` (developer machine, git-ignored)

Holds:
- `DATABASE_URL` - Supabase, direct host. Used by all local scripts and by the FastAPI dev server.
- `ANTHROPIC_API_KEY` - local tooling only.
- `GROQ_API_KEY` - Groq LLM, used by the chat endpoint when run locally.
- `ODDS_API_KEY` - betting-odds provider, used by the upcoming-predictions scraper when run locally.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - Supabase project URL and anon key (the anon key is public by design).

### 2. GitHub Actions secrets (repo Settings -> Secrets and variables -> Actions)

Enumerate with `gh secret list`. Current secrets:
- `DATABASE_URL` - Supabase, **pooler host**. Used by six workflows: daily-keepalive, weekly-ufc-scraper, post-scrape-clean, feature-engineering, retrain, upcoming-predictions.
- `GCP_SA_KEY` - Google Cloud service-account JSON key. Used by deploy-backend to authenticate to Google Cloud.
- `GROQ_API_KEY` - Groq LLM. Used by deploy-backend, which passes it to Cloud Run as an environment variable.
- `ODDS_API_KEY` - betting-odds provider. Used by upcoming-predictions.
- `GITHUB_TOKEN` - provided automatically by GitHub Actions, not managed by us. Used by retrain to commit model artifacts.

### 3. Google Cloud Secret Manager (project `kabes-maybes`)

Referenced by the Cloud Run service `kabes-maybes-api`:
- `DATABASE_URL` - Supabase, direct host. The service references version `:latest`, so a rotation is applied by adding a new version.
- `ALLOWED_ORIGINS` - CORS origins for the API. Not a credential, but rotated the same way if the frontend domain changes.

### 4. Google Cloud Run environment variables (set at deploy time)

- `GROQ_API_KEY` - set on every deploy by `deploy-backend.yml` from the GitHub secret of the same name (`--set-env-vars`). It is NOT in Secret Manager; the deploy workflow removes any old secret binding and sets it as a plain env var. So the source of truth for the deployed value is the GitHub secret.

### 5. Vercel (frontend project)

- `VITE_API_BASE_URL` - the public Cloud Run API URL. This is not a secret and contains no credential. There is no database credential anywhere in the frontend.

## Rotation checklists

### Rotating the Supabase database password

This is the high-risk one. Update all three stores.

1. Supabase dashboard -> Project Settings -> Database -> Reset database password. Copy the new password.
2. Local `.env`: update the password inside `DATABASE_URL`, keeping the **direct** host `db.mklpmbqpegbsistkoskm.supabase.co:5432`.
3. GitHub Actions secret `DATABASE_URL`: set the new password, keeping the **pooler** host `aws-1-us-east-1.pooler.supabase.com:5432`. Do not paste the `.env` direct-host string. Set via `gh secret set DATABASE_URL` or the repo UI.
4. Google Cloud Secret Manager `DATABASE_URL`: add a new secret version with the new password, keeping the direct host. Cloud Run reads `:latest`; a redeploy or the next cold start picks it up.
5. Verify all three:
   - GitHub: run the daily-keepalive workflow manually (`gh workflow run "Daily Supabase Keepalive"`) and confirm it is green.
   - Cloud Run: hit `/health/db` and confirm 200.
   - Local: run any script that opens a session, or `python -c "from db.database import SessionLocal; SessionLocal().execute(__import__('sqlalchemy').text('select 1'))"`.

### Rotating `GROQ_API_KEY`

1. Regenerate the key in the Groq console.
2. Update the GitHub Actions secret `GROQ_API_KEY`.
3. Update local `.env`.
4. Redeploy the backend so Cloud Run picks up the new value: push a backend change, or run the deploy-backend workflow via `workflow_dispatch`.

### Rotating `ODDS_API_KEY`

1. Regenerate the key with the odds provider.
2. Update the GitHub Actions secret `ODDS_API_KEY` and local `.env`. No redeploy needed; it is read by the scheduled scraper directly.

### Rotating `GCP_SA_KEY`

1. Create a new key for the service account in Google Cloud IAM, and delete the old one after cutover.
2. Update the GitHub Actions secret `GCP_SA_KEY`. Used only by deploy-backend.

### Rotating `ANTHROPIC_API_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_URL`

Local `.env` only. Update there. The anon key and URL are not secret.

## Why a missed store is silent, and the canary

Nothing checks that the stores agree. Each consumer only fails when it next runs, and the failures are spread across schedules, so a partial rotation can look fine for hours.
The earliest warning is the daily-keepalive workflow: it runs every day and does nothing but open a database connection.
If it goes red the morning after a rotation, a `DATABASE_URL` store was missed. Treat a red keepalive as a rotation error until proven otherwise.
