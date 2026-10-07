# Agent acceptance review — 2026-10-06

This is a separate Codex review pass, not independent human certification. Reviewed PRODUCT.md and A01–A12 against route inventory, models, computational services, tests, navigation and dependency pins.

- All required input records are owner-scoped. Composite foreign keys enforce subject/owner and feedback/exam/subject links. Every ID-based route uses `auth.owned`; forged read/write IDs are exercised. Corrections additionally enforce target ownership. Private reference uploads use generated basenames and attachment-only owner serving.
- CSRF middleware rejects mutations before any write lock. POSTs acquire SQLite write serialization before loading state. Session/evidence request identities and version checks protect credit/outcomes. Review added settings versions and made repeated archives no-ops; tests cover concurrency and stale forms.
- Priority functions are pure and inspectable. Teacher text/overall grades and numeric task marks never become ordinal outcomes. Completion/miss/skip cannot change the need component without explicit evidence. Late completions use their actual local date for waiting.
- Generation reserves all outstanding work, including outside the horizon, and counts completed commitments. Repair protects immutable/locked records, preserves history, bounds displacement and exposes unmet work/conflicts. Fingerprints protect unchanged requests. Random conservation/immutability and database sequence tests cover both initial and adaptive paths.
- Navigation has real Dashboard, Feedback & Targets, Study Plan, Progress and Settings pages. Create/edit/archive, exams, overrides, correction/source input, upload/download, timing, locks/moves/skip and explicit budget increases are exercised through real browser actions. Screenshots and mobile overflow checks cover the six major/session views. No dead controls or required placeholders found.
- Tests use fresh SQLite/upload fixtures and a fixed clock; no production time-travel route. Production startup does not seed or reset records. Migration tests exercise both empty setup and populated upgrades. The populated-upgrade regression required literal defaults to avoid rebuilding the referenced User table; foreign keys stay enabled.
- Dependencies comprise the approved Flask/SQLAlchemy/Jinja stack, security/migration helpers and pytest/Hypothesis/Playwright/ruff tooling. Runtime browser requests stay on localhost. No OCR, LLM/model runtime, external API, generated quizzes, OAuth/calendar, cloud deployment or previous-project code added.

A newly written archive test incorrectly expected the generic word “retained” absent, but the successful archive flash correctly says history is retained. Corrected it to positively assert the archived target is visible. This does not weaken record retention or hide an application defect. All substantive application defects found during work have regression assertions.

Remaining limitations are intentional: heuristic scheduling can miss legal placements (the FIFO-better tiny example is retained), local dates rather than clock-time/calendar appointments, next-visit reconciliation without a daemon, basic PDF type/size/header/end checks without sanitization, and no measured human usability/accessibility/educational outcomes. Stage 08 verifies the pinned environment and normal fresh launch separately.

## Adaptive-review scope review — 2026-10-07

Reviewed the actual extension services, model/migration links, route authorization,
capacity/accounting integration, test fixtures and UI. Original test files, auth/priority,
CSS/JS, existing migrations, dependency pins and FIFO/oracle were unchanged against the
base SHA256 manifest. Twenty existing implementation/tooling files were extended; new
review services/routes/partial/template/test files provide the authorized scope.

Review jobs have independent credit keys but common balancing/capacity. No attendance
or missing event transitions the interval engine. No completed session is rewritten by
correction. One pending task is enforced by SQLite uniqueness, owner/target links by
composite foreign keys, and all state/evidence/task/repair changes by the existing write
transaction. Optional outcomes and recurring-work consent are visible. UI history exposes
real evidence sources and interval reasons, with no retention probabilities or mastery
claims. Late entry validates an actual owned completed session; dates come from its
completion timestamp. Disable protects active/paused/locked work and surfaces conflicts.

Regression review retained fixes for equal-timestamp recurrence and the accessible budget
label. A new test's earlier-placement assumption was corrected to preserve the stable
saved booking. The normal-server smoke's ambiguous locator was scoped to both due and
scheduled date. Original no-outcome assertions remain before the explicitly entered
late outcome; additional review assertions follow it. No required test was skipped or
core component mocked in either browser journey. An injected exception occurs AFTER real
review creation/placement to test rollback; it is not a fake end-to-end success path.

Desktop/mobile dated-loop screenshots were visually inspected. Remaining limits include
heuristic intervals, small local history scans, visit-triggered reconciliation, a greedy
allocation gap and unevaluated learning effectiveness. This is an agent review, not a
human evaluation or independent certification.
