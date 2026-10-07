import hashlib
import json
from datetime import timezone

from .. import db
from ..clock import now, today
from ..models import SessionEvent
from .evidence import record
from .planning import repair

TRANSITIONS = {'start': ('planned', 'in_progress'), 'pause': ('in_progress', 'paused'),
               'resume': ('paused', 'in_progress')}


def active_seconds(session):
    elapsed = 0
    if session.state == 'in_progress' and session.active_since:
        elapsed = max(0, (now() - session.active_since.replace(tzinfo=timezone.utc)).total_seconds())
    return session.actual_seconds + elapsed


def action(user, session, name, version, request_id, *, rating=None, earned=None, possible=None,
           note='', move_date=None):
    payload = dict(session=session.id, action=name, version=version, rating=rating, earned=earned,
                   possible=possible, note=note, move_date=str(move_date))
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    previous = db.session.scalar(db.select(SessionEvent).where(SessionEvent.user_id == user.id,
                                  SessionEvent.request_id == request_id))
    if previous:
        if previous.payload_hash != digest:
            raise ValueError('This request was already used for a different action.')
        return False
    if version != session.version:
        raise ValueError('This block changed. Reload before acting again.')
    if name in TRANSITIONS:
        expected, resulting = TRANSITIONS[name]
        if session.state != expected:
            raise ValueError(f'Cannot {name} a {session.state.replace("_", " ")} block.')
        if name == 'start' and session.date != today(user):
            raise ValueError('Start a block scheduled for today. Move it first if needed.')
        if name == 'start' and session.review_task_id:
            from ..models import ReviewState, ReviewTask
            state = db.session.get(ReviewState, session.target_id)
            task = db.session.get(ReviewTask, session.review_task_id)
            if not state.enabled or task.due_date > today(user):
                raise ValueError('Reviews must be enabled and their recommended date reached before starting.')
        if name == 'pause':
            session.actual_seconds = active_seconds(session)
            session.active_since = None
        else:
            session.active_since = now().replace(tzinfo=None)
        session.state = resulting
    elif name in ('complete', 'skip', 'miss'):
        allowed = ('in_progress', 'paused') if name == 'complete' else ('planned',) if name == 'miss' else ('planned', 'in_progress', 'paused')
        if session.state not in allowed:
            raise ValueError(f'Cannot {name} this block in its current state.')
        session.actual_seconds = active_seconds(session)
        session.active_since = None
        session.state = {'complete': 'completed', 'skip': 'skipped', 'miss': 'missed'}[name]
        if name == 'complete':
            session.completed_at = now().replace(tzinfo=None)
            if rating or earned is not None:
                record(session.target, request_id=f'session:{request_id}', date=today(user),
                       rating=rating, source='self_report', note=note or f'Practice session #{session.id}',
                       earned=earned, possible=possible, session_id=session.id)
                session.target.version += 1
    elif name in ('lock', 'unlock', 'move'):
        if session.state != 'planned':
            raise ValueError('Only future planned blocks can be locked or moved.')
        if name == 'move':
            if session.locked:
                raise ValueError('Unlock this block before moving it.')
            from .planning import snapshot, job_key
            from .scheduler import ACTIVE, horizon
            day, _, sessions, targets, capacity, _ = snapshot(user)
            target = next(t for t in targets if t.id == job_key(session))
            if move_date not in horizon(day) or not target.active or target.deadline and move_date > target.deadline or target.not_before and move_date < target.not_before:
                raise ValueError('Choose an eligible date in the current seven-day plan.')
            used = sum(s.planned_minutes for s in sessions if s.id != session.id and s.date == move_date
                       and (s.state in ACTIVE or s.state == 'completed'))
            if used + session.planned_minutes > capacity.get(move_date, 0):
                raise ValueError('That date has no free 30-minute slot.')
            session.date = move_date
        else:
            session.locked = name == 'lock'
    else:
        raise ValueError('Choose a valid session action.')
    session.version += 1
    db.session.add(SessionEvent(user_id=user.id, session_id=session.id, timestamp=now().replace(tzinfo=None),
                               request_id=request_id, payload_hash=digest,
                               description=f'Block #{session.id}: {name}; {session.actual_seconds:.0f} actual active seconds.'))
    db.session.flush()
    repair(user, 'evidence' if rating else name)
    return True
