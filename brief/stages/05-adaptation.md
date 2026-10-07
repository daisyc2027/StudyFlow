# Stage 05 — lifecycle and adaptive repair

## Build

Implement planned, in-progress, paused, completed, missed, skipped and cancelled
history as needed. Start/pause/resume/finish actions track actual active time without
counting pauses. A refresh must not reset or duplicate a session. Completion can omit
an outcome; an outcome is separate evidence.

Implement missed-work reconciliation, deadline/availability repair, evidence-driven
limited rebalancing, manual valid rescheduling and locks according to DOMAIN_RULES.md.
Do not erase and regenerate the entire calendar. Preserve unaffected sessions and
history. Show a concise explanation of changes and unmet work.

Persist evidence and resulting state/schedule updates atomically. Guard stale/double
submissions. Reconciliation happens on the next app visit or a documented command,
not through an invented background service. Use injected clocks in tests.

## Gate

Pass A06/A07 and transactional rollback tests. Exercise a capacity-limited case where
a high-priority missed task displaces lower-priority work, and a no-space case where
work remains unallocated. Test repeated repair, unchanged IDs, no duplicated workload,
locked/active/completed preservation, pause timing, revised deadlines and prior-day
reconciliation. Assert that repair terminates and does not let displaced blocks cycle.
Run the first real end-to-end feedback → plan → practice → update → repaired-plan test.
