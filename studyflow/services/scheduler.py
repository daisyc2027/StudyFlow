"""Bounded greedy allocation on plain records. Dates, not appointments."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

BLOCK = 30
REPEAT_PENALTY = 5.0
ACTIVE = frozenset({'planned', 'in_progress', 'paused'})
IMMUTABLE = frozenset({'in_progress', 'paused', 'completed'})


@dataclass(frozen=True)
class Target:
    id: int
    budget: int
    priority: float
    deadline: date | None
    active: bool = True
    reason: str = 'Practice toward your goal.'
    not_before: date | None = None
    balance_id: int | None = None

    @property
    def group(self):
        return self.id if self.balance_id is None else self.balance_id


@dataclass(frozen=True)
class Booking:
    id: int
    target_id: int
    date: date
    state: str = 'planned'
    locked: bool = False
    minutes: int = BLOCK


@dataclass(frozen=True)
class Assignment:
    target_id: int
    date: date
    reason: str


@dataclass(frozen=True)
class Unallocated:
    target_id: int
    minutes: int
    reason: str


@dataclass(frozen=True)
class DayCapacity:
    date: date
    capacity: int
    used: int
    free: int
    remainder: int


@dataclass(frozen=True)
class Plan:
    assignments: tuple[Assignment, ...]
    unallocated: tuple[Unallocated, ...]
    days: tuple[DayCapacity, ...]
    conflicts: tuple[str, ...]


def horizon(today: date) -> tuple[date, ...]:
    return tuple(today + timedelta(days=i) for i in range(7))


def allocate(today: date, targets: list[Target], capacities: dict[date, int],
             bookings: list[Booking], *, place: bool = True) -> Plan:
    """Reserve all existing work, then allocate remaining demand. At most 336 slots."""
    dates = horizon(today)
    by_id = {t.id: t for t in targets}
    completed, reserved, used, count, same_day = Counter(), Counter(), Counter(), Counter(), Counter()
    conflicts = []
    for b in bookings:
        if b.state == 'completed':
            completed[b.target_id] += b.minutes
        if b.state in ACTIVE:
            reserved[b.target_id] += b.minutes
        if b.state in ACTIVE or b.state == 'completed':
            if b.date in dates:
                used[b.date] += b.minutes
                group = by_id[b.target_id].group if b.target_id in by_id else b.target_id
                count[group] += 1
                same_day[group, b.date] += 1
            target = by_id.get(b.target_id)
            if b.state in ACTIVE and target and (not target.active or
                    target.deadline and b.date > target.deadline or
                    target.not_before and b.date < target.not_before):
                conflicts.append(f'Block #{b.id}: target is disabled/archived or its due/deadline constraint is exceeded.')
    remaining = {}
    for target in targets:
        outstanding = max(0, target.budget - completed[target.id])
        remaining[target.id] = max(0, outstanding - reserved[target.id])
        if reserved[target.id] > outstanding:
            conflicts.append(f'Target #{target.id}: protected reservations exceed outstanding practice budget.')
    for day in dates:
        if used[day] > capacities.get(day, 0):
            conflicts.append(f'{day}: existing commitments use {used[day]} min against {capacities.get(day, 0)} min capacity.')
    assignments = []
    for day in dates:
        free_slots = max(0, capacities.get(day, 0) - used[day]) // BLOCK
        for _ in range(free_slots if place else 0):
            candidates = [t for t in targets if t.active and remaining[t.id] >= BLOCK and
                          (t.deadline is None or day <= t.deadline) and
                          (t.not_before is None or day >= t.not_before)]
            if not candidates:
                break
            chosen = min(candidates, key=lambda t: (
                -(t.priority / (1 + count[t.group]) - REPEAT_PENALTY * same_day[t.group, day]),
                t.deadline or date.max, t.group, t.id < 0, t.id))
            assignments.append(Assignment(chosen.id, day, chosen.reason))
            remaining[chosen.id] -= BLOCK
            used[day] += BLOCK
            count[chosen.group] += 1
            same_day[chosen.group, day] += 1
    unallocated = []
    for target in sorted(targets, key=lambda t: t.id):
        if remaining[target.id]:
            if not target.active:
                reason = 'Archived target; automatic placement is paused.'
            elif target.not_before and target.deadline and target.not_before > target.deadline:
                reason = 'Recommended review is after the study deadline; recommendation retained.'
            elif target.not_before and target.not_before > dates[-1]:
                reason = 'Recommended review is beyond this seven-day horizon; retained for later.'
            elif target.deadline and target.deadline < today:
                reason = 'Overdue; update the study deadline.'
            else:
                reason = 'No usable free slot allocated by the current heuristic before the deadline.'
            unallocated.append(Unallocated(target.id, remaining[target.id], reason))
    days = tuple(DayCapacity(day, capacities.get(day, 0), used[day],
                             max(0, capacities.get(day, 0) - used[day]),
                             max(0, capacities.get(day, 0) - used[day]) % BLOCK) for day in dates)
    return Plan(tuple(assignments), tuple(unallocated), days, tuple(conflicts))
