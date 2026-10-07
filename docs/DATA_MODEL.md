# Data model

Users own subjects. Feedback notes, exams and targets each reference one subject, with composite foreign keys containing the owner ID. Target-to-feedback and target-to-exam links also include the subject ID, enforcing same-subject links in SQLite as well as routes. Referenced records are archived rather than deleted; subject changes after creation are prohibited to preserve linkage. Saved input records have version counters for stale form protection.

Weekly availability is unique per owner/weekday (0 Monday–6 Sunday); overrides are unique per owner/date and replace the weekly minutes, including zero. Capacity accepts integers 0–1440. Practice budgets accept 30–1440 in multiples of 30. Overall grades remain free-form reference text on feedback notes and are never distributed to targets. Starting ratings are explicit optional self-reports retained on targets; free text is not interpreted.

Alembic migrations are the production schema history. Tests create the equivalent metadata in fresh databases; release verification separately exercises migrations from empty SQLite.

EvidenceEntry preserves date/rating/source/task marks, a correction link, superseded state and a unique owner/request ID plus payload digest. Evidence may reference a session using an owner-composite foreign key. StudySession preserves its 30-minute planned allocation separately from measured actual seconds, active/completed UTC timestamps, lifecycle, lock, version and unique replacement link. SessionEvent records action/request identity and repair explanations. User stores explicit plan-start state and the last repaired fingerprint; no plan is regenerated on unchanged dashboard visits.

## Entity relationships and persistence

```text
User → Subject → FeedbackEntry / Exam / PracticeTarget
PracticeTarget → optional same-subject FeedbackEntry / Exam
PracticeTarget → EvidenceEntry / StudySession
EvidenceEntry → optional superseded EvidenceEntry / originating StudySession
StudySession → optional historical same-target replacement predecessor
User → WeeklyAvailability / DateAvailabilityOverride / SessionEvent
SessionEvent → optional StudySession
```

`models.py` defines these records; seven ordered revisions (including the review extension) in `migrations/versions/` build the schema. The evidence revision backfills explicit initial self-reports while leaving unknown targets unassessed. The adaptation revision names its new FK/check and gives existing users literal defaults, avoiding a referenced User-table rebuild. Settings have a user-level version counter; inputs and sessions have record versions; evidence/actions also use unique owner/request identities.

Stored calendar fields use local dates. `active_since`, `completed_at` and event timestamps store UTC (SQLite naive UTC values are explicitly interpreted as UTC). `clock.py` supplies injected UTC time and user-local today. Reports use actual local completion date for waiting, distinguish measured seconds from credited allocations, and exclude archived targets/subjects from active budget totals while preserving time/history.

Routes validate ownership before links or mutations; corrections validate both owner and target. Foreign keys are enabled on all SQLite connections. POST mutations obtain `BEGIN IMMEDIATE` before reading mutable state, and commit triggers/evidence/repair together. Failed upload transactions remove newly staged files. Production schema upgrades and retained-data checks are exercised in test_migrations.py; normal application startup never creates demo accounts or resets the database.

## Adaptive-review extension

Revision ff0452cc31b6 adds three tables without rebuilding referenced existing tables:

- ReviewState: target primary key and owner FK, enabled (default off), step -1..4,
  interval, actual last-rated local date, recommended due date, awaiting-outcome flag,
  policy version and deterministic replay fingerprint. Missing row also means off.
- ReviewTask: owner/target, due date, 30-minute allocation, pending/completed/cancelled,
  source EvidenceEntry. Partial unique SQLite index on target WHERE state='pending'
  enforces at most one unfinished obligation even outside the UI.
- SessionReview: one-to-one optional session linkage to its review task, owner and
  target. Existing sessions without this row remain ordinary practice. Composite FKs
  enforce same owner AND target for both session/task and task/source evidence links.
  Added unique indexes on existing session/evidence owner-target tuples support these
  links without rebuilding tables containing user history.

There is one performance history (EvidenceEntry). Corrections retain the originating
completed session and supersede the prior source record. Interval history is a replayed
projection with links to those original evidence IDs. Completed session timestamps,
state and measured time are never rewritten by an evidence correction. Pending task due
may change independently of its saved attempt date; immutable/locked conflicts remain
visible. Every attempt retains its own date, lifecycle, actual time and audit events.

Review sessions have separate computational demand keys, so ordinary completed/reserved
minutes and the finite requested denominator exclude them. Progress shows ordinary
remaining and recurring-review remaining/reserved/completed/actual separately. Total
active study time includes both. Enablement, evidence, projection, task changes and
schedule repair share the existing serialized SQLite transaction. Exact retries use
request/payload identities; stale forms use target/session versions. Tests cover schema
integrity, duplicate pending-task rejection, cross-owner and cross-target links,
rollback after real placement, concurrency, no-data enablement and populated upgrades.
