# StudyFlow Planner

A local Flask application that turns manually entered teacher feedback and source-labelled practice outcomes into finite study targets, a seven-day plan, stable repairs when plans change, and opt-in outcome-based follow-up reviews. It records work and reported practice difficulty; it does not mark assessments or measure mastery.

## Install and launch

Verified on Python **3.14.7**, macOS arm64, Flask **3.1.3**, SQLAlchemy **2.1.3**, Playwright **1.63.0**. All Python dependencies, including test tools, are pinned in `requirements.txt`.

```sh
cd '/Users/daisychen/Desktop/CS projects/StudyFlow'
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app studyflow db upgrade
python -m flask --app studyflow run --host 127.0.0.1 --port 5001
```

Open **http://127.0.0.1:5001**. Create your own account and choose an IANA timezone. No API keys, model downloads, external accounts or demo records are required. Dependencies and test browsers need a one-time download; app runtime uses local assets and SQLite. Stop the server with Ctrl-C. Choose another localhost port if 5001 is occupied.

## First use without demo data

1. Create an account, then add a subject in **Feedback & Targets**. HL/SL is optional.
2. Paste teacher comments into a feedback note, or create a target directly. Describe a topic/skill and a practical goal. Unknown starting need is valid. A target defaults to 60 practice minutes.
3. Add an exam and link the relevant targets if useful. Practice ends one local day before an exam. Otherwise an optional last-study date applies.
4. Set **Settings** weekly capacity and date overrides. Zero is valid; an override replaces the usual day. Only complete 30-minute blocks fit.
5. Open **Study Plan** and generate it. Open a today's block to start/pause/resume/finish/skip. An outcome and target-specific task marks are optional. Finishing without an outcome provides no ability evidence.
6. Review **Progress**. Completion uses finite requested budgets; actual active time is separate. Add practice explicitly when useful. Genuine input/evidence changes repair future work and explain significant changes; completed/active/paused/locked work stays protected.

7. Optionally enable **Follow-up reviews** on a target card. This authorizes ongoing
   30-minute review tasks in addition to its finite budget. Explicit completed-session
   outcomes determine the next 1/3/7/14/30-day interval; the same greedy planner places
   it on/after the recommended date. A missing review outcome pauses recurrence. Use
   **Record practice outcome → Completed session** for a late rating; corrections replay
   existing outcomes. Reviews default off for all existing targets.

For an existing installation, stop the app and run `python -m flask --app studyflow db upgrade`
before relaunching. This preserves existing records and adds the review schema.

Overdue targets need a revised deadline before automatic placement. A locked or completed commitment can conflict with reduced capacity; the app displays the conflict rather than silently moving it. Past planned blocks become missed on the next authenticated visit. Unfinished active/paused blocks remain visible. There is no background daemon.

## Optional synthetic example

Create a separate synthetic Maths/Economics account explicitly:

```sh
python -m flask --app studyflow seed-demo --date 2026-10-06
```

The command prompts for a password of at least 10 characters. Default email is `demo@example.test`; `--email` can change it. Dates are relative to the supplied seed date: exams are ten days later, with three 60-minute targets and 60 minutes daily capacity. Choose a suitable current date when running later. The command refuses to overwrite an existing account; startup never seeds.

## Verification

Install isolated test browsers inside the project, keeping installed system browsers untouched:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers" python -m playwright install chromium
python scripts/check.py --all
```

The single command runs lint (including migrations), all unit/SQLite/HTTP/Hypothesis tests, a test-only FIFO/exhaustive comparison, mandatory Chromium workflows, and a fresh normal Flask CLI launch/onboarding/review/seed smoke. Review unit, SQLite, randomized and dated browser tests are included through normal test discovery; command/exit/timing metadata is saved in `docs/evidence/verification-summary.json`. It returns nonzero on any failure, writes separate logs under `docs/evidence`, and stops test servers. Tests use separate databases/uploads and synthetic records; they never reset your database. Pytest deselected counts separate browser and non-browser groups and are not skipped tests.

Optional WebKit verification, also executed during this build:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers" python -m playwright install webkit
python scripts/check.py --all --webkit
```

To run the fresh production-launch check alone: `python scripts/fresh_setup.py`. It creates a temporary database, exercises manual inputs and practice through Chromium, performs opt-in synthetic seeding, checks foreign keys and tears down. A clean second virtual environment (`.venv-repro`) was used to reproduce all pinned packages and run release verification separately from the fresh-database check.

## Configuration and stored data

Default data lives in ignored `instance/`: `studyflow.sqlite`, generated local `secret` (owner-only file permissions), and private `uploads/`. Normal startup never deletes records. `STUDYFLOW_DATABASE=sqlite:////absolute/path/fresh.sqlite` selects another database; run `db upgrade` with the same variable before serving it. The application factory accepts a Python configuration mapping for test databases/upload folders/clocks; there is no production time-travel endpoint.

To reconcile an account explicitly without visiting it:

```sh
python -m flask --app studyflow reconcile --email your-email@example.com
```

Use `db upgrade` for schema updates and `db check` to check model/migration drift. Stop the app before backing up the database, secret and uploads together. Keep the secret to preserve existing login sessions. Runtime is intended for localhost; the Flask development server, local HTTP cookies and current controls have not been evaluated for public hosting.

## Limits and engineering evidence

The scheduler is a bounded greedy heuristic, not an optimiser: a tiny documented case lets FIFO place 30 more minutes. Priorities and review intervals use configurable planning heuristics, not validated ability or retention measures. A growing interval does not prove mastery; due beyond a horizon/deadline remains visible. Valid later bookings stay stable and are labelled delayed. Planning covers dates rather than external calendar appointments. PDFs are optional private references (4 MB limit), checked for type/size/header/end marker and downloaded as attachments; they are not sanitized, parsed, graded or OCR-processed. Replaced PDFs are retained locally. No OCR, LLM, generated quiz, Google OAuth, notification, hosted deployment or background service is included.

Automated checks establish the listed software behaviour, not human usability, formal accessibility compliance or learning gains. See [handoff](docs/HANDOFF.md), [stage evidence](docs/PROGRESS.md), [acceptance map](docs/ACCEPTANCE.md), [algorithms](docs/ALGORITHMS.md), [data model](docs/DATA_MODEL.md), [comparison](docs/EVALUATION.md), [agent review](docs/REVIEW.md) and [AI assistance record](docs/AI_ASSISTANCE.md).
