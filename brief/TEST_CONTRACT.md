# Automated testing and acceptance contract

## Testing policy

Implement tests throughout development. The user should not be an intermediate test
runner. Use pytest unit tests, real SQLite/HTTP integration tests, Hypothesis-generated
invariant checks and Playwright browser tests against the actual running app.

Create a single documented verification command, preferably:
    python scripts/check.py --all
It must run lint, unit/integration/property tests and mandatory Chromium browser tests,
return nonzero on failure and preserve separate logs. A browser unavailable to the
agent is an unexecuted mandatory check, not a pass. Start/stop test servers explicitly.

Use a frozen Monday such as 2030-01-07 for acceptance fixtures and explicit timezones.
Use fresh isolated databases, temporary uploads and synthetic feedback. Unit clocks
must not depend on wall time. Browser flows can use a TESTING-only fixture clock, never
a publicly accessible production time-travel endpoint. Make failures reproducible.

## Mandatory acceptance cases

A01 Accounts: register/login/logout; bad credentials fail; two users cannot read or
mutate one another's feedback, targets, exams, sessions or attachments, including
forged IDs in POST requests. User A cannot link user B's exam or subject. Missing or
invalid CSRF tokens must reject mutating browser requests without changing records.

A02 Inputs: create/edit/archive subjects, feedback and targets; exam linkage is valid;
weekly availability and zero-minute date overrides persist after restart. Invalid
minutes, marks or dates are rejected with clear inline errors, without losing valid
form input. An overall assessment mark must not become per-target evidence.

A03 Evidence: missing ratings remain unknown; the documented one/two/three-result
averages and recency rules match independently calculated examples; numeric scores
remain source-labelled; duplicate/corrected submissions do not duplicate evidence.
Completion/missing alone does not change the evidence-derived need component.

A04 Priority: test the exact example P=80, range bounds, no deadline, far/near deadlines,
exam-today/overdue handling, waiting caps and deterministic ties. Holding other inputs
fixed, increasing need or urgency cannot reduce P. Do not conflate P with ability.

A05 Scheduling: test zero capacity, capacity below 30, exactly 30/60, leftover minutes,
single/multiple targets, competing deadlines, no exam, oversized demand and targets
with no remaining demand. No active reservations exceed target demand. No generated
block violates the deadline, capacity or 30-minute rules. Repeated input gives the
same plan; repeated saving preserves IDs and does not create duplicate rows.

A06 Adaptation: miss a block, change availability to zero, advance the date, edit a
deadline and record better/worse evidence. Verify visible repair when the fixture
contains a real competition for capacity. Check history, replacement accounting,
unchanged completed/in-progress/locked sessions and finite termination. If no space
exists, work remains visibly unallocated rather than disappearing or overbooking.

A07 Session lifecycle: start/pause/resume/complete/skip follow valid transitions; actual
active time excludes pauses and survives refresh; repeated complete/skip/reconcile
requests are safe. Invalid transitions do not corrupt records. User may complete
without a rating. The original budget does not grow when a session is missed.

A08 End-to-end browser: from a fresh user create two subjects, a feedback note, at least
three topic/skill targets, exams and availability. Generate a plan, start/pause/finish
a block, enter an outcome, see progress and plan changes, miss another block and see
repair. Edit one date's availability and observe the resulting adjustment. Reload
and log in again: records persist. Do not mock the scheduler/evidence/database here.

A09 Frontend: all main actions work using labels/buttons; no fatal browser console
errors; no broken links or debug-form-like screens. Check desktop and narrow mobile
viewports for horizontal overflow. Capture screenshots. Run WebKit too when available
and report separately; Chromium is the required minimum, not proof of every browser.

A10 Attachments: optional safe PDF attachment can be downloaded only by the owner;
unsupported/oversized uploads and path traversal fail safely. Runtime needs no OCR,
model or external API. Core acceptance also runs with no attachments at all.

A11 Failure/recovery: force an exception during an evidence+repair transaction and
verify rollback. Test stale/double requests, restart persistence, explicit lock
conflicts and expired targets. Normal app use must not reset the database.

A12 Handover: execute the documented fresh database init/run/seed/test sequence; also
complete the workflow without demo records. Inspect final diff/dependencies against
scope. No required placeholders or secretly skipped tests remain.

## Randomized checks

Generate many small combinations of budgets, deadlines, capacities, locks and outcomes.
After generation AND repair verify: nonnegative balances; capacity constraints except
explicitly reported pre-existing immutable conflicts; no new deadline violations;
accounting conservation; user isolation; no duplicate active allocation; unchanged
immutable sessions; termination; and idempotence. Record any counterexample and turn
it into a regression test. Do not assert a greedy heuristic is always optimal.

## Independent scheduler evaluation

Implement a simple non-adaptive FIFO baseline in test/benchmark code only. Compare
both on identical deterministic scenarios. Report hard violations, remaining work,
priority-weighted allocated minutes, and number of sessions moved after a change.
Keep normal cases, conflict cases and cases where the baseline does as well/better.
Do not tune only to selected successful demos or claim universal superiority.

For a few tiny fixtures, enumerate all legal placements with a test-only brute-force
oracle to independently check the capacity/deadline checker and illustrate heuristic
limitations. Never use the production placement function as its own oracle. Exact
optimality is not a product requirement; label allocation gaps honestly.

## Evidence, not reassurance

Maintain an acceptance-to-test map with test names/files. Save real command summaries,
seeds, environment versions and screenshots; use concise bounded logs. Do not fabricate
results, claim human evaluation, or substitute coverage percentages for assertions.
A mock response proves plumbing only. Automated tests do not prove improved learning,
student confidence, accessibility compliance or subjective usability.
