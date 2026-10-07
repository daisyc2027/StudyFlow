import hashlib
import json

from .priority import Observation, aggregate, effective_deadline, priority
from .. import db
from ..models import EvidenceEntry, StudySession, User

SOURCES = {'self_report': 'Student self-report', 'teacher_rating': 'Manually recorded teacher skill rating',
           'teacher_interpretation': 'Student interpretation of teacher feedback'}


def target_priority(target, day, last_study=None):
    if last_study is None:
        from datetime import timezone
        from zoneinfo import ZoneInfo
        user = db.session.get(User, target.user_id)
        completed = db.session.scalars(db.select(StudySession).where(
            StudySession.user_id == target.user_id, StudySession.target_id == target.id,
            StudySession.state == 'completed'))
        dates = [s.completed_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(user.timezone)).date()
                 if s.completed_at else s.date for s in completed]
        last_study = max(dates) if dates else None
    evidence = db.session.scalars(db.select(EvidenceEntry).where(
        EvidenceEntry.target_id == target.id, EvidenceEntry.user_id == target.user_id))
    need = aggregate(Observation(e.id, e.date, e.rating, e.superseded) for e in evidence)
    deadline = effective_deadline(target.exam.date if target.exam else None, target.deadline)
    return priority(need, day, last_study or target.created_date, deadline)


def record(target, *, request_id, date, rating, source, note='', earned=None, possible=None,
           supersedes_id=None, session_id=None):
    """Stage a source observation; caller commits evidence and any repair together."""
    if supersedes_id:
        original = db.session.get(EvidenceEntry, supersedes_id)
        if original and original.user_id == target.user_id and original.target_id == target.id:
            if session_id is not None and session_id != original.session_id:
                raise ValueError('A correction cannot change its completed session.')
            session_id = original.session_id
    if session_id is not None:
        session = db.session.get(StudySession, session_id)
        if not session or session.user_id != target.user_id or session.target_id != target.id or session.state != 'completed':
            raise ValueError('Choose a completed session on this target.')
    payload = dict(target_id=target.id, date=date.isoformat(), rating=rating, source=source,
                   note=note, earned=earned, possible=possible, supersedes_id=supersedes_id, session_id=session_id)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    existing = db.session.scalar(db.select(EvidenceEntry).where(
        EvidenceEntry.user_id == target.user_id, EvidenceEntry.request_id == request_id))
    if existing:
        if existing.payload_hash != digest:
            raise ValueError('This request identity was already used with different evidence.')
        return existing, False
    if supersedes_id:
        original = db.session.get(EvidenceEntry, supersedes_id)
        if original is None or original.user_id != target.user_id or original.target_id != target.id:
            raise ValueError('Correction must refer to evidence on this target.')
        if original.superseded:
            raise ValueError('This observation has already been corrected. Reload the evidence list.')
        original.superseded = True
    entry = EvidenceEntry(user_id=target.user_id, target_id=target.id, date=date, rating=rating,
                          source=source, note=note, earned=earned, possible=possible,
                          supersedes_id=supersedes_id, session_id=session_id, request_id=request_id, payload_hash=digest)
    db.session.add(entry)
    db.session.flush()
    return entry, True


def starting_evidence(target):
    if target.start_rating:
        record(target, request_id=f'starting:{target.id}', date=target.created_date,
               rating=target.start_rating, source='self_report', note='Starting practice need')
