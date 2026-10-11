# Execution progress

## Current state
Base stages 01–08 and review extension R1–R6 COMPLETE — verified locally on 2026-10-07 (Hong Kong).

| Stage | Status | Gate evidence |
|---|---|---|
| 01 Foundation | PASSED | Auth/health/CSRF, migrated schema and Chromium smoke |
| 02 Inputs | PASSED | Real input/browser workflows, isolation, restart, seed |
| 03 Evidence/priority | PASSED | Independent formulas/corrections and randomized bounds |
| 04 Scheduler | PASSED | Finite-budget/capacity/deadline invariants, stable IDs |
| 05 Adaptation | PASSED | Lifecycle/timing/repair, rollback, conflicts and browser loop |
| 06 Experience | PASSED | Progress/PDF security, all main screens, mobile and visual QA |
| 07 Acceptance | PASSED | 57 tests, 6 Chromium + 6 WebKit, baseline/oracle, review |
| 08 Release | PASSED | Exact clean dependency reproduction; normal fresh DB/run/seed; final full checks; HANDOFF.md |

No mandatory blocker, skip or unexecuted check remains. Original and extension results, including genuine development failures and fixes, are preserved below.

## Stage 01 — Foundation (2026-10-06, Hong Kong)
Plan: establish an isolated Python app, secure accounts, migration tooling, real SQLite/HTTP tests and a Chromium smoke test. Expected outcome: a new account can reach a persistent local dashboard.

Implemented: `studyflow/__init__.py`, `auth.py`, `models.py`, templates/static assets; `tests/conftest.py`, `test_auth.py`, `test_browser.py`; `scripts/check.py`; initial Alembic migration.

Executed:
- `/opt/homebrew/bin/python3 -m venv .venv` — Python 3.14.7.
- Project dependency installation — completed after sandbox DNS restriction required an approved network execution. `requirements.txt` records installed versions.
- `python -m flask --app studyflow db init`, `db migrate -m foundation`, `db upgrade` — passed.
- `.venv/bin/python scripts/check.py` — lint passed; 2 HTTP/database tests passed.
- Isolated Playwright browser download underway; Chromium smoke test still pending. Gate not yet complete.

Decisions: copied only supplied brief into the empty project; local secret, no cloud integrations; fixed-clock isolated tests. See DECISIONS.md and AI_ASSISTANCE.md.

Stage 01 gate PASSED: `.venv/bin/python scripts/check.py --all` (approved localhost/browser execution after sandbox bind rejection) — lint clean, 4 database/HTTP tests and 1 Chromium register/logout/login test passed. `docs/evidence/foundation.png` captured. `pip check` reports no broken dependencies. Next: Stage 02.

## Stage 02 — Inputs
Plan: normalize owner-scoped records and enforce same-subject links; expose concise create/edit/archive forms, weekly capacity and zero-date overrides; provide an opt-in synthetic seed command. Gate: invalid/foreign inputs rejected, records survive restart, browser input workflow passes.

Stage 02 gate PASSED. `db migrate -m inputs` and `db upgrade` passed. `scripts/check.py --all` — lint clean, 12 HTTP/database tests and 2 Chromium tests passed; final seed addition verified with `scripts/check.py` — 13 HTTP/database tests passed. Browser failure exposed option text in implicit select labels; explicit accessible labels fixed it and the original assertion passes. Restart, archives, duplicate weekly-day upsert, invalid date/minutes, cross-owner and cross-subject links covered. `test_opt_in_seed` verifies synthetic relative-date seeding and refusal to overwrite. Scope reviewed: no automatic diagnosis or external connections. Next: Stage 03.

## Stage 03 — Evidence and priority
Plan: retain source-labelled target evidence and corrections with request identity; implement pure recency/priority functions and readable reasons; verify independent examples, monotonicity and randomized bounds. No completion-based ability inference.

Stage 03 gate PASSED: `db migrate -m evidence`, `db upgrade` passed (migration preserves earlier explicit starting reports). `scripts/check.py --all` — lint clean, 19 unit/SQLite/HTTP/property tests and 2 Chromium tests passed. Priority property test uses seed 20300107 / 150 examples. Independent averages, P=80, corrections/retries, source labels, future evidence, invalid marks, stale forms, unknown text/overall-grade handling all covered. Formulas documented in ALGORITHMS.md; source/identity constraints in models.py and evidence service. No completion signal enters the aggregation function. Next: Stage 04.

## Stage 04 — Initial scheduler
Plan: pure deterministic integer-block allocation, finite demand conservation and daily capacity/deadline enforcement; persist stable saved sessions and expose the seven-day plan with visible unallocated work. Verify A05 examples, randomized invariants and a real browser generation.

Stage 04 gate PASSED: sessions migration/upgrade passed. `scripts/check.py --all` — lint clean, 27 unit/HTTP/database/property tests and 3 Chromium tests passed. Scheduler seed 4042030 / 120 generated examples; zero/29/30/45/60 capacity, budgets/deadlines, stable ties, overdue work, outside-horizon reservations, completed capacity and duplicate generation verified. Browser generates from manually persisted targets with stable IDs and captures `initial-plan.png`. Review caught preview capacity/balance ambiguity before tests: GET now shows saved capacity and visible unallocated work; unsaved suggestions shown separately. Algorithm bounds and limitations documented. Next: Stage 05.

## Stage 05 — Lifecycle and adaptation
Plan: persist pause-aware actual timing, valid transitions, stable request identities and audit history; build a bounded pure repair pass with transactional persistence and protected-work conflicts; reconcile past planned blocks on authenticated visits; verify rollback, misses, deadlines, availability and evidence competition.

Stage 05 gate PASSED: final `scripts/check.py --all` — lint clean, 36 unit/SQLite/HTTP/property tests and 4 Chromium tests passed. Fresh browser workflow captured in `workflow-chromium.png`. Timing, duplicate actions, replacement chains, capacity conflicts, evidence competition, two-allocation cap, no-space work, stale state, locks, manual moves, overdue dates, next-visit reconciliation and injected transactional rollback covered in test_adaptation.py. Actual local completion-date waiting regression added. Migration initially failed on unnamed SQLite FK; named FK/check and existing-user default fixed it, verified only the newly created audit table was empty before removing that failed-DDL artifact, then upgrade passed. Browser evidence assertion originally matched a hidden option and history; scoped to history without weakening it. Mutation serialization and unchanged-fingerprint no-op documented. Next: Stage 06.

## Stage 06 — Experience and attachments
Plan: derive dashboard/progress from real records, define finite-budget completion separately from attempts and actual time, add optional private reference PDFs, improve onboarding/contextual actions and inspect desktop/mobile screens. Gate: arithmetic/attachment tests, browser navigation/empty states, overflow and console checks, screenshots visually inspected.

Stage 06 gate PASSED: final `scripts/check.py --all` — lint clean, 46 tests and 5 Chromium tests passed. Attachment ownership/type/size/raw path checks, forged stored paths and rollback cleanup covered. Report arithmetic proves missed/replacement history does not inflate completion; actual time and explicit add-practice tested. Full browser flow now visits Progress. All six major/session screens captured at 1440×1000 and 375×812; links checked, no horizontal overflow or fatal page errors. Visually inspected dashboard/targets/settings/session desktop and progress/plan mobile images with view_image; cards, forms and wrapping readable. Fixed real Jinja dictionary-method collision and raw multipart backslash validation; all original assertions retained. PDFs are type/size/header/end-marker checked and attachment-only downloads, not sanitized or diagnosed. No destructive record deletion is exposed. Next: Stage 07.

## Stage 07 — Adversarial acceptance and review
Plan: acceptance-to-test mapping; randomized generation/repair sequences including immutable conflicts and database idempotence; concurrent submissions and stale availability; test-only FIFO and tiny exhaustive oracle; review all routes/relationships/UI controls against scope; run unified Chromium checks and WebKit separately.

Stage 07 gate PASSED: final `scripts/check.py --all --webkit` — lint clean, 57 non-browser tests, 6 Chromium tests and 6 WebKit tests passed, no skips. Benchmark writes six deterministic scenarios to EVALUATION.md/JSON, including a FIFO-better 30-minute oracle gap and a protected-conflict case. Random repair seed 7072030 / 200 cases and database sequence seed 7172030 / 25 sequences passed; concurrent completion duplicates only one outcome/event. Populated-upgrade regression caught expression-default SQLite table recreation; literal defaults preserve foreign keys and retained records without disabling integrity. Wrong archive test expected the generic word “retained” absent despite the correct retention flash; replaced with a positive archived-target visibility assertion (not a product defect). Agent review added stale settings versions and idempotent archives. Deprecated migration engine access updated. ACCEPTANCE.md exact names checked against test definitions. Runtime-only-localhost request check passed. Major-screen screenshots also captured for WebKit. Next: Stage 08.

## Stage 08 — Release verification
Plan: separate clean-environment dependency reproduction from fresh-database migration/onboarding; execute normal Flask localhost launch and optional seed with isolated synthetic data; rerun all checks after final changes; finalize engineering/first-use/handoff records and stop test servers. No new features.


Stage 08 gate PASSED (2026-10-06, Hong Kong):
- `/opt/homebrew/bin/python3.14 -m venv .venv-repro`; `.venv-repro/bin/python -m pip install --no-cache-dir -r requirements.txt` — all 26 pinned packages installed in a clean environment.
- `.venv-repro/bin/python -m pip check` — no broken requirements; freeze/diff against requirements.txt — exact match. Environment recorded in evidence/environment.txt.
- `.venv-repro/bin/python scripts/check.py --all --webkit` — exit 0. Lint including migrations passed; 57 non-browser tests (10.71s), 6 Chromium tests (12.95s), 6 WebKit tests (12.52s) passed. Benchmark six scenarios passed. No mandatory skips (marker deselections are complementary groups).
- Unified fresh-launch smoke applied all six migrations to an empty temporary SQLite file, started normal Flask on 127.0.0.1, completed manual feedback/target/exam/capacity/plan/pause/finish/miss/repair/Progress/login flow, then stopped the server. Opt-in seed dated 2026-10-06, reconcile, schema check and FK check passed. No ability evidence inferred from unrated completion; budget stayed 60. Runtime requests stayed on localhost.
- Fresh release screenshot visually inspected: protected completed commitment conflict and replacement work remain clearly visible, with history and explanations.
- Default development database remains empty (0 users) with no FK violations. Copied product brief unchanged; 52 source/test/migration/assets files inventoried in source-manifest.txt. No previous project/student/IA files inspected or edited.
- README, HANDOFF, TEST_REPORT, ACCEPTANCE, DATA_MODEL, ALGORITHMS, EVALUATION, REVIEW, DECISIONS and AI_ASSISTANCE finalized. Test servers/browsers closed explicitly. No server left running as deployment. No features added during release.

Next action: user launches the local app with the command in HANDOFF.md and creates their own account. No further implementation stage is pending.

## Extension R1 — audit and define (2026-10-07, Hong Kong)
Plan: inspect actual models/services/routes/tests, run original unified verification,
and define separate review obligations integrated with existing greedy/repair.
Read extension prompt, AGENTS, product/domain/test contracts, plan and full progress.
Inspected models, evidence/lifecycle/planning/scheduler/repair/progress, routes/templates,
migrations and HTTP/browser tests. Identified changes are recorded in REVIEW_EXTENSION.md.
Baseline command: `.venv/bin/python scripts/check.py --all --webkit`; final result below.
R1 PASSED: baseline exit 0; lint clean, 57 non-browser tests, 6 Chromium and 6 WebKit
tests passed; six benchmark scenarios and normal fresh launch/migration/seed/schema checks
passed. No skips or known baseline failures. Baseline logs preserved as review-baseline-*.log.
Scope checked: existing allocator/repair/auth retained, no unrelated or IA changes.

## Extension R2 — pure interval engine
Plan: pure chronological replay using UTC completion and local days; configurable ladder,
last rated session per day, initial/bounds/no-outcome/correction/timezone tests.
R2 PASSED: targeted `python -m pytest -q tests/test_review_algorithm.py`: 3 passed.
`.venv/bin/python scripts/check.py`: lint clean, 60 non-browser tests passed, six benchmark
scenarios passed. Seed 7102030, 150 examples. Hand-calculated 1/3/7-day dates, help/reset,
initial state, daily winner/ties, supersession, timezone boundary and cap verified.
Scope checked: pure service only, no runtime dependency or base behavior changed.

## Extension R3 — persistence and separate obligations
Plan: owner-scoped ReviewState/ReviewTask/SessionReview, partial uniqueness, opt-in
transaction service, correction session linkage, completion/awaiting behavior and
separate progress accounting. Gate: real SQLite migration/ownership/uniqueness, duplicate
requests, rollback, enable/disable, correction replay and original regressions.
R3 PASSED: targeted review persistence: 3 passed; `.venv/bin/python scripts/check.py`: lint
clean, 63 non-browser tests passed, six original benchmark scenarios retained. `flask db
migrate -m review_obligations` and `db upgrade` passed. Fresh and populated-base upgrades
pass including foreign-key/schema checks; old targets remain off. Added linkage table
rather than rebuilding the referenced session table; composite links/indexes enforce
ownership, and partial index rejects duplicate pending tasks. SQLite tests verify
rollback, replay corrections, unrated review awaiting state and ordinary credit separation.
Scope checked: no copied performance history, budget unchanged, existing tests retained.

## Extension R4 — shared greedy placement and repair
Plan: add not-before and target balancing group to existing pure jobs; map review task
keys through shared snapshot/persistence/repair; preserve protected work, history and
fingerprints. Gate: mixed-job capacity/deadline/due/horizon invariants, stable refresh,
miss replacement, availability/deadline/locked conflicts and regression suite.
R4 PASSED: targeted persistence/scheduling tests: 6 passed. `.venv/bin/python
scripts/check.py --all --webkit`: lint clean, 66 non-browser + 6 Chromium + 6 WebKit
passed, six benchmark cases and fresh normal launch/migration/seed/schema checks passed.
Seed 7112030, 180 mixed-job scenarios checks shared capacity, distinct demand, due/deadline
limits, immutable conflict allowance and finite repair. Missed review preserves task ID,
replacement links and evidence count; locked disabled review remains a visible conflict
until unlocked. Scope checked: one allocator and repair service, no priority bonus or
budget growth. Next: integrated UI and review-specific browser coverage.

## Extension R5 — interface and analytics
Plan: opt-in target card with ongoing-work explanation; due/scheduled/status/reasons;
review labels in plan/session; separate review progress; optional three outcome buttons;
late completed-session evidence and replay history. Gate: HTTP auth/CSRF/stale/double
requests, no data/capacity/disable cases and real headless browser flow.
R5 PASSED: targeted HTTP tests 2 passed; `.venv/bin/python scripts/check.py --all
--webkit`: lint clean, 68 non-browser, 7 Chromium and 7 WebKit tests passed; benchmarks
and fresh normal launch passed. New real browser verifies opt-in/no data, outcome button,
correct date/reason, no-capacity state, separate progress and disable at mobile width.
review-ui-chromium.png visually inspected: readable wrapping, no overflow, distinct review
workload card. Outcome remains optional, source/history preserved. Scope checked: no new
diagnostic form, external service or educational claims.

## Extension R6 — complete adaptive-loop verification
Plan: fresh dated browser journey through 1/3/7/reset/miss/availability/reload; late and
corrected session outcomes, same-day/cap/teacher exclusions, active/paused/locked safety,
foreign links, transaction/concurrency failures and seeded database mutations. Extend
unified checks through automatic test discovery; verify fresh and populated upgrades,
retain FIFO/oracle, document actual results and limitations.
R6 development check: initial late-correction test expected an existing Jan 11 booking
to move earlier to Jan 10. Actual due recomputed to Jan 9 while the Jan 11 reservation
remained valid. The stable-repair contract explicitly preserves valid unaffected bookings;
corrected this newly written expectation to assert the SAME ID/date and visible delayed/
overdue labels. No existing assertion removed. Targeted loop checks rerun below.
R6 browser found an existing budget input label included its nested help text, so an
exact accessible-label lookup failed. Added explicit aria-label to the real input; kept
the exact browser assertion. Original browser workflows will rerun with this fix.
R6 substantive defect found and fixed: awaiting-outcome comparison used timestamp alone.
Two completions in the same stored second left recurrence paused even when a later stable
session ID had a genuine outcome. Comparison now uses (actual completion, session ID),
consistent with deterministic replay. The failing equal-timestamp HTTP regression is
retained. Dated Chromium loop also now passes (1 passed, 4 complementary deselections).
Final normal-server extension check initially failed a strict locator because both the
review reason and the due/scheduled paragraph contained the recommendation date. Actual
page had the correct reservation. Preserved failure log as review-fresh-locator-failure.log;
scoped assertion to the exact recommended AND scheduled date paragraph, retaining both
checks. Original no-outcome/finite-budget assertions moved before the newly added explicit
late outcome, and separate post-outcome review assertions added. Full suite rerun follows.
Source audit against original SHA256 manifest: no original tests or migrations, auth,
priority service, baseline/oracle script, CSS/JS or dependencies altered. Changes are
review services/models/routes/templates, shared job integration and verification tooling.
Review audit text now names the real topic/work type rather than an internal review job key.

R6 PASSED — final `.venv/bin/python scripts/check.py --all --webkit` returned 0:
- Lint: all checks passed.
- Unit/real SQLite/HTTP/Hypothesis: 91 passed, 8 browser tests deselected (17.52s).
- Chromium: 8 passed, 91 non-browser tests deselected (17.86s).
- WebKit: 8 passed, 91 non-browser tests deselected (17.78s).
- FIFO/tiny oracle: all six original scenarios retained; FIFO-better 30-minute gap remains.
- Normal fresh Flask launch: all seven migrations, manual no-demo workflow, opt-in reviews,
  unrated no-data state, late explicit outcome, real shared greedy review reservation,
  seed/reconcile/schema check/FK check all passed. Production clock local date 2026-10-07.
  Browser/server explicitly closed; no server left running.
- Fresh and populated-old-schema upgrades are also automated SQLite tests. Existing
  sessions/evidence/time/budgets retained; existing targets stay off until explicitly enabled.
- Review randomized seeds: 7102030 / 150 pure replay examples; 7112030 / 180 mixed-job
  generation/repair examples; 7122030…7122041 / 12 isolated SQLite sequences × 8 daily
  mutations. Original seeds/settings unchanged. No generated failure remains unresolved.
- Required dated browser loop ran with real UI/services/SQLite in both engines: register,
  two subjects/targets, deadline/capacity, one opt-in target, ordinary outcome, 1 → 3 → 7,
  reset to 1, missed SAME task, availability zero, repeat generation/reload/relogin/restart.
  Ordinary budget stayed 60 total; 90 review minutes completed and 30 review minutes
  outstanding; four explicit source outcomes and four review tasks, with no duplicate debt.
- Additional tests cover completion without outcome, late/corrected and same-day outcomes,
  all transitions/cap, actual timezone boundary, teacher/general exclusions, no exam,
  deadline-before-due, future horizon, locks/active/paused/disabled/archive, cross-user and
  cross-target links, equal timestamps, transaction rollback AFTER real placement and
  concurrent ordinary/review completions. No core mock in the main journeys.
- `python -m pip check`: no broken requirements. No dependency added/changed; original
  clean-environment reproduction remains separately recorded in Stage 08.
- Desktop/mobile review screenshots visually inspected; no horizontal overflow/page errors.
  Final evidence/logs and command/exit/timing metadata are in docs/evidence.
- Architecture, algorithm/accounting, acceptance map, README, HANDOFF, TEST_REPORT,
  DECISIONS, REVIEW and honest AI-assistance records updated. No IA write-up changed.

| Extension stage | Final status |
|---|---|
| R1 Audit/contract | PASSED — original full baseline recorded |
| R2 Pure interval replay | PASSED — independent dates/transitions/invariants |
| R3 Persistence/accounting | PASSED — migration/uniqueness/ownership/rollback |
| R4 Greedy/repair integration | PASSED — mixed jobs/constraints/stability |
| R5 Interface/analytics | PASSED — routes/mobile/browser/optional outcomes |
| R6 Complete adaptive loop | PASSED — full regressions/fresh + existing upgrade |

No further implementation stage is pending. See HANDOFF.md for exact launch/verification
commands and heuristic/local-runtime limitations.

Final artifact checks: all six verification-summary entries exit 0; 63 source/test/asset
files hashed (original 52-file manifest preserved as source-manifest-base.txt); documentation
links valid; original test/auth/priority/oracle hashes unchanged. Default development DB
is at ff0452cc31b6, contains 1 user, and has no FK violations; no reset was performed.
`.venv/bin/python -m flask --app studyflow db check`: no schema drift. Visually inspected
fresh-production-review.png: ordinary/review blocks share 60-minute capacity tomorrow,
with the pre-existing completed-work conflict today shown honestly. No remaining blocker.

## UI redesign U1 — baseline and scope

User approved the Today-first discussion design and six-stage implementation plan.
Plan/acceptance gates: brief/UI_REDESIGN.md. Inspected AGENTS, domain/test contracts,
completed progress, actual Flask routes/templates, services and browser journeys.
Scope: presentation, read-only view queries and contextual navigation; preserve core
algorithms, persistence and accounting. Baseline verification follows before UI edits.

U1 PASSED: `.venv/bin/python scripts/check.py --all --webkit` exit 0; lint,
91 non-browser, 8 Chromium, 8 WebKit, six FIFO/oracle cases and fresh normal launch
passed. Copies retained in docs/evidence/ui-baseline-*.log and ui-baseline-summary.json.

## UI redesign U2 — foundation and Today
Plan: reusable local CSS/SVG shell, four destinations with current-page semantics,
responsive navigation, next real session with direct start/resume, unfinished-first
selection and persisted subject/goal/time setup steps. Acceptance: real HTTP setup and
unfinished checks, browser direct start/resume, desktop/320px and existing screen checks.
Tests use the new Today/Subjects/Plan navigation names; original action/accounting
assertions retained. No service, schema, dependency or learning-rule changes.
Targeted `.venv/bin/python -m pytest -q tests/test_ui.py -m 'not browser'`: 2 passed.

U2 PASSED: `scripts/check.py` lint clean, 93 non-browser tests and six benchmarks
passed. First regression found an old literal dashboard heading in test_auth; updated
it to assert the actual approved `<h1>Today</h1>`, keeping auth/CSRF assertions.
Chromium `pytest -q tests/test_ui.py tests/test_browser.py -m browser -k
'today_direct or auth or saved_plan or main_screens'`: 4 passed. Desktop and 320px
Today screenshots visually inspected. Diff scope: templates/CSS, read-only home query,
presentation tests/docs only; lifecycle/scheduler/database untouched.

## UI redesign U3 — subjects and setup
Plan: subjects overview → owned subject detail, contextual create/save navigation,
goal terminology and shorter forms, original feedback preview/full-text disclosure,
compact review controls. Keep /targets as an accessible all-goals view for existing
links. Acceptance: HTTP ownership/prefill/persistence, real input/upload/archive
browser paths and accumulated non-browser regressions. Review opt-in remains explicit.

U3 PASSED: targeted HTTP `pytest -q tests/test_ui.py tests/test_inputs.py
tests/test_experience.py tests/test_review_interface.py -m 'not browser'`: 24 passed.
Chromium `pytest -q tests/test_browser.py -m browser -k 'inputs or edit_evidence or
full_feedback or main_screens'`: 4 passed. `scripts/check.py`: lint, 94 non-browser
tests and six benchmarks passed. Visually inspected subject overview/detail mobile.
New subject/detail/prefill routes enforce ownership; original text is retained verbatim.
Browser journeys now navigate subject cards and open explicit options, retaining all
original persistence, correction, attachment, archive, lock and accounting assertions.
Scope reviewed: existing writes/repair still transactional; no data model changes.

## UI redesign U4 — focus and finish
Plan: focused elapsed timer, start/pause/resume, one Finish link to a server-rendered
optional check-in, three explicit outcomes or Finish without a rating. Session options
hold skip/miss/lock/move. GET check-in does not complete or rate; final POST remains
atomic through the original lifecycle service. Acceptance: invalid marks retain form,
unrated/rated completion, duplicate safety, timer refresh, real dated review journey.

U4 checks: targeted HTTP/lifecycle/review loop 20 passed; `scripts/check.py` lint,
95 non-browser tests and six benchmarks passed. First Chromium run: 8 passed, 1 failed
because a decorative arrow changed the exact Start practice accessible name. Marked
the arrow aria-hidden (kept the exact assertion). Full browser rerun follows.

U4 PASSED: full Chromium `pytest -q -m browser`: 9 passed. Added real browser
check-in/back/unrated completion checks with actual SQLite state, no inferred evidence
and unchanged 60-minute demand. Visually inspected 320px focus/check-in screenshots.
All original lifecycle, dated intervals, missing/replacement and atomicity checks pass.
Scope reviewed: lifecycle/evidence/review engines unchanged; GET only selects a view.

## UI redesign U5 — Plan, Progress and Settings
Plan: seven date jump links and compact session rows; short next actions for unplaced
work/conflicts; inspectable reasons/history. Progress leads with initial work and actual
time, separate recurring work, details on demand. Compact weekly inputs and shorter
evidence/context copy. Acceptance: existing capacity/deadline/manual/lock/correction
journeys, separate review accounting and desktop/mobile/link checks; regressions.

U5 development: Chromium 9 passed. Targeted/regression checks exposed one obsolete
Plan sentence assertion; replaced it with the new concise unfinished date AND actual
continue action, keeping underlying preserved-state checks. Empty-state review found
zero capacity incorrectly restarted onboarding and the home nudge counted ordinary
work only. Added two failing real HTTP regressions, then derived waiting minutes from
the unchanged shared allocator result and kept onboarding conditional on setup state.
No workload/accounting engine changes. Final gate rerun follows.

U5 PASSED: targeted `pytest -q tests/test_ui.py tests/test_adaptation.py -m
'not browser'`: 16 passed after fixes. `scripts/check.py`: lint, 97 non-browser
tests and all six benchmarks passed. Full Chromium supporting-screen journey: 9
passed. Plan/Progress desktop/mobile screenshots visually reviewed; compact review
controls remain accessible under Review options. Scope: no service/model/migration
changes; existing capacity and separate review totals are displayed faithfully.

## UI redesign U6 — final verification and handoff
Plan: add a first-use Today → subject → goal → study time → plan → focus → unrated
finish browser journey, exercise keyboard/date links, test all main screens at 320px
and 375px, full Chromium/WebKit and normal fresh-server checks. Retain migration,
randomized invariant and independent scheduler evaluations. Review complete diff,
inspect screenshots, update run instructions and actual limitations/results.

U6 PASSED — `.venv/bin/python scripts/check.py --all --webkit` exit 0:
- Lint: passed.
- Pure functions / real SQLite / HTTP / seeded invariants: 97 passed (20.32s).
- Chromium: 10 passed (23.53s); WebKit: 10 passed (24.59s).
- Fresh normal Flask server: seven migrations, manual no-demo flow, unrated completion,
  review opt-in/late outcome/shared allocation, seed/reconcile/schema/FK checks passed.
  Production local date 2026-10-07. Test servers and browsers explicitly stopped.
- Existing populated-schema migrations passed in the non-browser suite. UI needs no new
  migration. Read-only development DB check: head ff0452cc31b6, two accounts, zero FK
  violations. No reset or seed into existing user records was performed.
- Six original independent FIFO/tiny-oracle cases retained, including the 30-minute gap.
  Existing randomized settings/seeds unchanged; no unresolved counterexample.
- Final suite: zero failures/skips. Browser/non-browser deselections are complementary.
  New Today-led browser workflow completes first setup using real routes/SQLite, keyboard
  activation, date jump links, unrated finish and unchanged finite demand/no evidence.
- Main screen checks at 1440px, 375px and 320px passed in both engines. Visually inspected
  Today desktop/mobile, subject overview/detail, focus/check-in, Plan/Progress, WebKit
  Settings and fresh production ordinary/review/conflict captures; no fatal console error.
- Diff audit: services, auth, models, clock, attachments, migrations, dependencies and
  independent benchmark unchanged. Source manifest covers 67 files; previous evidence
  preserved. Existing behavioral assertions retained; approved copy/navigation updated.
- `git diff --check` exit 0. `.venv/bin/python -m pip check` exit 0, no broken requirements;
  pip cache-permission warning is non-blocking. No dependency added.
- README, HANDOFF, TEST_REPORT, DECISIONS, ACCEPTANCE and AI_ASSISTANCE updated. No IA
  write-up or fabricated human usability/reflection claim. All U1–U6 stages complete.

Additional command detail: U4 targeted `.venv/bin/python -m pytest -q tests/test_ui.py
tests/test_adaptation.py tests/test_review_loop.py -m 'not browser'`: 20 passed.
U5 initial targeted `.venv/bin/python -m pytest -q tests/test_experience.py
tests/test_review_interface.py tests/test_ui.py tests/test_scheduler.py
tests/test_adaptation.py -m 'not browser'`: 33 passed, 1 obsolete-copy assertion failed.
Initial U5 `scripts/check.py`: 94 passed, same assertion failed. Updated the sentence
check to retain the actual unfinished date/action; subsequent recorded gates all pass.
Two empty-state tests were first run with `pytest -q tests/test_ui.py -k
'without_capacity or waiting_review'`: both failed, then passed in the final suite after
the view fix. During adding those tests an invalid-marks assertion block was briefly
misplaced; restored it to its original test before the final targeted/full verification.

Remaining limits: first visual implementation uses a light theme and native date jump
links within the complete week. Automated tests do not establish human usability or
formal accessibility. Original heuristic/local-runtime limitations remain in HANDOFF.
