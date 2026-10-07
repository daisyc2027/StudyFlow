"""Transactional projection of existing evidence into opt-in review obligations."""
import hashlib
from datetime import timedelta, timezone

from .. import db
from ..clock import now
from ..models import (EvidenceEntry, PracticeTarget, ReviewState, ReviewTask, SessionReview,
                      StudySession, SessionEvent, User)
from .review import POLICY_VERSION, RatedPractice, replay


def outcome_records(target):
    entries = list(db.session.scalars(db.select(EvidenceEntry).where(
        EvidenceEntry.user_id == target.user_id, EvidenceEntry.target_id == target.id,
        EvidenceEntry.source == 'self_report', EvidenceEntry.session_id.is_not(None))))
    values = []
    for entry in entries:
        session = db.session.get(StudySession, entry.session_id)
        if session and session.target_id == target.id and session.state == 'completed' and session.completed_at:
            values.append(RatedPractice(entry.id, session.id, session.completed_at, entry.rating, entry.superseded))
    return values


def projection(target):
    user = db.session.get(User, target.user_id)
    return replay(outcome_records(target), user.timezone)


def sync_target(target):
    state = db.session.get(ReviewState, target.id)
    if state is None:
        return None
    result = projection(target)
    signature = hashlib.sha256(repr(result).encode()).hexdigest()
    changed = signature != state.outcome_fingerprint
    tasks = list(db.session.scalars(db.select(ReviewTask).where(ReviewTask.target_id == target.id,
                                  ReviewTask.user_id == target.user_id).order_by(ReviewTask.id)))
    completed_unrated = []
    rated = {o.session_id for o in outcome_records(target) if not o.superseded and o.rating in ('needs','developing','confident')}
    qualifying = [(o.completed_at, o.session_id) for o in outcome_records(target) if not o.superseded and o.rating in ('needs','developing','confident')]
    latest_rated = max(qualifying, default=None)
    for task in tasks:
        links = db.session.scalars(db.select(SessionReview).where(SessionReview.task_id == task.id))
        attempts = [db.session.get(StudySession, link.session_id) for link in links]
        done = [s for s in attempts if s.state == 'completed']
        if done and task.state == 'pending':
            task.state = 'completed'
        completed_unrated.extend((s.completed_at, s.id) for s in done if s.id not in rated and s.completed_at)
    state.step, state.interval = result.step, result.interval
    state.last_rated_date, state.recommended_due_date = result.last_date, result.due_date
    state.awaiting_outcome = bool(completed_unrated and
        (latest_rated is None or max(completed_unrated) >= latest_rated))
    state.policy_version, state.outcome_fingerprint = POLICY_VERSION, signature
    pending = next((t for t in tasks if t.state == 'pending'), None)
    if pending and result.due_date:
        pending.due_date, pending.source_evidence_id = result.due_date, result.source_id
    if pending and (not state.enabled or state.awaiting_outcome or not result.due_date):
        protected = db.session.scalar(db.select(StudySession).join(SessionReview,
            StudySession.id == SessionReview.session_id).where(SessionReview.task_id == pending.id,
            db.or_(StudySession.state.in_(['in_progress','paused']),
                   db.and_(StudySession.state == 'planned', StudySession.locked.is_(True)))))
        if not protected:
            pending.state = 'cancelled'
    db.session.flush()  # release the unique pending slot before creating a successor
    if (state.enabled and not state.awaiting_outcome and result.due_date and changed and
            not any(t.state == 'pending' for t in tasks)):
        db.session.add(ReviewTask(user_id=target.user_id, target_id=target.id,
                                 due_date=result.due_date, source_evidence_id=result.source_id))
    db.session.flush()
    return state


def sync(user):
    for target in db.session.scalars(db.select(PracticeTarget).where(PracticeTarget.user_id == user.id)):
        sync_target(target)


def set_enabled(user, target, enabled, version, request_id):
    if target.user_id != user.id:
        raise ValueError('Review target must belong to this account.')
    payload = f'{target.id}:{enabled}:{version}'
    digest = hashlib.sha256(payload.encode()).hexdigest()
    event = db.session.scalar(db.select(SessionEvent).where(SessionEvent.user_id == user.id,
                              SessionEvent.request_id == request_id))
    if event:
        if event.payload_hash != digest:
            raise ValueError('Request identity already used for a different review change.')
        return False
    if target.version != version:
        raise ValueError('This target changed. Reload before changing reviews.')
    if target.archived or target.subject.archived:
        raise ValueError('Archived targets cannot enable reviews.')
    state = db.session.get(ReviewState, target.id)
    if state is None:
        state = ReviewState(target_id=target.id, user_id=user.id)
        db.session.add(state)
    if state.enabled != enabled:
        state.enabled = enabled
        # Enabling explicitly authorizes a new next obligation from existing evidence.
        if enabled:
            state.outcome_fingerprint = None
    target.version += 1
    db.session.flush()
    sync_target(target)
    if not enabled:
        sessions = db.session.scalars(db.select(StudySession).join(SessionReview,
            StudySession.id == SessionReview.session_id).where(SessionReview.target_id == target.id,
            StudySession.state == 'planned', StudySession.locked.is_(False)))
        for session in sessions:
            session.state, session.version = 'cancelled', session.version + 1
    db.session.add(SessionEvent(user_id=user.id, timestamp=now().astimezone(timezone.utc).replace(tzinfo=None),
        request_id=request_id, payload_hash=digest,
        description=f'Target #{target.id}: follow-up reviews {"enabled" if enabled else "disabled"}.'))
    db.session.flush()
    return True


def summary(target, day):
    """Read-only UI projection; refresh cannot manufacture obligations."""
    from uuid import uuid4
    state = db.session.get(ReviewState, target.id)
    task = db.session.scalar(db.select(ReviewTask).where(ReviewTask.target_id == target.id,
                             ReviewTask.state == 'pending'))
    attempts = list(db.session.scalars(db.select(StudySession).join(SessionReview,
        StudySession.id == SessionReview.session_id).where(SessionReview.target_id == target.id)))
    scheduled = min((s.date for s in attempts if task and s.review_task_id == task.id and
                    s.state in ('planned','in_progress','paused')), default=None)
    result = projection(target) if state else None
    due = state.recommended_due_date if state else None
    enabled = bool(state and state.enabled)
    if not enabled:
        status = 'Off'
    elif state.awaiting_outcome:
        status = 'Awaiting outcome'
    elif due is None:
        status = 'Rated practice needed'
    elif scheduled and scheduled > due:
        status = 'Delayed'
    elif scheduled:
        status = 'Due' if due <= day else 'Upcoming'
    else:
        status = 'Not scheduled'
    from .evidence import target_priority
    deadline = target_priority(target, day).deadline
    reason = result.history[-1].reason if result and result.history else 'Complete practice with an explicit outcome to establish the first review date.'
    if state is None:
        reason = 'Enable follow-up reviews to calculate a recommendation from rated completed practice.'
    if task and due and deadline and due > deadline:
        reason += ' Recommended review is after the study deadline; recommendation retained.'
    elif task and due and due > day + timedelta(days=6):
        reason += ' Beyond this seven-day horizon; retained for later.'
    elif task and not scheduled:
        reason += ' No saved reservation; check availability and refresh the plan.'
    if task and not enabled:
        reason += ' Active or locked review is protected; unlock/skip it to release the obligation.'
    from .lifecycle import active_seconds
    return {'state': state, 'enabled': enabled, 'task': task, 'due': due, 'scheduled': scheduled,
            'status': status, 'timing': 'Overdue' if due and due < day else 'Due' if due == day else 'Upcoming',
            'reason': reason, 'history': result.history if result else (), 'request_id': str(uuid4()),
            'completed': sum(s.planned_minutes for s in attempts if s.state == 'completed'),
            'remaining': 30 if task else 0, 'reserved': 30 if scheduled else 0,
            'actual': sum(active_seconds(s) for s in attempts) / 60}
