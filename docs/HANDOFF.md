# StudyFlow handoff — 2026-10-07 (Hong Kong)

Original stages 01–08, adaptive reviews R1–R6 and the approved Today-first redesign
U1–U6 are implemented and verified locally against the checks below. No mandatory
blocker remains. This is agent-assisted implementation, not an IA reflection or a
claim of independently authored student work; see AI_ASSISTANCE.md and PROGRESS.md.

## Launch

From the StudyFlow directory, using the installed environment:

```sh
.venv/bin/python -m flask --app studyflow db upgrade
.venv/bin/python -m flask --app studyflow run --host 127.0.0.1 --port 5001
```

Open **http://127.0.0.1:5001**. Stop with Ctrl-C. Restart an existing server to load
the changed Python routes, then refresh the browser. The UI introduces no new schema
or dependency. Existing data remains usable; no database reset or reseed is required.
For a new installation, follow README.md's Python 3.14/install/migrate commands.

## First use and redesigned navigation

1. **Today** guides first use: add a subject, add a study goal, set study time, create
   the plan. It then presents one next action, **Start practice**. Unfinished sessions
   take precedence; waiting initial practice and review work remain visible.
2. **Subjects → Open subject** holds its goals, teacher feedback and exams. Enter a
   goal directly or choose **Create goal from this feedback**. Original comments have
   a short verbatim preview and expandable full text. Initial practice defaults to
   60 minutes; starting need, exam, supporting feedback, PDF and last date are optional.
3. **Settings** contains weekly minutes, date exceptions and timezone. Zero is valid.
   An exception replaces that date's usual time. Only complete 30-minute blocks fit.
4. **Plan → Plan my week** saves real greedy allocations. Seven date links jump to
   their day; session reasons and recent changes expand on demand. Waiting work has
   goal/time links. Protected-session conflicts remain explicit. The plan assigns
   dates, without clock-time appointments.
5. **Start → Focus → Finish** supports pause/resume and saved elapsed time. **Finish
   practice** opens **How did it go?** Choose an explicit outcome or **Finish without
   a rating** to save completion. Opening/backing out of this check-in does not finish
   or rate practice; active time continues until the final choice unless paused.
   Optional marks/context are expandable. **Session options** contains miss, skip,
   lock/unlock and move controls.
6. **Progress** separates completed initial allocations, actual active time and ongoing
   review work. Outcomes retain their source. **Add 30 minutes of practice** explicitly
   increases initial work. Workload/priority details and review controls expand on demand.
7. **Follow-up reviews** are optional on each goal. Enabling them authorizes ongoing
   30-minute tasks separate from initial practice. Rated actual completed practice
   determines the next 1/3/7/14/30-day recommendation; the existing scheduler places it
   on or after that date. Unrated review completion pauses recurrence. Add a late
   outcome through **Record practice outcome → Completed session**; corrections replay
   history. Disabling cancels mutable unstarted reviews; protected work stays visible.

Desktop uses a sidebar; mobile uses four main destinations and a Settings icon.
Native links, forms and expandable details work without JavaScript. The existing
local timer script updates the elapsed display. The existing /targets URL still
opens all study goals; new /subjects and owned /subject/<id> pages provide grouping.

## Exact verification and actual results

```sh
.venv/bin/python scripts/check.py --all --webkit
```

Returned **0** after the final application changes:

| Check | Actual result |
|---|---|
| Ruff lint | Passed |
| Unit / real SQLite / HTTP / seeded Hypothesis | 97 passed, 10 browser tests deselected |
| Chromium | 10 passed, 97 non-browser tests deselected |
| WebKit | 10 passed, 97 non-browser tests deselected |
| FIFO / tiny exhaustive oracle | All six scenarios retained; FIFO-better 30-minute gap remains |
| Fresh normal Flask server | All seven migrations, manual no-demo inputs, unrated finish, late outcome, reviews, shared allocation, seed/reconcile/schema/FK checks passed |
| Populated existing-schema upgrade | Automated SQLite migration tests passed; existing records/time/budgets retained and reviews default off |

Zero failures or skips in final verification. Complementary marker groups explain
all deselections. Existing journeys retain their behavioral assertions; selectors
and copy assertions were deliberately updated for approved labels and navigation.
New checks cover Today-led setup, keyboard activation, direct start/resume, check-in
back navigation, no inferred outcome, zero-capacity state, waiting reviews, subject
ownership and preserved invalid-form context. Main journeys use real services/SQLite.
Every main screen was checked at 1440px, 375px and 320px; screenshots were visually
inspected. Test servers and browsers were explicitly closed.

Additional final checks: `git diff --check` passed; `.venv/bin/python -m pip check`
reported no broken requirements (non-blocking pip cache-permission warning).
Read-only development DB check: head ff0452cc31b6, two accounts, zero FK violations.
Core services, auth, models, migrations, dependencies and the independent benchmark
are unchanged from the pre-UI commit. No IA write-up was changed.

Use `.venv/bin/python scripts/check.py` for lint/non-browser/evaluation checks, or
`.venv/bin/python scripts/fresh_setup.py` for the normal CLI/browser launch alone.
For isolated browser installation commands, see README.md. Logs and exact command/
exit/timing metadata: evidence/verification-summary.json. Baseline logs before UI
changes: evidence/ui-baseline-*.log; source audit: evidence/source-manifest-ui.txt.

## Screenshots

- [Today desktop](evidence/today-chromium-desktop.png) and [320px mobile](evidence/today-chromium-mobile.png).
- [Subjects](evidence/subjects-chromium-desktop.png) and [subject mobile](evidence/subject-chromium-mobile.png).
- [Focus](evidence/focus-chromium-mobile.png) and [optional finish check-in](evidence/finish-chromium-mobile.png).
- [Plan desktop](evidence/plan-chromium-desktop.png), [Progress mobile](evidence/progress-chromium-mobile.png), [Settings mobile](evidence/settings-webkit-mobile.png).
- [Real review loop](evidence/review-loop-chromium-desktop.png) and [fresh production workflow](evidence/fresh-production-review.png).

Corresponding WebKit and other viewport captures are in evidence/. Fixtures are synthetic.

## Limits and maintenance

This is the first implementation of the approved visual direction; human usability,
formal accessibility and learning outcomes have not been evaluated. The interface
currently uses the light theme. Date links jump within the full seven-day plan; this
is not a clock-time calendar or drag-and-drop planner.

The deterministic greedy scheduler and review intervals remain planning heuristics,
not optimality, mastery or validated retention measures. Valid later bookings stay
stable and show their delay. Recommendations beyond the horizon/deadline remain
visible. The app reconciles past plans on visits, without a background daemon.
PDFs are private reference downloads with basic type/size/header/end checks, without
sanitization, parsing or marking. Replaced files are retained locally. The Flask
server is for localhost; public deployment has not been evaluated. No external
calendar, OCR, LLM, generated quiz or notification service was introduced.

Optional synthetic seed:

```sh
.venv/bin/python -m flask --app studyflow seed-demo --date 2026-10-07
```

It prompts for a password and refuses to overwrite an account; select a suitable date
when running later. Explicit reconciliation:
`.venv/bin/python -m flask --app studyflow reconcile --email your-email@example.com`.

Persistent data, uploads and local secret are in ignored instance/. Back them up
together while the app is stopped. Tests never reset the user's database.
