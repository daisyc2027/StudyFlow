# Local verification report — 2026-10-07 (Hong Kong)

Base application plus adaptive-review extension, verified against the listed checks.
Final command: `.venv/bin/python scripts/check.py --all --webkit` — **exit 0**.

| Check | Actual final result | Evidence |
|---|---|---|
| Lint (application/tests/scripts/migrations) | Passed | evidence/lint.log |
| Pure functions / real SQLite / HTTP / Hypothesis | 91 passed; 8 browser tests deselected; 17.52s | evidence/tests.log |
| Chromium | 8 passed; 91 non-browser deselected; 17.86s | evidence/chromium.log |
| WebKit | 8 passed; 91 non-browser deselected; 17.78s | evidence/webkit.log |
| Fresh normal Flask CLI/browser launch | Seven migrations; manual workflow; no inferred outcome; review opt-in, late rating and shared placement; seed/reconcile/schema/FK checks; shutdown passed | evidence/fresh-launch.log; fresh-setup.log; fresh-server.log |
| Fresh and populated migration tests | Retained old users/sessions/evidence/time/budget; review mode off; schema/FK checks passed | test_migrations.py; test_review_persistence.py |
| FIFO / tiny exhaustive comparison | Six scenarios retained, including FIFO-better 30-minute gap | evidence/benchmark.log; scheduler-comparison.json; EVALUATION.md |
| Original baseline before extension | Lint; 57 non-browser, 6 Chromium, 6 WebKit; fresh launch and benchmark passed | evidence/review-baseline-*.log |
| Dependency check | pip check passed; no dependencies added/changed | requirements.txt; base Stage 08 clean reproduction records |
| Desktop/mobile review UI | Real journeys and screenshots; no overflow/fatal page/console errors | evidence/review-ui-*.png; review-loop-*-desktop.png; review-loop-*-mobile.png |
| Commands/exit/timing metadata | All six checks exit 0 | evidence/verification-summary.json |

There are **0 failed checks, 0 skipped tests, no unexecuted mandatory checks and no
remaining mandatory blockers**. Deselections are complementary marker groups; all tests
run in the appropriate invocation. All original test files are unchanged. Main browser
journeys use actual services/database; no core mocks. Runtime requests stay on localhost.
Test servers and browsers have explicit teardown; no deployment/server remains running.

The dated fresh-user review journey creates two subjects/targets, an exam and availability,
enables one target, completes ordinary practice with an outcome, verifies 1 → 3 → 7-day
intervals on distinct actual practice days, resets to 1 after could-not-complete, misses
the same review obligation, reduces capacity to zero, and checks repeated generation,
reload/relogin/restart. Initial budget stays 60 total, separate review credit is 90 minutes,
one 30-minute review remains outstanding, with four genuine outcomes and four review
tasks. Missing/completion without outcome never creates performance evidence.

Additional real integration checks cover unrated review pause/resume through late genuine
practice, corrections/backdating from actual completion dates, same-day repeats, equal
completion timestamps, teacher/general-evidence exclusion, cap, future horizon, deadline
before due, no exam, immutable/locked/active/paused conflicts, disabled/archive states,
foreign session/source/task links, rollback after real scheduling and concurrent exact
completion retries for both job types.

Randomized settings: original priority seed 20300107 / 150 examples; generation 4042030 /
120; repair 7072030 / 200; database sequences 7172030 / 25. Review replay seed 7102030 /
150; mixed generation/repair 7112030 / 180; real SQLite mutation seeds 7122030…7122041,
12 isolated scenarios × 8 daily changes. No unresolved counterexample remains. Expected
transition dates are hand-calculated; production replay is never its own expected oracle.

Environment remains Python 3.14.7, macOS 26.6.2 arm64, SQLite 3.53.4, Flask 3.1.3,
SQLAlchemy 2.1.3, pytest 9.1.1, Hypothesis 6.168.5, Playwright 1.63.0, ruff 0.16.10,
Chromium 153.0.8010.12 and WebKit 26.6. See evidence/environment.txt. Stage 08 separately
verified all 26 pinned packages in a clean .venv-repro environment. No reinstall was
needed for the extension. pip emitted a cache-permission warning and still exited 0
with no broken requirements; this was not a runtime/test blocker.

Genuine development failures/fixes are retained in PROGRESS.md, including the same-second
awaiting-state regression, exact budget label, stable-booking test expectation and fresh
smoke ambiguous locator (failure log preserved). Source manifests record base and final
files. Screenshots were visually inspected. These are software checks, not evidence of
retention, learning improvement, human usability or formal accessibility compliance.
