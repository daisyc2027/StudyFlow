"""Test-only FIFO baseline and exhaustive tiny placement oracle. No product dependency."""
from collections import Counter
from datetime import date, timedelta
from itertools import product
import json
from pathlib import Path

from studyflow.services.scheduler import Target, Booking, allocate, horizon
from studyflow.services.repair import repair_plan

DAY = date(2030, 1, 7)


def fifo(day, targets, capacities):
    remaining = {t.id: t.budget for t in targets}
    result = []
    for d in horizon(day):
        free = capacities.get(d, 0) // 30
        for t in sorted(targets, key=lambda t: t.id):
            if not t.active or t.deadline and d > t.deadline:
                continue
            while free > 0 and remaining[t.id] >= 30:
                result.append((t.id, d))
                remaining[t.id] -= 30
                free -= 1
    return result


def violations(targets, capacities, placements):
    """Independent checker: no production accounting or placement helper."""
    by_id = {t.id: t for t in targets}
    used, allocated = Counter(), Counter()
    bad = 0
    for identifier, day in placements:
        target = by_id.get(identifier)
        if not target or not target.active or target.deadline and day > target.deadline:
            bad += 1
        used[day] += 30
        allocated[identifier] += 30
    bad += sum(minutes > capacities.get(day, 0) for day, minutes in used.items())
    bad += sum(minutes > by_id[identifier].budget for identifier, minutes in allocated.items() if identifier in by_id)
    return bad


def enumerate_legal(targets, capacities):
    """Enumerate all choices for tiny fixtures including unscheduled blocks."""
    block_targets = [t.id for t in targets for _ in range(t.budget // 30)]
    if len(block_targets) > 6 or len(capacities) > 3:
        raise ValueError('Tiny oracle only: at most six blocks and three dates.')
    by_id = {t.id: t for t in targets}
    legal = []
    for choices in product([None, *sorted(capacities)], repeat=len(block_targets)):
        placements = [(identifier, day) for identifier, day in zip(block_targets, choices) if day is not None]
        # Direct independent constraints; not the checker under test.
        if any(not by_id[i].active or by_id[i].deadline and d > by_id[i].deadline for i, d in placements):
            continue
        counts = Counter(d for _, d in placements)
        if any(30 * count > capacities.get(d, 0) for d, count in counts.items()):
            continue
        legal.append(tuple(placements))
    return legal


def metrics(targets, capacity, placements, moved=0):
    allocated = Counter(i for i, _ in placements)
    return {'hard_violations': violations(targets, capacity, placements),
            'remaining_minutes': sum(max(0, t.budget - 30 * allocated[t.id]) for t in targets),
            'priority_weighted_minutes': sum(30 * t.priority * allocated[t.id] for t in targets),
            'existing_sessions_released_or_moved': moved}


def evaluation():
    tomorrow = DAY + timedelta(days=1)
    scenarios = [
        ('ample capacity', [Target(1, 60, 70, None), Target(2, 60, 50, None)], {DAY: 60, tomorrow: 60}, None),
        ('limited capacity favours need', [Target(1, 60, 30, None), Target(2, 60, 90, None)], {DAY: 60}, None),
        ('FIFO fits urgent work better', [Target(1, 30, 42, DAY), Target(2, 30, 70, None)], {DAY: 30, tomorrow: 30}, None),
        ('zero availability change', [Target(1, 60, 70, None), Target(2, 30, 50, None)], {DAY: 60, tomorrow: 30}, {DAY: 0, tomorrow: 60}),
        ('no capacity', [Target(1, 30, 80, DAY)], {DAY: 0}, None),
    ]
    rows = []
    for name, targets, capacity, changed in scenarios:
        planned = allocate(DAY, targets, capacity, [])
        placements = [(a.target_id, a.date) for a in planned.assignments]
        baseline = fifo(DAY, targets, capacity)
        row = {'scenario': name, 'adaptive_initial': metrics(targets, capacity, placements),
               'fifo_initial': metrics(targets, capacity, baseline)}
        if changed is not None:
            saved = [Booking(i, target, day) for i, (target, day) in enumerate(placements, 1)]
            repaired = repair_plan(DAY, targets, changed, saved)
            cancelled = {i for i, _ in repaired.cancelled}
            after = [(b.target_id, b.date) for b in saved if b.id not in cancelled]
            after += [(a.target_id, a.date) for a in repaired.assignments]
            row['adaptive_after_change'] = metrics(targets, changed, after, len(cancelled))
            row['fifo_nonadaptive_after_change'] = metrics(targets, changed, baseline)
        if sum(t.budget for t in targets) <= 180 and len(capacity) <= 3:
            legal = enumerate_legal(targets, capacity)
            row['oracle_max_allocated_minutes'] = max(len(p) * 30 for p in legal)
            row['heuristic_allocation_gap_minutes'] = row['oracle_max_allocated_minutes'] - len(placements) * 30
        rows.append(row)
    locked_targets = [Target(1, 30, 80, None)]
    conflict = repair_plan(DAY, locked_targets, {DAY: 0}, [Booking(1, 1, DAY, locked=True)])
    assert conflict.plan.conflicts and not conflict.assignments
    rows.append({'scenario': 'pre-existing protected conflict', 'adaptive_after_change': metrics(locked_targets, {DAY: 0}, [(1, DAY)]),
                 'fifo_nonadaptive_after_change': metrics(locked_targets, {DAY: 0}, [(1, DAY)]),
                 'note': 'Both retain one pre-existing protected capacity conflict; repair reports it explicitly.'})
    return rows


def write_report():
    rows = evaluation()
    folder = Path('docs/evidence')
    (folder / 'scheduler-comparison.json').write_text(json.dumps(rows, indent=2))
    lines = ['# Synthetic scheduler comparison', '',
        'Fixed date 2030-01-07. FIFO is capacity/deadline-aware at creation, then does not adapt. ',
        'Priority-weighted minutes sum priority × allocated minutes, not learning outcomes. ',
        'Movement counts existing bookings released/replaced; new bookings are not historical moves.', '',
        '| Scenario / phase | Violations | Remaining min | Priority × min | Existing moved/released |',
        '|---|---:|---:|---:|---:|']
    for row in rows:
        for phase in ['adaptive_initial', 'fifo_initial', 'adaptive_after_change', 'fifo_nonadaptive_after_change']:
            if phase in row:
                m = row[phase]
                lines.append(f"| {row['scenario']} / {phase} | {m['hard_violations']} | {m['remaining_minutes']} | {m['priority_weighted_minutes']:.0f} | {m['existing_sessions_released_or_moved']} |")
        if row.get('heuristic_allocation_gap_minutes'):
            lines.append(f"\nTiny exhaustive oracle finds {row['heuristic_allocation_gap_minutes']} more allocatable minutes in “{row['scenario']}”.\n")
    lines += ['', 'These six small scenarios illustrate behaviour and limitations; they do not establish universal superiority or educational benefit. Protected conflicts are reported violations, not newly generated overbooking. The FIFO-better deadline case is deliberately retained.']
    Path('docs/EVALUATION.md').write_text('\n'.join(lines) + '\n')
    print(f'{len(rows)} deterministic scenarios written to docs/EVALUATION.md; FIFO-better oracle gap: 30 minutes.')


if __name__ == '__main__':
    write_report()
