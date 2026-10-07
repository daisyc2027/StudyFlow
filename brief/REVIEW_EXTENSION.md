# Adaptive review extension — approved integration contract

The full staged specification is ../studyflow_review_extension_prompt.md. This is
an extension of the completed base application, after lifecycle/repair stage 05.
All original acceptance requirements remain in force.

## Recurrence
Opt-in per target, default off. Calendar-day interval ladder [1,3,7,14,30],
initial step -1. Explicit completed-session outcomes only: needs resets to 0;
developing decreases one step, floored at 0; confident advances one, capped at 4.
Replay active, non-superseded outcomes chronologically using actual completion UTC
timestamps converted to the user's timezone. Only the last rated session per local
day (completion timestamp then stable session/evidence ID) transitions the ladder.
No attendance, marks alone, teacher feedback or free text transitions it. Corrections
retain history and replay rather than advancing again. A missing outcome is valid.

## Workload and persistence
Keep per-target derived state and one pending 30-minute review task. Database partial
unique index enforces one unfinished task per target; owner-composite foreign keys
protect links. Sessions distinguish practice/review, with review-task linkage.
Review credit/reservations never consume or enlarge the finite ordinary budget.
Miss/skip releases the attempt reservation, retaining the same obligation. Completing
without an outcome completes that obligation and pauses recurrence awaiting outcome.
A later rated session resumes it. Only the next review is generated, from observed
outcomes; no assumed-success chain. Enabling replays existing qualifying outcomes.
Disabling cancels mutable unstarted bookings; protected work and history survive.

## Shared placement
Extend the existing plain scheduling job with a not-before date and balancing group.
Ordinary jobs retain their IDs; review jobs use a separate internal task key. Both
use one greedy allocator, daily capacity ledger, priority and target-level diminishing
preference. Review earliest date = max(today,due); deadline unchanged. Keep due and
scheduled date distinct, including due beyond horizon/deadline and delayed work.
Reuse finite repair, protect active/paused/completed/locked bookings and show conflicts.
No overdue academic bonus. Unchanged refresh preserves IDs. Transactional state/evidence/
tasks/repair and existing request identity/stale guards apply.

## Stages and gates
R1: actual baseline audit, this contract and service/model plan.
R2: pure replay with hand-calculated transitions, timezone, daily dedup and correction tests.
R3: migration/state/tasks, SQLite uniqueness, ownership, rollback, toggles and separate credit.
R4: shared greedy/repair integration and seeded mixed-job invariants.
R5: target/plan/progress UI, optional outcomes and late entry, real route/browser checks.
R6: complete dated browser loop, original regressions, fresh/populated upgrades and handoff.

## Audit findings
Existing EvidenceEntry has session_id and supersession; retain it as the sole outcome
history. Completion timestamps exist on StudySession. Existing scheduler credits all
bookings by target, so review jobs MUST get their own accounting key. Existing progress
also counts all sessions as ordinary; filter ordinary sessions explicitly. Existing
corrections do not carry session linkage automatically; preserve that linkage. Existing
planning fingerprint must include review due/enablement/job state. No base prerequisite
is missing; verify all original tests as extension regression gates.
