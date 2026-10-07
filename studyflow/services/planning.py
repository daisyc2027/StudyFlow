from .. import db
from ..clock import today
from ..models import PracticeTarget, WeeklyAvailability, DateAvailabilityOverride, StudySession, ReviewTask, ReviewState, SessionReview
from .evidence import target_priority
from .scheduler import Target, Booking, allocate, horizon


def snapshot(user):
    day = today(user)
    targets = list(db.session.scalars(db.select(PracticeTarget).where(PracticeTarget.user_id == user.id)
                                     .order_by(PracticeTarget.id)))
    sessions = list(db.session.scalars(db.select(StudySession).where(StudySession.user_id == user.id)
                                      .order_by(StudySession.id)))
    weekly = {r.weekday: r.minutes for r in db.session.scalars(db.select(WeeklyAvailability).where(
        WeeklyAvailability.user_id == user.id))}
    overrides = {r.date: r.minutes for r in db.session.scalars(db.select(DateAvailabilityOverride).where(
        DateAvailabilityOverride.user_id == user.id))}
    dates = set(horizon(day)) | {s.date for s in sessions}
    capacities = {d: overrides.get(d, weekly.get(d.weekday(), 0)) for d in dates}
    specs = []
    for target in targets:
        result = target_priority(target, day)
        specs.append(Target(target.id, target.requested_minutes, result.value, result.deadline,
                            not target.archived and not target.subject.archived, result.reason))
    ordinary = {t.id: t for t in specs}
    for task in db.session.scalars(db.select(ReviewTask).where(ReviewTask.user_id == user.id).order_by(ReviewTask.id)):
        base = ordinary[task.target_id]
        state = db.session.get(ReviewState, task.target_id)
        active = bool(base.active and state and state.enabled and not state.awaiting_outcome and task.state == 'pending')
        specs.append(Target(-task.id, 30 if task.state != 'cancelled' else 0, base.priority, base.deadline,
                            active, f'Review recommended {task.due_date}. ' + base.reason,
                            task.due_date, task.target_id))
    bookings = [Booking(s.id, job_key(s), s.date, s.state, s.locked, s.planned_minutes) for s in sessions]
    return day, targets, sessions, specs, capacities, bookings


def calculate(user, *, place=True):
    day, _, _, targets, capacity, bookings = snapshot(user)
    return allocate(day, targets, capacity, bookings, place=place)


def generate(user):
    from .reviews import sync
    sync(user)
    user.plan_started = True
    plan = calculate(user)
    for a in plan.assignments:
        save_assignment(user, a)
    db.session.flush()
    user.repair_fingerprint = fingerprint(user)
    return plan


def fingerprint(user):
    import hashlib
    import json
    day, _, _, targets, capacity, bookings = snapshot(user)
    payload = [str(day), [(t.id, t.budget, t.priority, str(t.deadline), t.active, str(t.not_before), t.group) for t in targets],
               sorted((str(d), m) for d, m in capacity.items()),
               [(b.id, b.target_id, str(b.date), b.state, b.locked) for b in bookings]]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def repair(user, cause='constraints'):
    from uuid import uuid4
    from ..clock import now
    from ..models import SessionEvent
    from .repair import repair_plan
    from .reviews import sync
    sync(user)
    if not user.plan_started:
        return None
    identity = fingerprint(user)
    if identity == user.repair_fingerprint:
        return None
    day, _, sessions, targets, capacities, bookings = snapshot(user)
    result = repair_plan(day, targets, capacities, bookings, evidence_only=cause == 'evidence')
    by_id = {s.id: s for s in sessions}
    changes = []
    for identifier, reason in result.cancelled:
        session = by_id[identifier]
        session.state = 'cancelled'
        session.version += 1
        changes.append(f'Block #{identifier} released: {reason}')
    already_replaced = {s.replacement_for_id for s in sessions if s.replacement_for_id}
    released = [s for s in sessions if s.state in ('missed', 'skipped', 'cancelled') and s.id not in already_replaced]
    for a in result.assignments:
        original = next((s for s in released if job_key(s) == a.target_id), None)
        if original:
            released.remove(original)
        session = save_assignment(user, a, original.id if original else None)
        changes.append(f'Block #{session.id} placed on {a.date} for {session.kind}: {session.target.topic}' +
                       (f' (replaces #{original.id}).' if original else '.'))
    if changes:
        db.session.add(SessionEvent(user_id=user.id, timestamp=now().replace(tzinfo=None),
            request_id=f'repair:{uuid4()}', payload_hash=identity,
            description=f'Plan repair after {cause}: ' + ' '.join(changes)))
    db.session.flush()
    user.repair_fingerprint = fingerprint(user)
    return result


def reconcile(user):
    from ..clock import now
    from ..models import SessionEvent
    day = today(user)
    past = list(db.session.scalars(db.select(StudySession).where(StudySession.user_id == user.id,
                StudySession.state == 'planned', StudySession.date < day)))
    for session in past:
        session.state = 'missed'
        session.version += 1
        db.session.add(SessionEvent(user_id=user.id, session_id=session.id,
            timestamp=now().replace(tzinfo=None), request_id=f'reconcile:{session.id}',
            payload_hash=str(session.id), description=f'Block #{session.id} marked missed on next visit.'))
    return bool(past)


def job_key(session):
    task_id = session.review_task_id
    return -task_id if task_id else session.target_id


def save_assignment(user, assignment, replacement_id=None):
    task = db.session.get(ReviewTask, -assignment.target_id) if assignment.target_id < 0 else None
    if task and task.user_id != user.id:
        raise ValueError('Review job must belong to this account.')
    session = StudySession(user_id=user.id, target_id=task.target_id if task else assignment.target_id,
        date=assignment.date, reason=assignment.reason, replacement_for_id=replacement_id)
    db.session.add(session)
    db.session.flush()
    if task:
        db.session.add(SessionReview(session_id=session.id, task_id=task.id,
                                    user_id=user.id, target_id=task.target_id))
        db.session.flush()
    return session
