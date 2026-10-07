"""Inspectable planning heuristics; no academic ability is inferred."""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

RATING_NEED = {'needs': 100.0, 'developing': 60.0, 'confident': 20.0}
UNKNOWN_NEED = 50.0
NEED_WEIGHT, URGENCY_WEIGHT, WAIT_WEIGHT = 0.60, 0.30, 0.10
WAIT_DAYS, URGENCY_DAYS = 14, 60


@dataclass(frozen=True)
class Observation:
    id: int
    date: date
    rating: str | None
    superseded: bool = False


@dataclass(frozen=True)
class Need:
    value: float
    known: bool
    count: int


@dataclass(frozen=True)
class Priority:
    value: float
    need: Need
    urgency: float
    waiting: float
    deadline: date | None
    overdue: bool
    reason: str


def aggregate(observations: Iterable[Observation]) -> Need:
    """Last three valid ratings, stable date/ID ordering, weights 1..n."""
    rated = sorted((o for o in observations if not o.superseded and o.rating in RATING_NEED),
                   key=lambda o: (o.date, o.id))[-3:]
    if not rated:
        return Need(UNKNOWN_NEED, False, 0)
    value = sum(i * RATING_NEED[o.rating] for i, o in enumerate(rated, 1))
    return Need(value / sum(range(1, len(rated) + 1)), True, len(rated))


def effective_deadline(exam_date: date | None, explicit_date: date | None) -> date | None:
    return exam_date - timedelta(days=1) if exam_date else explicit_date


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def priority(need: Need, today: date, last_study: date, deadline: date | None) -> Priority:
    urgency = 100 * clamp(1 - (deadline - today).days / URGENCY_DAYS) if deadline else 0.0
    waiting = 100 * clamp((today - last_study).days / WAIT_DAYS)
    value = NEED_WEIGHT * need.value + URGENCY_WEIGHT * urgency + WAIT_WEIGHT * waiting
    overdue = bool(deadline and deadline < today)
    if overdue:
        reason = 'Study deadline has passed; update it before automatic placement.'
    elif not need.known:
        reason = 'Not yet assessed; set aside an initial practice block.'
    elif need.value >= 70:
        reason = 'Recent reports suggest more practice is useful.'
    elif deadline and (deadline - today).days <= 7:
        reason = 'The study deadline is close.'
    elif waiting >= 50:
        reason = 'This target has waited for practice.'
    else:
        reason = 'Keep practice moving toward your goal.'
    return Priority(value, need, urgency, waiting, deadline, overdue, reason)
