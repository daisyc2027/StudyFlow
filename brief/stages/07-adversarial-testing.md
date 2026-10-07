# Stage 07 — full acceptance, randomized tests and independent review

## Build and verify

Read TEST_CONTRACT.md in full and map A01–A12 to exact tests. Run the whole real browser
workflow from a fresh account, not only a seeded demo. Expand unit/integration cases
for every discovered failure. Run randomized initial-scheduling and repair sequences
and preserve counterexamples as regressions.

Implement the test-only FIFO baseline and tiny brute-force checker. Produce a modest,
reproducible comparison on normal, deadline-conflict and changing-availability cases.
Report violations, unmet work, priority-weighted allocation and movement counts. Show
limitations instead of forcing the heuristic to win all cases.

Review the implementation as a separate pass: inspect each acceptance requirement
against the actual routes, UI, data ownership, transactions and algorithm calls. Look
for dead controls, duplicate state updates, hidden dependencies and scope drift. This
is an agent review, not an independent human certification.

## Gate

Lint, all unit/integration/property tests and required Chromium E2E tests pass through
the unified check command. There are no unexplained skips on mandatory paths. Run
WebKit when available and label its result separately. Keep factual test logs,
comparison output and screenshots. Fix failures before proceeding; an environment
blocker remains explicitly unresolved rather than becoming a fabricated pass.
