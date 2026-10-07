# StudyFlow — staged adaptive-review extension

Extend the existing StudyFlow Planner project. Do not start a new application or replace working code.

GOAL

Keep the deterministic greedy scheduler and stable adaptive rescheduler. Add an outcome-based review-interval engine that decides WHEN a practice target should next be reviewed. The scheduler decides WHERE that review fits within capacity and deadlines.

This is a transparent practice-spacing heuristic, not a trained predictive model, a validated memory model, or a claim to implement SM-2 exactly. Do not add a genetic algorithm, OCR, LLM, automatic marking, generated quizzes, external calendar integration or paid service.

EXECUTION CONTRACT

Read AGENTS.md, brief/PRODUCT.md, brief/DOMAIN_RULES.md, brief/TEST_CONTRACT.md, brief/PLAN.md and docs/PROGRESS.md where present. Inspect actual code and test results; do not assume a feature exists because it appears in a brief.

Complete the extension stages below sequentially. At each stage:
1. Record the intended changes and acceptance tests.
2. Implement a small working slice.
3. Run its tests and the accumulated regression suite.
4. Fix failures and check the diff for unrelated changes.
5. Record actual commands/results in docs/PROGRESS.md.
6. Continue automatically after the gate passes; do not ask for routine approval.

Use existing permissions. Do not bypass safeguards, delete user records or change unrelated projects. Record genuine blockers and continue independent work where safe. Never fabricate test results, disable valid assertions or label unfinished work complete.

If the base application is not yet built, complete the dependent original stages first. Insert this extension after the base session lifecycle/adaptive repair, then finish the remaining original stages with the extension included in end-to-end verification. A running application, not just updated documentation, is required.

STAGE R1 — AUDIT AND DEFINE THE EXTENSION

Preserve the existing:
- target-specific feedback and practice outcomes;
- priority calculation;
- seven-day horizon and 30-minute blocks;
- finite initial practice budgets;
- capacity/deadline rules, locks and stable session identities;
- authentication, ownership checks and existing tests.

Inspect how targets, evidence, sessions and outstanding demand currently interact. Record the actual baseline test results before changing code.

Write brief/REVIEW_EXTENSION.md and update the plan/domain contract to include the rules below. Recurring reviews are an explicit new scope item, not permission to rewrite unrelated requirements. Keep original budget-conservation rules for ordinary practice; define separate accounting for reviews.

Gate: documented integration plan, known baseline failures, and identified service/model changes.

STAGE R2 — IMPLEMENT THE PURE REVIEW-INTERVAL ALGORITHM

Use the following configurable starting policy. These are engineering defaults, not scientifically optimal learning intervals.

Interval ladder in calendar days:
[1, 3, 7, 14, 30]

Each target starts with step = -1, meaning no qualifying practice outcome yet. No outcome means no calculated review date.

On an explicit outcome from a completed practice or review session:
- Could not complete: new_step = 0.
- Completed with help: new_step = max(0, old_step - 1).
- Completed independently: new_step = min(old_step + 1, 4).

Then:
interval_days = ladder[new_step]
recommended_due_date = actual_practice_local_date + interval_days

Examples:
- First independent completion: next review in 1 day.
- Next independent completion on a later day: 3 days.
- Next independent completion on a later day: 7 days.
- With-help outcome at the 7-day step: return to 3 days.
- Could-not-complete outcome at any step: return to 1 day.

Use the existing three outcome categories; do not infer an outcome from attendance, free text, an overall grade or the absence of a rating. Teacher feedback can still affect planning need under the existing rules, but is not evidence of a completed review.

Process at most one interval transition per target per local calendar day. Use the last explicitly rated completed practice on that day, ordered by actual completion timestamp then stable ID. Preserve all original outcomes for progress reporting. This prevents repeated same-day submissions or sessions from rapidly advancing the ladder.

Implement the calculation as a pure function/service, separate from Flask and database writes. Inject time and use the user's timezone. Do not use submission date in place of actual practice date.

When an accepted outcome is corrected or backdated, recompute the affected target's state chronologically from active, non-superseded outcomes rather than applying another transition. Do not alter completed session history.

Gate: independently calculated unit tests for all transitions, no outcome, initial state, bounds, repeated same-day practice, corrected evidence, deterministic replay and timezone boundaries.

STAGE R3 — PERSIST REVIEW STATE WITHOUT INFLATING WORKLOAD

Adapt existing models and migrations. Reuse the existing outcome records rather than copying the same evidence into two performance histories.

Add equivalent structures for:
- Per-target review state: enabled, step, interval, last rated practice date, recommended next-review date, awaiting-outcome state and policy version.
- Review tasks: target, due date, fixed 30-minute allocation, lifecycle state and links to source outcome and scheduled attempt(s).
- A way to distinguish ordinary-practice sessions from review sessions.

Follow-up reviews must be opt-in per target, default OFF. Explain that enabling them authorizes ongoing 30-minute review tasks in addition to the target's finite initial budget. Existing users/targets must not silently acquire recurring work.

On enabling reviews, derive the current state from existing qualifying outcomes if available. Otherwise show that a rated practice session is needed to establish the first review date.

Rules:
- At most one unfinished review task per target; enforce integrity in the database/transaction logic, not only in the UI.
- Generate only the NEXT review from observed outcomes. Never populate a chain of future reviews assuming success.
- Review allocations do not change, consume or inflate the initial practice budget.
- Each completed block is credited once, to its own task type; never count it against both budgets.
- A missed/skipped review releases its scheduling reservation but preserves the same outstanding review task. No extra debt or failed-recall outcome is created.
- Completing a review without an outcome completes that task, but pauses the recurrence as “awaiting outcome”. Do not assume success or recreate the just-completed task.
- A later genuine rated practice can resume/update the next review. Normal target practice with an explicit outcome may also update an existing unstarted review's due date; it must not create a second pending review.
- Do not rewrite active, completed or locked sessions. Surface conflicts when a due-date change cannot be applied safely.
- Disabling reviews cancels unstarted mutable review bookings, while preserving history and active/locked-session safeguards.

Persist evidence, derived state, task changes and schedule changes atomically. Use stable request/event identities so retries and double-clicks cannot apply outcomes or create tasks twice. Corrections update the current pending recommendation rather than multiplying tasks.

Gate: real SQLite tests for migration, uniqueness, ownership, rollback, duplicate requests, separate budgets, correction replay and enabling/disabling review mode.

STAGE R4 — INTEGRATE WITH GREEDY SCHEDULING AND ADAPTIVE REPAIR

Do not create a second independent calendar allocator.

Treat each pending review as a 30-minute scheduling job with a target priority, a not-before date and the existing effective deadline.

Keep recommended_due_date separate from scheduled_date:
- A review can be placed on or after max(today, recommended_due_date).
- It cannot be placed after the effective study deadline.
- A linked exam remains excluded as a study day under the original contract.
- If the recommendation is beyond the deadline, retain it and show why it is not scheduled. Do not silently move it earlier and pretend the interval was followed.
- Due dates beyond the seven-day horizon persist; do not force them into this week's plan.
- A review scheduled later than recommended must be visibly labelled delayed/overdue.

Use the existing priority and diminishing-allocation preference for eligible jobs. Count same-target ordinary/review allocations consistently so they do not bypass balancing. Extend stable tie-breaking only where necessary. Do not count review overdue time as an additional academic failure or add an unbounded priority bonus.

Both job types share the same daily capacity ledger. Preserve zero/sub-block capacity behaviour and show unscheduled work honestly. A failed greedy placement is not proof of mathematical infeasibility.

Reuse bounded adaptive repair after outcomes, missed reviews, deadline changes and availability changes. Preserve unaffected sessions and existing movement limits. If work is displaced, keep its demand visible. Never recursively displace work forever.

Refreshing the plan without a genuine change must preserve task/session identities and must not generate new reviews. Reconcile time-dependent status on the existing app-visit/explicit-command mechanism; no background daemon is required.

Gate: integration and randomized invariant tests for mixed practice/review workloads, capacity, deadline restrictions, overdue reviews, future-horizon persistence, immutable sessions, unchanged-request stability and bounded repair.

STAGE R5 — ADD A SIMPLE REVIEW INTERFACE AND ANALYTICS

Integrate this into existing target cards, the study plan and progress page. Do not build another complicated diagnostic form.

Show:
- Follow-up reviews: on/off.
- Recommended next review and actual scheduled date, when different.
- Due / upcoming / delayed / awaiting outcome / not scheduled status.
- Three familiar outcome buttons after practice.
- A short reason, such as “Independent completion; the next interval is 7 days.”

Show outcome history and interval history with evidence-source labels. Keep initial practice remaining and recurring review work separate. Report planned versus actual study minutes accurately. Do not display invented retention probabilities or claim that interval growth proves mastery.

A missing outcome remains valid; never force students to select a success rating just to finish a session.

Gate: route and headless-browser tests covering enablement, outcome recording, due dates, explanations, no-data states, no-capacity states and disabling reviews. No real student data.

STAGE R6 — VERIFY THE COMPLETE ADAPTIVE LOOP

Extend the project's unified verification command. Run all original tests plus the new tests. Fix regressions; do not weaken unrelated requirements.

Required end-to-end path, with injected dates:
1. Register a fresh user and create subjects, targets, deadlines and availability.
2. Enable reviews for one target only.
3. Generate and complete ordinary practice; record an explicit outcome.
4. Confirm the correct interval and exactly one pending review.
5. Place that review through the real greedy scheduler.
6. Complete reviews on distinct simulated days with independent outcomes; verify 1 -> 3 -> 7-day intervals.
7. Record a could-not-complete outcome; verify reset to 1 day.
8. Miss the next review; confirm the same obligation is repaired without a new ability rating or duplicated workload.
9. Reduce availability; verify valid repair or visible unallocated work, not overbooking.
10. Repeat requests and reload the app; verify persistence and no duplicate changes.

Also test completion without an outcome, late-entered/corrected outcomes, same-day repeats, capped intervals, deadline-before-due, no exam, locked conflicts, paused/active sessions, disabled targets, cross-user access and failed transactions.

Use hand-calculated expected dates, seeded randomized scenarios and invariant checks. Do not call the implementation itself to generate expected answers. Use the real services/database in end-to-end tests; do not mock the scheduler or interval engine.

Retain the existing scheduler-baseline and tiny-instance comparison tests. Distinguish “follows the scheduling rules” from “improves learning”; synthetic tests cannot establish educational effectiveness.

FINISHING REQUIREMENTS

Run a real headless-browser journey and verify both a fresh setup and an upgrade from an existing database. Record exact commands, pass/fail/skip counts, blockers and limitations in docs/HANDOFF.md.

Update architecture/algorithm documentation with the recurrence rules, workload separation, examples, complexity bounds and tests. Record agent-assisted changes honestly. Do not fabricate first-person IA reflections or modify Criterion A–D write-ups.

Continue through all stages without routine approval requests. End with what actually works, tests actually run, remaining limitations and exact local run/verification commands.
