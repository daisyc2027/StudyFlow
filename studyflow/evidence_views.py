from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import db
from .auth import login_required, owned
from .clock import today
from .inputs import RATINGS, integer, parse_date
from .models import PracticeTarget, EvidenceEntry, StudySession
from .services.evidence import SOURCES, record, target_priority

bp = Blueprint('evidence', __name__)


def marks(form):
    earned, possible = form.get('earned', '').strip(), form.get('possible', '').strip()
    if not earned and not possible:
        return None, None
    try:
        e, p = Decimal(earned), Decimal(possible)
        if not e.is_finite() or not p.is_finite() or not 0 <= e <= p or not 0 < p <= 100000:
            raise ValueError
        return float(e), float(p)
    except (InvalidOperation, ValueError):
        raise ValueError('Enter both marks: earned must be 0–possible, and possible must be positive (up to 100000).') from None


@bp.route('/target/<int:identifier>/evidence', methods=['GET', 'POST'])
@login_required
def evidence(identifier):
    target = owned(PracticeTarget, identifier)
    error = None
    if request.method == 'POST':
        try:
            form = request.form
            rating = form.get('rating') or None
            source = form.get('source')
            if rating and rating not in RATINGS or source not in SOURCES:
                raise ValueError('Choose a valid outcome and source.')
            day = parse_date(form.get('date'))
            if day > today(g.user):
                raise ValueError('Evidence cannot be dated in the future.')
            earned, possible = marks(form)
            note = form.get('note', '').strip()
            if len(note) > 1000 or (earned is not None and not note):
                raise ValueError('Describe the task/source for numeric marks (up to 1000 characters).')
            if rating is None and earned is None:
                raise ValueError('Choose a practice outcome or enter target-specific marks.')
            key = form.get('request_id', '')
            if not key or len(key) > 80:
                raise ValueError('Reload the form to obtain a valid request identity.')
            correction = integer(form['supersedes_id'], 'Correction', 1, 2147483647) if form.get('supersedes_id') else None
            if correction:
                owned(EvidenceEntry, correction)
            existing = db.session.scalar(db.select(EvidenceEntry).where(
                EvidenceEntry.user_id == g.user.id, EvidenceEntry.request_id == key))
            if not existing and integer(form.get('version', '0'), 'Version', 0, 2147483647) != target.version:
                abort(409, 'This target changed. Reload before recording evidence.')
            session_id = integer(form['session_id'], 'Completed session', 1, 2147483647) if form.get('session_id') else None
            if session_id:
                session = owned(StudySession, session_id)
                if session.target_id != target.id or session.state != 'completed' or not session.completed_at:
                    raise ValueError('Choose a completed session on this target.')
                from datetime import timezone
                from zoneinfo import ZoneInfo
                day = session.completed_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(g.user.timezone)).date()
            _, changed = record(target, request_id=key, date=day, rating=rating, source=source,
                                note=note, earned=earned, possible=possible, supersedes_id=correction, session_id=session_id)
            if changed:
                target.version += 1
                from .services.planning import repair
                repair(g.user, 'evidence')
            db.session.commit()
            flash('Evidence saved with its source. Completion alone is never an ability rating.')
            return redirect(url_for('evidence.evidence', identifier=identifier))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
    entries = list(db.session.scalars(db.select(EvidenceEntry).where(
        EvidenceEntry.user_id == g.user.id, EvidenceEntry.target_id == target.id)
        .order_by(EvidenceEntry.date.desc(), EvidenceEntry.id.desc())))
    from .services.reviews import summary
    return render_template('evidence.html', target=target, entries=entries, ratings=RATINGS,
                           sources=SOURCES, priority=target_priority(target, today(g.user)),
                           review=summary(target, today(g.user)),
                           completed_sessions=list(db.session.scalars(db.select(StudySession).where(
                               StudySession.target_id == target.id, StudySession.user_id == g.user.id,
                               StudySession.state == 'completed').order_by(StudySession.completed_at.desc()))),
                           day=today(g.user), request_id=request.form.get('request_id', str(uuid4())),
                           error=error), 422 if error else 200
