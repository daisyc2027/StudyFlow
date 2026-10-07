# Planning algorithms

These are configurable planning heuristics, not validated educational weights or ability percentages. Teacher text and overall grades are never automatically scored.

## Evidence and priority

`studyflow/services/priority.py` holds all evidence/priority constants and pure functions. `services/evidence.py` reads owner-scoped records and preserves source observations. Needs-practice, developing and confident map to 100, 60 and 20 planning need. Unknown uses 50 for allocation and is displayed as “Not yet assessed”. Only valid explicit ratings are included; marks remain task-labelled reference results.

Take the last three ratings ordered by evidence date then ID. Weights increase from 1 to n: 100 alone → 100; 100,60 → (100+120)/3 = 73.3333; 100,60,20 → (100+120+60)/6 = 46.6667. Round only when displaying. Corrections mark the old observation superseded and store a new one. A unique owner/request identity and payload hash make exact retries safe and reject changed payloads. Initial ratings are student self-reports; teacher skill ratings and student interpretations of comments have separate source labels.

Priority P = 0.60N + 0.30U + 0.10W. U = 100 clamp(1 − days_to_deadline/60, 0, 1). No deadline gives U=0. A linked exam's effective last-study date is exam date minus one local calendar day. W = 100 clamp(days_since_last_completed_study/14, 0, 1), using creation date if no completed session exists. N=100,U=50,W=50 gives P=80. Expired targets are flagged and cannot receive new automatic blocks. Waiting is elapsed time, never repeated-miss punishment. A priority drop is not proof of improved ability.

Session completion and missed/skipped work provide no ordinal observation unless an explicit outcome is entered. Optional marks do not merge unlike tasks into this estimate.

## Finite initial scheduling

`services/scheduler.py` accepts plain Target/Booking records and returns assignments, balances, day capacities and conflicts. `services/planning.py` persists the result. The seven-day horizon is local today through today+6. Every block is 30 minutes. Completed planned allocations satisfy the budget once; actual time remains separate. All active reservations, including those outside the horizon, reserve demand. Today's completed blocks consume today's capacity. Missed/skipped/cancelled history does not consume capacity or create debt.

Outstanding = max(0, requested − completed allocations). Unallocated = max(0, outstanding − active reservations). For each date chronologically, choose the eligible target with highest marginal score P/(1+k) − 5*s, where k counts its active/completed allocations in the horizon and s counts its same-day blocks. Ties favour the earlier deadline then smaller target ID. The 5-point repeat penalty prefers variety; it does not enforce rigid spacing. Shrink demand by one integer block at each placement. Capacity 45 permits one block and shows the 15-minute remainder. Existing commitments reserve capacity first and conflicts are explicitly visible.

At most seven days × 48 slots × target count are examined. The allocator is deterministic and bounded, not globally optimal. Unplaced work means no placement was made by this heuristic; it is not a proof of infeasibility. GET displays saved bookings and full unallocated balances, with a separate count of unsaved suggestions. Refresh saves only new allocations and preserves existing IDs.

## Stable repair and lifecycle

`services/repair.py` reserves completed, in-progress, paused and user-locked planned blocks first. It retains valid mutable blocks in stable ID order; invalid capacity/deadline/archive/budget bookings are cancelled with history, then outstanding demand gets one allocation pass. Higher-priority unallocated targets may replace lower-priority mutable blocks if the raw priority gap is at least 10. Each original mutable booking can be displaced once; new/relocated blocks cannot displace others. Relocation is attempted without recursive displacement. Evidence-only repair permits at most two changed allocations during displacement/relocation; hard-constraint corrections are uncapped by that routine limit. Pre-existing protected conflicts are visible and never compounded by a new assignment.

`services/planning.py` hashes date, target constraints/priorities, capacity and saved booking state. It saves the post-repair fingerprint. An unchanged repair request is a no-op, including after a capped evidence pass. A genuine new fact or local date changes the fingerprint. A plan begins only after explicit generation. Later genuine input changes repair it transactionally. Replacements link to an unreplaced historical attempt for the same target, and reserve the same finite demand once. Audit events explain changes.

`services/lifecycle.py` stores accumulated active seconds and a UTC start timestamp. Pause/finish add only elapsed active time; resume starts a new interval. Actual time is independent of the 30-minute credited allocation. Start/pause/resume/complete/skip/miss and lock/move actions enforce state and version rules. Unique request/event identities reject changed retries and make exact retries safe. SQLite POST mutations acquire a write lock before reading form state, preventing concurrent double credit. Routes commit evidence, lifecycle changes and repair together.

Authenticated visits reconcile past planned blocks idempotently as missed. Past active/paused sessions remain unfinished and are surfaced. There is no background daemon. Calendar dates use the user's IANA timezone; tests inject UTC clocks. Manual moves require capacity and an eligible date in the current horizon.

## Pseudocode and bounds

```text
aggregate(evidence):
    rated = valid non-superseded explicit ratings sorted by (date, ID), last 3
    if empty: return unknown allocation need 50
    return sum(recency_weight * rating_need) / sum(recency_weights)

allocate(targets, capacity, existing):
    credit completed allocations; reserve all active allocations
    reserve horizon capacity for completed and active commitments
    for each of 7 dates in chronological order:
        for each complete free 30-minute slot:
            choose eligible remaining target by marginal score, deadline, ID
            reserve 30 minutes and reduce outstanding unreserved demand
    return proposed blocks, full balances and explicit conflicts

repair(saved bookings, changed facts):
    if post-repair fact fingerprint unchanged: return without mutations
    reserve protected work; retain valid mutable work in stable order
    cancel invalid mutable work with reasons; run one allocation pass
    for each original mutable candidate at most once:
        if eligible outstanding target exceeds its priority by at least 10:
            release the lower-priority booking and reserve the high target
            attempt relocation without allowing new recursive displacement
            cap evidence-only changed allocations at 2
    preserve released history, link same-target replacements, record changes
    save the resulting fingerprint; commit with triggering evidence/state
```

For T targets, B stored bookings and S usable horizon slots (S ≤ 336), initial allocation is O(B + S·T), with sorted output bookkeeping O(T log T). Database snapshots/progress currently inspect per-target history and can cost O(T·B); that is suitable for this small local planner, not a scale claim. Repair is finite: at most B original mutable victims and bounded allocation/relocation passes. Its straightforward candidate scans can be quadratic in B plus allocation work; it favours readable constraints/stability over global optimisation. An unchanged service repair returns without creating IDs/events.

Progress queries are in `services/progress.py::report`; lifecycle timing/transitions in `services/lifecycle.py::active_seconds` and `action`; owner checks and form validation in route modules. `scripts/benchmark.py` contains a test-only FIFO baseline, independent hard-constraint checker and brute-force tiny oracle. They are never used for production placement. See EVALUATION.md for results, including heuristic limitations.

## Opt-in review intervals and mixed jobs

`services/review.py::replay` is pure. The policy version is review-v1 and the configurable
starting ladder is [1,3,7,14,30] calendar days. Each target begins at step -1: no rated
completed practice, no recommendation. Needs practice / could not complete sets step 0;
developing / completed with help decreases one step (floor 0); confident / completed
independently increases one step (cap 4). Due = actual local completion date + ladder[step].
These are transparent engineering defaults, not SM-2, a memory model or validated intervals.

Example: independent on Jan 7 → due Jan 8 (1 day); independent Jan 8 → due Jan 11 (3 days);
independent Jan 11 → due Jan 18 (7 days); help Jan 18 → due Jan 21 (3 days), or could not
complete Jan 18 → due Jan 19 (1 day). Missing Jan 19 retains that SAME review obligation
without an outcome. Completing without an outcome finishes its allocation and pauses
recurrence awaiting a genuine rated completed practice. Actual time remains separate.

Only active, non-superseded self-report outcomes linked to completed sessions with actual
UTC completion timestamps qualify. General evidence, starting ratings, marks alone and
teacher ratings/comments affect original planning need as before, but never imply a
completed review. Convert UTC to the owner's IANA timezone, select the last explicitly
rated completed session per day by (actual timestamp, session ID, evidence ID), and replay
one transition per day. Corrections inherit session linkage; late entry uses the actual
completion date, never submission/scheduled date. All source outcomes remain in history.
Replaying requires O(E log E) time and O(E) memory for E candidate outcome records.

`services/reviews.py` projects existing evidence into ReviewState and at most one pending
ReviewTask. It creates only the next observed recommendation. A fingerprint prevents
recreating a completed unrated task; awaiting-outcome uses actual completion plus stable
session ID, so equal stored timestamps remain deterministic. Enablement defaults off;
turning on explicitly authorizes recurring 30-minute allocations in addition to initial
practice. Existing qualifying outcomes are replayed on enable. Disabling cancels mutable
unstarted bookings; active/paused/locked work remains protected with a visible conflict.
A genuine outcome or correction updates an existing pending recommendation atomically.

The existing allocator now takes jobs with optional not_before and balance_id. Ordinary
job keys are target IDs; review job keys are negative review-task IDs, mapped back through
SessionReview. Credit/reservations use job keys, while diminishing preference and same-day
penalties use the shared target balancing ID across BOTH job types. Stable ties use
priority score, deadline, target ID, ordinary before review, then job key. One common
capacity ledger covers all work. Reviews are eligible only on/after max(today,due) and
on/before the effective deadline; due beyond the horizon/deadline persists visibly.
There is no overdue academic bonus. A saved valid later booking remains stable and is
labelled delayed. Locks never override validation for NEW automatic placements.

Repair uses the same bounded pass and movement caps. Changed not-before dates invalidate
mutable too-early bookings; protected too-early bookings conflict. Replacement links
match the exact job (ordinary target or same review task), preventing cross-budget credit.
Completed ordinary minutes satisfy only requested initial minutes; completed review
minutes satisfy only their 30-minute task. Miss/skip/cancel history adds neither budget.
The seven-day placement bound is unchanged (≤336 new slots); job count replaces target
count in the original complexity. Database projection currently scans history per target
and is intended for the small local app, not large-scale workloads.

Tests: test_review_algorithm.py, test_review_persistence.py, test_review_scheduling.py,
test_review_interface.py, test_review_loop.py and test_review_adversarial.py. They include
independent dates, randomized mixed constraints, rollback after real scheduling, concurrent
completions, daily/timestamp ties, actual timezone boundaries, fresh/populated upgrades
and a complete dated browser loop. The FIFO/tiny oracle remains unchanged and still
shows a case where the greedy heuristic leaves 30 feasible minutes unplaced.
