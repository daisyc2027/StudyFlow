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

1. Create an account. **Today** guides you through a subject, a study goal and available study time. HL/SL is optional; a goal defaults to 60 minutes of initial practice.
2. Use **Subjects → Open subject** for its goals, original teacher feedback and exams. Create a goal directly or choose **Create goal from this feedback**. Starting need can remain unknown. Read the full original comments under **Read original feedback**.
3. In **Settings**, enter weekly minutes and any date exceptions. Zero means no study that day. Optionally link an exam to a goal; practice ends one local day before the exam. Only complete 30-minute blocks fit.
4. Choose **Plan my week** in **Plan**, or **Create my plan** in Today's setup. The seven date links jump to each day's sessions. Edit study time or check goal deadlines if work is waiting; explanations and plan history expand on demand.
5. From **Today**, choose **Start practice**, then pause/resume as needed. **Finish practice** opens an optional check-in: choose an outcome or **Finish without a rating**. The final choice saves completion; the check-in itself doesn't complete a session. Active time continues until completion unless paused. **Session options** contains miss, skip, lock and move controls.
6. **Progress** separates initial practice completion, measured active time and recurring reviews. Add 30 minutes explicitly when needed. Finishing without a rating creates no ability evidence. Genuine changes repair future work; completed, active, paused and locked sessions stay protected.
7. Optionally **Enable follow-up reviews** on a goal. These are ongoing 30-minute tasks separate from initial practice. Explicit completed-session outcomes determine the next 1/3/7/14/30-day interval; the existing greedy scheduler places it on or after that date. For a late rating, use **Record practice outcome → Completed session**. Review controls are also under **Progress → Review options**. Reviews default off.

The UI redesign needs no new migration or dependency. For an existing installation, stop the app and run `python -m flask --app studyflow db upgrade`
before relaunching. This preserves existing records and adds the review schema.

Overdue targets need a revised deadline before automatic placement. A locked or completed commitment can conflict with reduced capacity; the app displays the conflict rather than silently moving it. Past planned blocks become missed on the next authenticated visit. Unfinished active/paused blocks remain visible. There is no background daemon.

## Optional synthetic example

Create a separate synthetic Maths/Economics account explicitly:

```sh
python -m flask --app studyflow seed-demo --date 2026-10-07
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
