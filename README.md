# Pathfinder Job Copilot (v1 - Django)

A personal job-search web app: define selectable search criteria (not
hardcoded to any one title/country), pull matching postings from Adzuna
and Reed, screen them against an editable occupation going-rate table
(useful for visa sponsorship eligibility, but works for anyone), build a
portfolio of CVs/certs/project write-ups, and generate tailored CVs,
cover letters, and application Q&A answers grounded only in the portfolio
documents you select. Every user has their own login and their own data.

## Stack, and why

Single Django project, server-rendered templates + [HTMX](https://htmx.org)
for interactivity - no separate frontend framework/build step. Django
renders HTML directly from Python; HTMX attributes (`hx-post`, `hx-target`)
let specific parts of a page update via small server round-trips without a
full reload or a JSON API layer in between. One language, one deployable
process, matches the stack you already know (Django/Python/BCS Full-Stack).

Auth is Django's built-in session-based auth (`django.contrib.auth`) -
every model that holds user data (`Document`, `CriteriaProfile`, `Job`)
has an `owner` ForeignKey, and views are wrapped with `@login_required`.

## App layout

```
pathfinder-job-copilot/
  manage.py
  config/                  # project settings, root urls, wsgi/asgi
  accounts/                # login, signup (Django auth)
  portfolio/               # Document model - CV/cert/project library
  jobsearch/               # CriteriaProfile, ThresholdRow, Job models
    integrations/
      base.py               # ExternalJob dataclass + JobIntegration protocol
      adzuna.py              # Adzuna API client
      reed.py                 # Reed API client (UK only)
    services.py              # run_search() / save_results() / evaluate_threshold()
  aiassist/                # GeneratedDraft model + Anthropic-backed service.py
    service.py               # tailor_cv() / draft_cover_letter() / answer_question()
  templates/base.html      # shared layout + nav + HTMX script tag
  static/css/style.css
  requirements.txt
  .env.example
```

### Data model summary

- `jobsearch.CriteriaProfile` - a saved search: keywords (comma-separated,
  editable), location, country code, job type, and salary mode (either a
  flat minimum or the going-rate table below). You can have several.
- `jobsearch.ThresholdRow` - one row of an occupation going-rate table
  scoped to a profile (keyword match, occupation code, threshold amount,
  currency, verified flag). Not UK-specific - edit the rows for any
  country's system.
- `jobsearch.Job` - a posting pulled in by search (or added manually),
  with `status` (new → interested → tailoring → applied → interviewing →
  offer/rejected), `sponsor_status` (unknown/likely/confirmed/no, set
  manually - no source exposes this programmatically), and
  `threshold_pass` (computed against the matched profile).
- `portfolio.Document` - CV/certificate/project text you paste or upload;
  tagged and typed, feeds the AI layer.
- `aiassist.GeneratedDraft` - a saved AI output (CV, cover letter, or Q&A
  answer) tied to a job, recording exactly which `Document`s it was
  grounded in.

## Setup

```bash
cd pathfinder-job-copilot
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env           # fill in ANTHROPIC_API_KEY, ADZUNA_*/REED_API_KEY
python manage.py makemigrations accounts portfolio jobsearch aiassist
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/accounts/signup/` to create your account, or
`/admin/` with the superuser to manage data directly. Job search needs at
least one of Adzuna or Reed credentials (both free tier); AI features
need `ANTHROPIC_API_KEY`.

## What's genuinely working vs. what's a stub

- **Working end-to-end**: signup/login, portfolio document CRUD, criteria
  profile + going-rate table CRUD, Adzuna/Reed search wired to real APIs,
  job tracker with status/sponsor updates, AI tailoring/cover
  letter/Q&A wired to the Anthropic API and grounded in selected documents.
- **Manual by design (v1)**: sponsor-licence status is a dropdown you set
  yourself - no API exposes this, so automating it would mean scraping a
  government register, deliberately left out of v1.
- **Not built yet**: automated sponsor-licence lookup, LinkedIn/company
  career-page sources (no public API), auto-apply, password reset email,
  deployment config.

## Housekeeping

This folder also has a `src/`, `tests/`, `data/`, and old root-level
`requirements.txt`/`pyproject.toml` left over from an earlier
standalone-CLI prototype that predates the decision to build this as a
Django web app. They're unrelated to the app above and safe to delete
(`src/`, `tests/`, `data/`, `pyproject.toml`) - I couldn't remove them
from this session because the shell tool is currently broken by a stale
WSL folder reference; delete them manually via File Explorer whenever
convenient.

## Roadmap

- v1 (this): manual pipeline end-to-end, single-user-per-login, sqlite by default
- v1.1: password reset email, deploy to Railway/Render with Postgres
- v1.2: automated sponsor-licence cross-check against a licensed-sponsor register
- v1.3: additional job sources as APIs become available
- v2: auto-apply on user-approved jobs above a confidence threshold (deliberately out of scope until tailoring quality is proven out)
