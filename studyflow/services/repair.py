"""One finite repair pass. Released blocks never recursively displace other blocks."""
from collections import Counter
from dataclasses import dataclass
from datetime import date

from .scheduler import (ACTIVE, IMMUTABLE, Target, Booking, Assignment, Plan,
                        allocate, horizon)

DISPLACEMENT_GAP = 10.0
EVIDENCE_CHANGE_CAP = 2


@dataclass(frozen=True)
class Repair:
    cancelled: tuple[tuple[int, str], ...]
    assignments: tuple[Assignment, ...]
    plan: Plan


def repair_plan(today: date, targets: list[Target], capacities: dict[date, int],
                bookings: list[Booking], *, evidence_only: bool = False) -> Repair:
    by_id = {t.id: t for t in targets}
    protected = [b for b in bookings if b.state in IMMUTABLE or b.state == 'planned' and b.locked]
    history = [b for b in bookings if b.state not in ACTIVE and b.state not in IMMUTABLE]
    mutable = sorted((b for b in bookings if b.state == 'planned' and not b.locked), key=lambda b: b.id)
    credit, reserved, used = Counter(), Counter(), Counter()
    for b in protected:
        if b.state == 'completed':
            credit[b.target_id] += b.minutes
        else:
            reserved[b.target_id] += b.minutes
        used[b.date] += b.minutes
    retained, cancelled = [], []
    for b in mutable:
        t = by_id.get(b.target_id)
        reason = None
        if not t or not t.active:
            reason = 'Target archived.'
        elif b.date < today:
            reason = 'Past planned work released.'
        elif t.not_before and b.date < t.not_before:
            reason = 'Recommended review date changed.'
        elif t.deadline and b.date > t.deadline:
            reason = 'Study deadline changed.'
        elif reserved[t.id] + b.minutes > max(0, t.budget - credit[t.id]):
            reason = 'Practice budget reduced.'
        elif used[b.date] + b.minutes > capacities.get(b.date, 0):
            reason = 'Available time changed.'
        if reason:
            cancelled.append((b.id, reason))
        else:
            retained.append(b)
            reserved[t.id] += b.minutes
            used[b.date] += b.minutes
    base = protected + history + retained
    first = allocate(today, targets, capacities, base)
    added = list(first.assignments)
    virtual = [Booking(-i, a.target_id, a.date) for i, a in enumerate(added, 1)]
    # Bound displacement by the original mutable count (or two changed allocations for evidence).
    changed_allocations = 0
    dates = horizon(today)
    for _ in range(len(retained)):
        state = allocate(today, targets, capacities, base + virtual, place=False)
        needs = sorted((by_id[u.target_id] for u in state.unallocated
                        if by_id[u.target_id].active and
                        (by_id[u.target_id].deadline is None or by_id[u.target_id].deadline >= today)),
                       key=lambda t: (-t.priority, t.deadline or date.max, t.id))
        pair = None
        for high in needs:
            victims = [b for b in retained if b.date in dates and b.target_id != high.id and
                       (high.deadline is None or b.date <= high.deadline) and
                       (high.not_before is None or b.date >= high.not_before) and
                       high.priority - by_id[b.target_id].priority >= DISPLACEMENT_GAP and
                       # Do not compound any existing immutable capacity conflict.
                       sum(x.minutes for x in base + virtual if x.date == b.date and
                           (x.state in ACTIVE or x.state == 'completed')) <= capacities.get(b.date, 0)]
            if victims:
                victim = min(victims, key=lambda b: (by_id[b.target_id].priority, b.date, b.id))
                pair = high, victim
                break
        if pair is None or evidence_only and changed_allocations >= EVIDENCE_CHANGE_CAP:
            break
        high, victim = pair
        retained.remove(victim)
        base.remove(victim)
        cancelled.append((victim.id, f'Higher-priority outstanding work needs this slot (difference ≥ {DISPLACEMENT_GAP:g}).'))
        assignment = Assignment(high.id, victim.date, 'Repaired for higher-priority outstanding practice.')
        added.append(assignment)
        virtual.append(Booking(-len(virtual) - 1, assignment.target_id, assignment.date))
        changed_allocations += 1
        # One relocation attempt. Newly allocated blocks cannot become displacement victims.
        relocation = allocate(today, targets, capacities, base + virtual)
        for a in relocation.assignments:
            if evidence_only and changed_allocations >= EVIDENCE_CHANGE_CAP:
                break
            added.append(a)
            virtual.append(Booking(-len(virtual) - 1, a.target_id, a.date))
            changed_allocations += 1
    final = allocate(today, targets, capacities, base + virtual, place=False)
    return Repair(tuple(cancelled), tuple(added), final)
