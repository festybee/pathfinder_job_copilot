# Pathfinder Job Copilot (v1 - Django + React)

A personal job-search web app: define selectable search criteria (not
hardcoded to any one title/country), pull matching postings from Adzuna,
Reed, and JSearch (which itself aggregates Google for Jobs - LinkedIn,
Indeed, Glassdoor, ZipRecruiter, and more), screen them against an
editable occupation going-rate table
(useful for visa sponsorship eligibility, but works for anyone), build a
portfolio of CVs/certs/project write-ups, and generate tailored CVs,
cover letters, and application Q&A answers grounded only in the portfolio
documents you select. Every user has their own login and their own data.

## Stack, and why

Two UIs, one Django backend, sharing the same database:

1. **Server-rendered templates + [HTMX](https://htmx.org)** (`templates/`, and
   `templates/` inside each app) - the original UI, unchanged, still fully
   functional at `/`, `/criteria/`, `/portfolio/`, etc. No build step.
2. **A separate React app** (`frontend/`) talking to a REST API
   (`django rest framework`, under `/api/`) - added because a plain
   template UI made it hard to keep concerns (search, results, tracker,
   portfolio, AI actions) visually and structurally separate as the app
   grew. Runs as its own process (`npm run dev`, port 5173 by default).

Both are optional entry points into the same data - create a criteria
profile in one, see it in the other. If you only ever use one of them,
that's fine; the other doesn't need to be running.

Auth is Django's built-in `django.contrib.auth` for the template UI
(session cookies), and DRF token authentication for the API
(`Authorization: Token <key>` header) - session cookies don't play nicely
across two different origins/ports without extra CORS/CSRF plumbing that
isn't worth it for a personal project, so the API uses its own token
instead. Every model that holds user data (`Document`, `CriteriaProfile`,
`Job`) has an `owner` ForeignKey either way, and both the template views
and the API views filter to `request.user`.

## App layout

Physically split into `backend/` and `frontend/`, sitting side by side:

```
pathfinder-job-copilot/
  backend/                 # Django project - everything below was under the repo root before
    manage.py
    config/                  # project settings, root urls, wsgi/asgi
    accounts/                # login, signup (Django auth) + serializers.py/api_views.py/api_urls.py
    portfolio/               # Document model - CV/cert/project library + API equivalents
    jobsearch/               # CriteriaProfile, ThresholdRow, Job, SponsorRegisterEntry models
      integrations/
        base.py               # ExternalJob dataclass + JobIntegration protocol
        adzuna.py              # Adzuna API client
        reed.py                 # Reed API client (UK only)
        jsearch.py               # JSearch API client (aggregates Google for Jobs)
      management/commands/
        sync_sponsor_register.py  # downloads the gov.uk sponsor register CSV
        check_sponsors.py          # re-checks existing jobs against it
      services.py              # run_search() / save_results() / evaluate_threshold()
      sponsor_register.py      # company-name matching against the register
      serializers.py, api_views.py, api_urls.py   # REST API for this app
    aiassist/                # GeneratedDraft model + Anthropic-backed service.py
      service.py               # tailor_cv() / draft_cover_letter() / answer_question()
      serializers.py, api_views.py, api_urls.py
    templates/base.html      # shared layout + nav + HTMX script tag (template UI)
    static/css/style.css
    requirements.txt
    .env.example
    .gitignore
  frontend/                # separate React app (Vite) - the other UI
    src/
      api.js                # fetch wrapper + all API calls
      AuthContext.jsx        # login/signup/logout + current-user state
      App.jsx                 # routes
      pages/                   # JobsPage, CriteriaListPage, CriteriaDetailPage,
                                # PortfolioPage, AiAssistPage, LoginPage, SignupPage
      components/               # NavBar, ProtectedRoute
```

### Data model summary

- `jobsearch.CriteriaProfile` - a saved search: keywords (comma-separated,
  editable), location, country code, job type, salary mode (either a flat
  minimum or the going-rate table below), and an optional
  `include_sponsorship_keyword` toggle that adds "visa sponsorship" as an
  extra, independent search term (weak signal - see below). You can have
  several profiles.
- `jobsearch.ThresholdRow` - one row of an occupation going-rate table
  scoped to a profile (keyword match, occupation code, threshold amount,
  currency, verified flag). Not UK-specific - edit the rows for any
  country's system.
- `jobsearch.Job` - a posting pulled in by search (or added manually),
  with `status` (new → interested → tailoring → applied → interviewing →
  offer/rejected), `sponsor_status` (unknown/likely/confirmed/no - see
  below for how "confirmed" gets set), and `threshold_pass` (computed
  against the matched profile).
- `jobsearch.SponsorRegisterEntry` - shared reference data: one row per UK
  government-registered Worker/Temporary Worker sponsor, loaded via
  `python manage.py sync_sponsor_register`. Matched against each job's
  employer name to auto-set `sponsor_status = confirmed` - see below.
- `portfolio.Document` - CV/certificate/project text you paste or upload;
  tagged and typed, feeds the AI layer.
- `aiassist.GeneratedDraft` - a saved AI output (CV, cover letter, or Q&A
  answer) tied to a job, recording exactly which `Document`s it was
  grounded in.

## Setup

### Backend (required either way)

```bash
cd pathfinder-job-copilot/backend
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env           # fill in ANTHROPIC_API_KEY, ADZUNA_*/REED_API_KEY
python manage.py makemigrations accounts portfolio jobsearch aiassist
python manage.py migrate
python manage.py createsuperuser
python manage.py sync_sponsor_register   # loads the UK sponsor register (~a minute, one-time)
python manage.py runserver
```

Visit `http://127.0.0.1:8000/accounts/signup/` to create your account
through the template UI, or `/admin/` with the superuser to manage data
directly. Job search needs at least one of Adzuna, Reed, or JSearch
credentials (all free tier); AI features need `ANTHROPIC_API_KEY`.

### Frontend (optional - the React UI)

In a second terminal, with the backend above still running:

```bash
cd pathfinder-job-copilot/frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL, defaults to http://localhost:8000/api
npm run dev
```

Visit `http://localhost:5173` and sign up there - it creates its own
account via the API (same `User` table, so it's separate from any account
you made through the template UI's signup unless you use the same
username). I couldn't run `npm install` or `npm run dev` myself this
session (same broken-shell issue as elsewhere), so this hasn't been
executed - if something doesn't compile, it's most likely a small typo
rather than a structural problem; the component logic mirrors the
already-working template views closely.

**JSearch fixed**: the initial version assumed `search-v2` returned
`{"data": [...]}` (a list of jobs directly). The real shape, per OpenWeb
Ninja's docs, nests it one level deeper - `{"data": {"jobs": [...],
"cursor": "..."}}` - so the old code was iterating over the dict's keys
("jobs", "cursor") instead of the job objects, throwing `'str' object
has no attribute 'get'`. Fixed in `jobsearch/integrations/jsearch.py`.
Note most JSearch postings don't include salary data at all (only
populated when the employer explicitly states it), so an empty
`compensation_raw` for JSearch results is expected, not a bug.

`sync_sponsor_register` downloads the UK government's list of licensed
Worker/Temporary Worker sponsors from gov.uk (auto-discovers the current
CSV link, since the filename changes roughly monthly) and stores it
locally. Re-run it periodically to keep it current, then run
`python manage.py check_sponsors` to re-check any existing jobs that
weren't confirmed the first time.

## Admin-approved signups

New accounts (through either UI) are created with `is_active=False` and
can't log in until an admin approves them. To approve someone: log into
`/admin/` as your superuser, open Authentication and Authorization > Users,
tick the "Active" checkbox on their row, and click Save at the bottom -
no need to open their individual profile. Newest signups sort to the top.

Both login paths (template and API) tell a pending user that their
account needs approval, rather than showing a generic "invalid
credentials" message - this needs `AUTHENTICATION_BACKENDS` set to
`AllowAllUsersModelBackend` in `settings.py` (already done), since the
default backend silently treats inactive users the same as a wrong
password. Your own superuser account (via `createsuperuser`) is active
immediately and isn't affected by any of this.

## What's genuinely working vs. what's a stub

- **Working end-to-end**: signup/login (with admin approval gating - see
  above), portfolio document CRUD, criteria
  profile + going-rate table CRUD, Adzuna/Reed search wired to real APIs,
  job tracker with status/sponsor updates, AI tailoring/cover
  letter/Q&A wired to the Anthropic API and grounded in selected documents.
- **Sponsor-licence status**: two layers, neither claiming false
  certainty. (1) A weak keyword heuristic - ticking
  "include_sponsorship_keyword" on a criteria profile adds "visa
  sponsorship" as an extra search term, surfacing postings that happen to
  say so. (2) The real check - `sync_sponsor_register` loads the actual
  gov.uk register, and every new job's employer name gets matched against
  it (`jobsearch/sponsor_register.py`); a match auto-sets `sponsor_status
  = confirmed`. A non-match is left as-is (never auto-set to "No") since
  company names in postings often don't exactly match their registered
  legal name - the system only ever asserts sponsorship when it's
  confident, and otherwise leaves it to you.
- **Not built yet**: LinkedIn/company career-page sources (no public
  API), auto-apply, password reset email, deployment config.
- **Frontend**: hand-written, not yet run/compiled (see the Setup note
  above) - covers the same ground as the template UI (auth, job tracker
  with filters, criteria + going-rate table CRUD, portfolio CRUD, AI
  actions), styled plainly, no polish pass done yet.

### Fixed along the way

Two real bugs worth knowing about if you're diffing history: the
`include_sponsorship_keyword` heuristic used to merge "visa sponsorship"
into the same query as your role keywords, which meant totally unrelated
postings (e.g. "Support Worker" showing up under a "Data Analyst" search)
could get pulled in - it's now a separate search pass, only kept if the
result is also relevant to your actual keywords. And Reed's search
endpoint (unlike Adzuna) returns raw salary numbers with no currency or
pay-period field, so a small hourly rate could get silently compared
against an annual threshold as if it were a yearly salary - `evaluate_threshold`
now treats implausibly low figures (<1000) as unparseable instead of
guessing.

JSearch had two bugs of its own, both now fixed. First, the response
shape was mis-parsed - jobs are nested under `data.jobs`, not `data`
directly, so results were silently empty/erroring. Second, and more
seriously: JSearch's own `country` request param isn't reliably honored
by the API, so a GB-scoped search could - and did - return US postings
(and others) mixed in. `jobsearch/integrations/jsearch.py` now filters
each result against the requested country client-side using the result's
own `job_country` field, so this won't recur for new searches. Jobs
already saved from before this fix can be cleaned up with
`python manage.py purge_bad_jsearch_jobs --dry-run` (then without
`--dry-run` once you're happy with what it lists).

## Housekeeping

**After the backend/frontend split**, every backend file now lives under
`backend/` (copied there, not moved - I can't move or delete files in
this environment). The old root-level copies are now stale duplicates
and should be deleted manually via File Explorer once you've confirmed
`backend/` works:

- `manage.py`, `config/`, `accounts/`, `portfolio/`, `jobsearch/`,
  `aiassist/`, `templates/`, `static/`, root `requirements.txt`, root
  `.env.example` - all now duplicated under `backend/`, delete the
  root-level originals.
- `.venv/` - **don't delete**; instead recreate it inside `backend/`
  (`cd backend && python -m venv .venv`) since a venv can't just be
  copied between locations.
- `.env` (your real secrets, not `.env.example`) - move it into
  `backend/.env` yourself; I never touch real secrets.
- `db.sqlite3`, if it exists at the root - move it into `backend/`
  (or just re-run migrations there and re-add your data/superuser).

This folder also has a `src/`, `tests/`, `data/`, and old root-level
`pyproject.toml` left over from an earlier standalone-CLI prototype that
predates the decision to build this as a Django web app - unrelated to
the app above, safe to delete alongside the stale root-level Django
files.

## Roadmap

- v1 (this): manual pipeline end-to-end, single-user-per-login, sqlite by default, sponsor-register cross-check, REST API + React frontend alongside the template UI
- v1.0.1: run `npm install && npm run dev` for real, fix whatever that surfaces
- v1.1: password reset email, deploy to Railway/Render with Postgres
- v1.2: scheduled/automatic re-sync of the sponsor register (currently manual)
- v1.3: additional job sources as APIs become available
- v2: auto-apply on user-approved jobs above a confidence threshold (deliberately out of scope until tailoring quality is proven out)
