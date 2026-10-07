# StudyFlow Planner handoff

Base stages 01–08 and adaptive-review stages R1–R6 are implemented and **verified locally against the listed checks** on 2026-10-07. No mandatory blocker remains. This is an agent-assisted implementation; see AI_ASSISTANCE.md, PROGRESS.md and REVIEW.md for provenance and fixes.

## Launch

The project already has an installed `.venv` and a migrated default database. Schema upgrades preserve existing data; reviews default off for existing targets. From the StudyFlow folder:

```sh
.venv/bin/python -m flask --app studyflow db upgrade
.venv/bin/python -m flask --app studyflow run --host 127.0.0.1 --port 5001
```

Open **http://127.0.0.1:5001**, register and begin. The app is ready for manual inputs; it does not need demo records, files, keys, models or external account connections. Stop with Ctrl-C. For a new installation, follow README.md's Python 3.14 environment/install/`db upgrade` sequence.

## Five-minute first use

1. **Account and subject:** register with an email/password (10+ characters) and timezone such as Asia/Hong_Kong. Add your own subject; HL/SL is optional.
2. **A practical goal:** add pasted teacher feedback, then “Create target from this feedback”, or create a target directly. Enter topic/skill and a clear activity. Starting need can be unknown; the default budget is 60 minutes.
3. **Time and deadlines:** optionally add/link an exam. In Settings, enter weekly minutes and date exceptions. A zero override means no capacity that date; the exam day itself is not a study day.
4. **Practice:** generate the Study Plan. Open today's block, start/pause/resume/finish, and optionally report an outcome or target-specific task marks. Completing without an outcome does not change reported need. Refresh is safe and retains valid IDs.
5. **Adjust:** inspect Progress for measured active time, credited work, remaining practice and source-labelled outcomes. Mark missed/skip when needed or change availability/deadlines; future work repairs with explanations. Locked/active/paused/completed commitments remain protected. Add 30 minutes explicitly if you want more practice.

6. **Optional follow-up reviews:** on the target card, enable reviews to authorize ongoing
   30-minute tasks beyond its finite initial budget. Rated completed practice determines
   the next 1/3/7/14/30-day recommendation; the same greedy planner places it on/after
   that date. Recommended and scheduled dates are distinct. A review completed without
   an outcome pauses recurrence. To enter an outcome later, select its completed session
   on the evidence form; corrections replay history. Disable reviews to cancel mutable
   unstarted bookings; protected active/locked work remains visible.

If work cannot fit, it stays visible as unallocated. Expired targets need an updated deadline. If a protected commitment conflicts with reduced capacity, the conflict stays visible. Unfinished active sessions survive date changes; past planned blocks are reconciled as missed on the next visit, with no daemon.

## Scope delivered

Secure local accounts, ownership/CSRF checks; subjects, feedback notes, exams and practice goals; weekly/date capacity; source-labelled ratings and corrections; inspectable priority formulas; finite seven-day allocation; transactional bounded repair, audit/replacement history and stable retries; pause-aware actual timing; dashboard/progress and private optional PDFs; migrations, synthetic seed command, tests and documentation. The extension adds opt-in per-target intervals, one pending review obligation, outcome/correction replay, shared greedy placement/repair, visible due/upcoming/delayed/awaiting/not-scheduled states, and separate review accounting. All static assets are local. Previous applications, student records and IA documents were left untouched.

## Exact verification commands and outcome

```sh
source .venv/bin/activate
PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers" python -m playwright install chromium
python scripts/check.py --all
```

Optional WebKit, also verified:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/.browsers" python -m playwright install webkit
python scripts/check.py --all --webkit
```

Final extension command `.venv/bin/python scripts/check.py --all --webkit` returned **0**:
lint passed, **91** unit/SQLite/HTTP/property tests, **8 Chromium** and **8 WebKit**
browser journeys passed. There were **0 failures and 0 skips**. All original tests remain
unchanged. The six original FIFO/oracle scenarios remain, including the FIFO-better case.
The complete dated review journey verifies 1 → 3 → 7 days, reset to 1, missed-task repair,
zero availability and stable reload/relogin/restart with real services/SQLite. A separate
normal production-clock Flask launch applies all seven migrations to fresh SQLite and
verifies manual onboarding, no-outcome completion, review opt-in/late outcome/shared
placement, seed/reconcile/schema/FK checks. An upgrade from a populated pre-extension
database also passes, retaining records and default-off review mode. All servers stopped.
See TEST_REPORT.md, ACCEPTANCE.md and evidence/verification-summary.json for actual logs,
commands and timings. `pip check` passed; no dependencies changed. Original Stage 08's
clean `.venv-repro` installation/freeze verification remains recorded separately.

The optional demo command is `python -m flask --app studyflow seed-demo --date 2026-10-07`; it prompts for a password and creates clearly synthetic records with relative dates. Choose a suitable seed date when running later. It refuses to overwrite an account. Explicit reconciliation: `python -m flask --app studyflow reconcile --email your-email@example.com`.

## Screenshots and engineering notes

- [Dashboard desktop](evidence/dashboard-chromium-desktop.png), [targets desktop](evidence/targets-chromium-desktop.png), [plan mobile](evidence/plan-chromium-mobile.png), [progress mobile](evidence/progress-chromium-mobile.png), [settings desktop](evidence/settings-chromium-desktop.png), [session desktop](evidence/session-chromium-desktop.png).
- [Dated review loop desktop](evidence/review-loop-chromium-desktop.png), [review loop mobile](evidence/review-loop-chromium-mobile.png), [fresh production review](evidence/fresh-production-review.png).
- [Full acceptance workflow](evidence/workflow-chromium.png) and [fresh normal-server workflow](evidence/fresh-production-workflow.png). Corresponding WebKit and additional desktop/mobile captures are in evidence/.
- ALGORITHMS.md explains formulas, worked examples, pseudocode, bounds and trade-offs. DATA_MODEL.md explains owner relationships/accounting. EVALUATION.md retains the FIFO-better tiny case. TEST_REPORT.md contains actual results/environment. Screenshots were visually inspected, including the fresh release conflict/repair state.

## Remaining limitations

No known core blocker remains. The scheduler is a greedy heuristic, not an optimiser; the tiny oracle shows one 30-minute allocation gap. Planning need/priority weights and review intervals are engineering heuristics, not ability percentages, validated memory models or learning-effectiveness claims. Interval growth does not prove mastery. Valid later bookings remain stable and are labelled delayed. Recommendations beyond the horizon/deadline are retained; only the next observed review is generated. History scans suit a small local application. The app plans local dates rather than clock-time or external calendar appointments and reconciles on visits rather than in the background. PDFs receive basic type/size/header/end checks and private downloads, not sanitization or automatic analysis. Replaced files are retained locally. The Flask development server is for localhost; public hosting was not evaluated. Other browsers/operating systems, formal accessibility, human usability and learning outcomes were not tested or claimed.

Persistent data and the generated secret are in ignored instance/. Keep database, uploads and secret together when backing up a stopped app. Normal startup and test commands never reset a user's database. Agent-assisted engineering records are not fabricated IA reflections or evidence of independent student authorship.
