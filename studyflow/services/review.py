"""Transparent calendar-day spacing heuristic; no database or Flask dependencies."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LADDER = (1, 3, 7, 14, 30)
POLICY_VERSION = 'review-v1'
OUTCOMES = {'needs': 'Could not complete', 'developing': 'Completed with help',
            'confident': 'Completed independently'}


@dataclass(frozen=True)
class RatedPractice:
    id: int
    session_id: int
    completed_at: datetime
    rating: str | None
    superseded: bool = False


@dataclass(frozen=True)
class IntervalEvent:
    evidence_id: int
    practice_date: date
    rating: str
    step: int
    interval: int
    due_date: date
    reason: str


@dataclass(frozen=True)
class ReviewResult:
    step: int = -1
    interval: int | None = None
    last_date: date | None = None
    due_date: date | None = None
    source_id: int | None = None
    history: tuple[IntervalEvent, ...] = ()


def replay(outcomes, timezone_name, ladder=LADDER):
    """Rebuild state from active rated completions; at most one transition/local day.

    O(n log n) sorting and O(n) storage. Naive stored timestamps are explicitly UTC.
    Time is supplied through records, never wall/submission time.
    """
    if not ladder or any(type(d) is not int or d <= 0 for d in ladder):
        raise ValueError('Use positive integer calendar-day intervals.')
    zone = ZoneInfo(timezone_name)
    winners = {}
    for outcome in outcomes:
        if outcome.superseded or outcome.rating not in OUTCOMES:
            continue
        stamp = outcome.completed_at
        stamp = stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
        day = stamp.astimezone(zone).date()
        key = (stamp, outcome.session_id, outcome.id)
        if day not in winners or key > winners[day][0]:
            winners[day] = (key, outcome)
    step, history = -1, []
    for day, (_, outcome) in sorted(winners.items()):
        if outcome.rating == 'needs':
            step = 0
        elif outcome.rating == 'developing':
            step = max(0, step - 1)
        else:
            step = min(step + 1, len(ladder) - 1)
        interval = ladder[step]
        history.append(IntervalEvent(outcome.id, day, outcome.rating, step, interval,
            day + timedelta(days=interval), f'{OUTCOMES[outcome.rating]}; the next interval is {interval} {"day" if interval == 1 else "days"}.'))
    if not history:
        return ReviewResult()
    last = history[-1]
    return ReviewResult(step, last.interval, last.practice_date, last.due_date, last.evidence_id, tuple(history))
