# Domain and algorithm contract

These are proposed application rules, not validated educational claims or official IB
marking thresholds. Implement them transparently and test them. Do not silently replace
them with an LLM or a library that hides the scheduling logic.

## 1. Evidence and planning need

Store original feedback and evidence separately from derived priority. Never distribute
an overall assessment percentage across all its skills.

Core evidence is an explicit, target-specific rating/outcome:
- needs practice / could not complete: planning need value 100;
- developing / completed with help: 60;
- confident / completed independently: 20.

These numbers are configurable planning heuristics, NOT ability percentages. Starting
state may be unknown. Unknown uses 50 for allocation only and is displayed as “Not yet
assessed”, not “50% ability”. Keep self-reports labelled as self-reports. A manually
recorded teacher skill rating must be distinguishable from a student interpretation
of a teacher comment. Free text alone is not automatically scored.

For a target, use its last three valid explicit ratings/outcomes, ordered by evidence
date and then stable ID. Apply recency weights 1..n from oldest to newest and divide
by their sum. Example: 100, 60, 20 gives 280/6 = 46.6667. With only 100, 60,
the value is 220/3 = 73.3333. With no rated evidence, use the unknown policy above.
Do not round until displaying. Corrections supersede evidence, not double-count it.

Optional earned/possible marks can be logged and shown, preserving the task/source.
For version 1 do not automatically merge marks from unlike tasks into this ordinal
estimate. The user can also record the corresponding practice outcome explicitly.
Only genuine target-specific numeric results belong on that target; an overall
assessment score stays on the assessment note.

Session completion, missing, skipping or moving a session must NEVER create an ability
rating. A missed block is outstanding work, not proof of reduced understanding.

## 2. Priority

Use a simple inspectable rule initially:
P = 0.60 * N + 0.30 * U + 0.10 * W.
N is the planning need above. U is deadline urgency. W is waiting time, not a punitive
count of repeated missed-session requests. All components lie in 0..100.

Let last_study_date be the target's last completed session date, or its creation date
when no session has been completed. W = 100 * clamp(days_since_last_study / 14, 0, 1).

The effective study deadline is exam_date minus one local calendar day when linked
to an exam; otherwise use the optional explicit last-study date. No deadline means
U = 0. For a deadline d days away, U = 100 * clamp(1 - d/60, 0, 1). Expired work
is flagged overdue and excluded from automatic placement until its deadline changes;
urgency alone must not permit studying after a deadline.

Show short deterministic reasons. The numerical priority may be under Details. Do not
infer academic improvement merely from a priority falling after an exam disappears.
Unit example: N=100, U=50, W=50 gives P=80. Weights/thresholds belong in one config.

## 3. Finite workload: no duplicate debt

A target has a requested practice budget, default 60 minutes, in positive multiples
of 30. The student can add more practice or revise uncompleted demand. This is an
estimate of planned work, not a prediction of minutes needed for mastery.

Create 30-minute scheduled blocks initially. Show adjacent same-target blocks grouped
visually where useful, but preserve stable block IDs. Do not build arbitrary-duration
packing for this version.

Completed blocks satisfy their planned allocation once. Actual measured minutes are
stored separately for time reports. An early finish does not imply mastery. Never
silently represent planned duration as measured duration.

For each target, outstanding demand equals requested minutes minus credited completed
allocations, floored at zero. Planned/in-progress/paused blocks reserve outstanding
demand; missed/skipped/cancelled historical attempts do not reserve additional demand.
Outstanding demand = active reserved minutes + unallocated minutes.

Missing a 30-minute block releases its reservation but does not add another 30 minutes
to the original budget. Replacing it reserves the same outstanding work once. Repeated
requests must not create repeated replacement debt. Expanding the budget is an explicit
user action, never a side effect of refreshing a page or changing a quiz result.

## 4. Calendar and availability

The planner assigns dates and durations, not clock-time appointments. Do not promise
collision detection against external calendars. Weekly minutes plus date-specific
overrides are the source of capacity; an override replaces that date's weekly value.

Plan from local today through today+6 inclusive. A target can only be placed on or
before its effective last-study date. A linked exam is not a study day. No deadline
means eligible anywhere in the current horizon.

Validate minutes as non-negative integers up to 1440. Allow zero. Use only complete
30-minute blocks; show unusable remainder rather than round capacity up. Count all
capacity-consuming commitments, including already completed planned blocks today,
active sessions and locked future blocks. Historical missed/skipped attempts do not
consume future capacity. Outside-horizon reservations still reserve target demand.

Store timestamps in UTC and derive calendar dates using the user's timezone. Use an
injected clock for tests. Never hard-code today's real date. Do not create a daemon:
past planned sessions are reconciled idempotently on the next authenticated app visit
or an explicit local command. Unfinished in-progress sessions must be surfaced rather
than silently marked completed. Describe that behaviour honestly in the UI/docs.

## 5. Initial scheduling

Write a deterministic greedy allocator returning proposed assignments and explicit
unallocated-work reasons, without directly modifying the database.

Start by reserving immutable and existing valid commitments and calculating remaining
capacity and demand. Traverse eligible dates chronologically. At each free 30-minute
slot choose among eligible targets with outstanding unreserved demand.

Use priority with diminishing allocation preference, for example
marginal_score = P / (1 + k), where k is the number of blocks for that target already
allocated/completed in the current horizon. Apply a small documented same-day repeat
penalty to prefer spacing when feasible. Break remaining ties by earlier deadline,
then stable target ID. This allocates more attention to high needs without filling
the entire week with the first target. Spacing is a preference, never a reason to
violate deadlines or manufacture capacity.

Do not independently round proportional minutes upward for every target. Work in
integer blocks throughout. Complexity must be bounded by finite days/slots/targets.
The algorithm is a heuristic, not a proof of optimality or infeasibility. Label
unplaced work accurately, e.g. no usable free slot, overdue, or not allocated by the
current heuristic. Do not claim a feasible plan cannot exist merely because greedy
placement did not find it.

## 6. Stable adaptive repair

Trigger repair after genuine changes: evidence, deadline, target budget, availability,
missed/skipped work or manual rescheduling. Repeating an unchanged request must keep
the same schedule and IDs. Never regenerate everything on every dashboard GET.

Keep completed/in-progress/paused sessions immutable. Respect user-locked future
sessions. When constraints make a locked session invalid, display the conflict rather
than silently move it. Repair other work without compounding that conflict.

Preserve valid unaffected sessions first. Release invalid mutable bookings and attempt
to place their outstanding work into free eligible slots. If needed, allow higher
priority unallocated work to displace lower priority mutable work, using a documented
minimum priority difference of 10 initially. Try to relocate the displaced block;
otherwise return it to visible unallocated demand. Preserve history.

Use a bounded repair pass: consider each mutable block a limited number of times;
do not allow recursively displaced sessions to displace one another indefinitely.
For evidence-only rebalancing, cap routine changes at two blocks per run. Hard
constraint repairs may need more changes. Record what moved and why. This is a
stability preference, not a guarantee of minimum movement.

Persist evidence, state changes and the resulting schedule update transactionally.
Repeated submissions use stable event/request identity. Protect against stale/double
submissions so completing one block twice cannot duplicate evidence or workload credit.

## 7. Progress

Report planned versus actual minutes, completed work, outstanding work, source-labelled
practice outcomes and priority separately. Archive rather than destroy referenced
records. Avoid double-counting missed attempts and their replacements in completion
summaries: clearly define each denominator and show missed attempts separately.
A completed final block may exhaust the budget even when the outcome is poor; offer
“Add 30 minutes of practice”, without silently increasing the student's workload.

## 8. Opt-in adaptive reviews

The additional recurrence, separate review accounting and not-before rules in
[REVIEW_EXTENSION.md](REVIEW_EXTENSION.md) extend this contract. Ordinary finite
practice rules remain unchanged. Interval growth is a spacing heuristic, not mastery.
