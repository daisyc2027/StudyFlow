# Engineering decisions

- Build lives in StudyFlow. The supplied brief was copied from the staged-brief workspace; the source brief and previous projects remain untouched.
- Python 3.14 in a project virtual environment; Flask/SQLAlchemy/Jinja and local static assets. Dependencies are pinned after installation. Official Flask and Playwright installation documentation checked during setup.
- Local secret generated on first launch and stored with owner-only permissions in ignored `instance/secret`. SQLite foreign keys enabled on every connection. Schema changes use Alembic through Flask-Migrate.
- Tests use a fixed Monday (2030-01-07), a separate database/upload directory per test, and a local threaded server explicitly stopped after browser tests.

- Default target budget is 60 minutes, allowed range 30–1440 in 30-minute steps; daily capacity range 0–1440 with complete-block remainder visible.
- Evidence retains explicit source, task marks and corrections. Exact retries use unique owner/request identities plus payload hashes; stale forms use version counters. SQLite mutations serialize before reading state.
- Greedy allocation uses P/(1+k) minus a 5-point same-day repeat penalty. Repair permits a priority gap of 10 and caps evidence displacement/relocation at two changed allocations. Valid unaffected IDs stay stable; released attempts are retained with replacement links and audit descriptions.
- Archived records remain linked and inspectable. No record deletion/reset controls are exposed. Progress totals cover active budgets while actual time includes all attempts; completed allocations are capped at the current target budget for the completion numerator.
- Optional PDFs are limited to 4 MB, MIME/extension/header/end-marker checked, stored outside static assets with generated filenames and served only as owner downloads. This is not PDF sanitization or content analysis; replacement uploads retain old local files rather than destroy source material.
- Review fixed SQLite populated-upgrade defaults using literal values, preserving foreign-key enforcement. See [Alembic batch-migration documentation](https://alembic.sqlalchemy.org/en/latest/batch.html) for rebuild constraints, and [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html) for connection-level FK enforcement.
- Official setup sources: [Flask installation](https://flask.palletsprojects.com/en/stable/installation/) and [Playwright installation](https://playwright.dev/python/docs/intro). The actual installed versions are pinned in requirements.txt; verification is based on executed checks, not documentation alone.

## Review extension — 2026-10-07

The user explicitly authorized recurring reviews after the completed base build. Added
REVIEW_EXTENSION.md and R1–R6 to the plan; original contracts/tests remain in force.
ReviewState is a replayable projection; EvidenceEntry remains the sole outcome history.
A SessionReview linkage table distinguishes work without rebuilding the referenced
StudySession table or resetting user data. Partial uniqueness and composite links enforce
pending-task and ownership invariants in SQLite. Reviews use separate internal job keys
but the same target balancing group, allocator and repair. No new dependency was needed.
Only self-report outcomes attached to actual completed sessions transition intervals;
teacher/general evidence continues to affect planning need. Stable repair may retain a
later valid booking after an earlier recommendation; the UI labels that delay honestly.
An equal-timestamp regression required stable session IDs in awaiting-outcome comparisons.

## Today-first interface — 2026-10-07

The user approved the discussion prototype and a six-stage UI implementation plan.
Navigation is Today / Plan / Subjects / Progress, with Settings secondary. Existing
/targets links still open all study goals; /subjects and owned /subject/<id> pages
provide the new hierarchy. Creation and review toggles return to the relevant subject.
Original teacher comments are previewed verbatim and expandable, never summarized by
a model. Required initial practice minutes remain visible; optional context expands.

Today prioritises unfinished work and posts start/resume through the existing CSRF,
request-identity and version-protected lifecycle route. Waiting work comes from the
shared allocator's read-only result so reviews aren't lost from the home state.
Finish opens a GET check-in, with one explicit POST choice for a rating or none. GET
does not complete practice; active time continues unless paused. Completion, evidence
and repair remain one original transaction. Native links/forms/details support the
flow without JavaScript; only the elapsed display uses the existing timer script.

Seven native date links jump within the complete week. No frontend framework, schema,
new dependency, remote asset or core service change was introduced. Presentation test
selectors follow the approved copy and hierarchy; behavioral assertions are retained.
