# Pathfinder Job Copilot (v1 - Django API + React)

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

Two deployables, one database: `backend/` is a Django REST Framework API
(`/api/...`), `frontend/` is a React (Vite) app - the single UI. Intended
deployment is `frontend/` on Vercel and `backend/` on Railway, as two
separate services talking over HTTPS. Django's own `/admin/` panel stays
mounted for superuser/user-approval management, but there's no other
server-rendered UI - an earlier version had a parallel HTMX + Django
template UI, which was removed once the React app had full feature
parity, to avoid maintaining (and accidentally diverging) two frontends.

Auth is DRF token authentication (`Authorization: Token <key>` header)
rather than session cookies, since the two deployables live on entirely
different origins (Vercel vs. Railway) - avoids CORS+CSRF-cookie
complexity. Every model that holds user data (`Document`,
`CriteriaProfile`, `Job`) has an `owner` ForeignKey, and every API view
filters to `request.user`.

## App layout

```
pathfinder-job-copilot/
  backend/                 # Django project - API only, deploys to Railway
    manage.py
    config/                  # project settings, root urls (all /api/... + /admin/), wsgi/asgi
    accounts/                # User approval workflow: serializers.py/api_views.py/api_urls.py, admin.py
    portfolio/               # Document model - CV/cert/project library + API
    jobsearch/               # CriteriaProfile, ThresholdRow, Job, SponsorRegisterEntry models
      integrations/
        base.py               # ExternalJob dataclass + JobIntegration protocol
        adzuna.py              # Adzuna API client
        reed.py                 # Reed API client (UK only)
        jsearch.py               # JSearch API client (aggregates Google for Jobs)
      management/commands/
        sync_sponsor_register.py    # downloads the gov.uk sponsor register CSV
        check_sponsors.py            # re-checks existing jobs against it
        purge_bad_jsearch_jobs.py     # one-off cleanup, see "Fixed along the way"
      services.py              # run_search() / save_results() / evaluate_threshold()
      sponsor_register.py      # company-name matching against the register
      serializers.py, api_views.py, api_urls.py   # REST API for this app
    aiassist/                # GeneratedDraft model + Anthropic-backed service.py
      service.py               # tailor_cv() / draft_cover_letter() / answer_question()
      serializers.py, api_views.py, api_urls.py
    requirements.txt
    .env.example
    .gitignore
  frontend/                # React app (Vite) - the only UI, deploys to Vercel
    src/
      api.js                # fetch wrapper + all API calls
      AuthContext.jsx        # login/signup/logout + current-user state
      App.jsx                 # routes
      pages/                   # JobsPage, CriteriaListPage, CriteriaDetailPage,
                                # PortfolioPage, AiAssistPage, LoginPage, SignupPage,
                                # ApprovalsPage (staff only - approve pending signups)
      components/               # NavBar, ProtectedRoute, StaffRoute
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

### Backend (Django API)

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

`createsuperuser` gives you an account that's active immediately and can
log into `/admin/` - use it to approve everyone else's signups (see
"Admin-approved signups" below). Job search needs at least one of Adzuna,
Reed, or JSearch credentials (all free tier); AI features need
`ANTHROPIC_API_KEY`.

### Frontend (React - the UI)

In a second terminal, with the backend above still running:

```bash
cd pathfinder-job-copilot/frontend
npm install
cp .env.example .env    # VITE_API_BASE_URL, defaults to http://localhost:8000/api
npm run dev
```

Visit `http://localhost:5173` and sign up there. New accounts start
inactive - see "Admin-approved signups" below for how to approve them
before they can log in.

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

New accounts are created with `is_active=False` and can't log in until an
admin approves them. Two ways to approve someone, same underlying flag:

1. **In the app** (recommended) - log in with a staff account, an
   "Approvals" link appears in the nav (`frontend/src/pages/ApprovalsPage.jsx`,
   backed by `GET/POST /api/auth/pending-users/...`, both gated by DRF's
   `IsAdminUser` - i.e. `is_staff`).
2. **In `/admin/`** - Authentication and Authorization > Users, tick
   "Active" on their row, click Save. Works even if the React app is down.

The API's login endpoint tells a pending user their account needs
approval, rather than a generic "invalid credentials" message - this
needs `AUTHENTICATION_BACKENDS` set to `AllowAllUsersModelBackend` in
`settings.py` (already done), since the default backend silently treats
inactive users the same as a wrong password. Your own superuser account
(via `createsuperuser`) is active and staff immediately, unaffected by
any of this. To promote an existing regular account to staff/superuser
instead of creating a new one:

```bash
python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.get(username='YOUR_USERNAME'); u.is_superuser = True; u.is_staff = True; u.is_active = True; u.save()"
```

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
  API), auto-apply, password reset email, production deployment (Vercel +
  Railway config, `CORS_ALLOWED_ORIGINS` still only has localhost).
- **Frontend**: React is the only UI now, running and tested against the
  live API - auth (incl. admin approval), job tracker with filters,
  criteria + going-rate table CRUD, portfolio CRUD, AI actions. Styled
  plainly, no polish pass done yet.

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

**Template UI removed** (`backend/{accounts,portfolio,jobsearch,aiassist}/{forms,views,urls}.py`,
each app's `templates/`, project-level `templates/` and `static/`) once
the React app reached full feature parity, including admin approvals -
see the "Stack, and why" section above. `config/urls.py` and
`config/settings.py` no longer reference any of it (`django_htmx`,
`STATICFILES_DIRS`, `LOGIN_URL`/etc. all removed). Each app's `models.py`,
`admin.py`, `migrations/`, and `serializers.py`/`api_views.py`/`api_urls.py`
are unaffected - that's all shared/API code, not template-only.

## Roadmap

- v1 (this): manual pipeline end-to-end, single-user-per-login, sqlite by default, sponsor-register cross-check, admin-approved signups, React as the single API-backed UI
- v1.1: deploy - `frontend/` to Vercel, `backend/` to Railway with Postgres (`DATABASE_URL`), update `CORS_ALLOWED_ORIGINS` to the real Vercel domain
- v1.2: password reset email
- v1.3: scheduled/automatic re-sync of the sponsor register (currently manual)
- v1.4: additional job sources as APIs become available
- v2: auto-apply on user-approved jobs above a confidence threshold (deliberately out of scope until tailoring quality is proven out)
