# Stage 04 — initial plan, finite demand and constraints

## Build

Implement the bounded greedy scheduler in DOMAIN_RULES.md using integer 30-minute
blocks. Separate calculation from persistence. Inputs are plain target/priority,
capacity/deadline and existing-session data; outputs are proposed assignments and
unallocated-work reasons.

Use shrinking demand, remaining capacity, diminishing allocation preference,
deterministic tie-breaks and a small documented spacing preference. Do not implement
an optimiser framework or assert global optimality. Missing a placement is not a
proof that no feasible placement exists.

Add the real weekly study-plan page and Generate/Refresh plan action. Preserve IDs
and valid commitments on unchanged requests. Show daily used/available minutes and
unallocated tasks. Display dates and durations, not invented clock-time slots.

## Gate

Pass A05 plus initial randomized invariants. Check no daily overbooking, no budget
inflation, no exam-day/after-deadline assignments, zero/sub-block capacity, single target,
competing targets, no exam, large demand and duplicate generation. In a controlled
capacity-limited fixture with otherwise equal constraints, high-priority work is
favoured; do not demand this irrespective of deadlines and other constraints.

Demonstrate in a browser that manually entered feedback targets produce a saved plan.
Record exact algorithm behaviour and limits. Update progress and continue.
