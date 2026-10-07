from dataclasses import dataclass

from .. import db
from ..clock import today
from ..models import PracticeTarget, StudySession, EvidenceEntry
from .evidence import target_priority
from .lifecycle import active_seconds
from .scheduler import ACTIVE


@dataclass(frozen=True)
class TargetProgress:
    target: PracticeTarget
    completed: int
    credited: int
    outstanding: int
    reserved: int
    unallocated: int
    actual_minutes: float
    missed: int
    skipped: int
    priority: object


def report(user):
    targets = list(db.session.scalars(db.select(PracticeTarget).where(
        PracticeTarget.user_id == user.id).order_by(PracticeTarget.id)))
    sessions = list(db.session.scalars(db.select(StudySession).where(StudySession.user_id == user.id)))
    items = []
    for target in targets:
        blocks = [s for s in sessions if s.target_id == target.id and s.kind == 'practice']
        completed = sum(s.planned_minutes for s in blocks if s.state == 'completed')
        credited = min(target.requested_minutes, completed)
        outstanding = max(0, target.requested_minutes - completed)
        reserved = sum(s.planned_minutes for s in blocks if s.state in ACTIVE)
        items.append(TargetProgress(target, completed, credited, outstanding, reserved,
            max(0, outstanding - reserved), sum(active_seconds(s) for s in blocks) / 60,
            sum(s.state == 'missed' for s in blocks), sum(s.state == 'skipped' for s in blocks),
            target_priority(target, today(user))))
    active = [i for i in items if not i.target.archived and not i.target.subject.archived]
    evidence = list(db.session.scalars(db.select(EvidenceEntry).where(
        EvidenceEntry.user_id == user.id, EvidenceEntry.superseded.is_(False))
        .order_by(EvidenceEntry.date.desc(), EvidenceEntry.id.desc()).limit(12)))
    from .reviews import summary
    reviews = {t.id: summary(t, today(user)) for t in targets}
    return {'reviews': reviews, 'review_completed': sum(r['completed'] for r in reviews.values()),
            'review_remaining': sum(r['remaining'] for r in reviews.values()),
            'review_reserved': sum(r['reserved'] for r in reviews.values()),
            'review_actual': sum(r['actual'] for r in reviews.values()), 'items': items, 'budget': sum(i.target.requested_minutes for i in active),
            'credited': sum(i.credited for i in active), 'outstanding': sum(i.outstanding for i in active),
            'reserved': sum(i.reserved for i in active), 'unallocated': sum(i.unallocated for i in active),
            'actual': sum(active_seconds(s) for s in sessions) / 60,
            'missed': sum(s.state == 'missed' for s in sessions),
            'skipped': sum(s.state == 'skipped' for s in sessions), 'evidence': evidence,
            'today_sessions': [s for s in sessions if s.date == today(user) and s.state in ACTIVE],
            'unfinished': [s for s in sessions if s.state in ('in_progress','paused')]}
