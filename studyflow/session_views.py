from uuid import uuid4

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import db
from .auth import login_required, owned
from .clock import today
from .evidence_views import marks
from .inputs import RATINGS, integer, parse_date
from .models import StudySession
from .services.lifecycle import action, active_seconds

bp = Blueprint('sessions', __name__)


@bp.route('/session/<int:identifier>', methods=['GET', 'POST'])
@login_required
def session_detail(identifier):
    session = owned(StudySession, identifier)
    error = None
    if request.method == 'POST':
        try:
            key = request.form.get('request_id', '')
            if not key or len(key) > 80:
                raise ValueError('Reload to obtain a valid request identity.')
            name = 'complete' if 'outcome' in request.form else request.form.get('action')
            rating = request.form.get('outcome') or request.form.get('rating') or None
            if rating and rating not in RATINGS:
                raise ValueError('Choose a valid practice outcome.')
            earned, possible = marks(request.form)
            note = request.form.get('note', '').strip()
            if len(note) > 1000:
                raise ValueError('Keep context within 1000 characters.')
            version = integer(request.form.get('version'), 'Version', 1, 2147483647)
            action(g.user, session, name, version, key, rating=rating, earned=earned, possible=possible,
                   note=note, move_date=parse_date(request.form.get('move_date'), optional=True))
            db.session.commit()
            flash('Practice finished.' if name == 'complete' else 'Session updated.')
            return redirect(url_for('sessions.session_detail', identifier=identifier))
        except ValueError as exc:
            db.session.rollback()
            error = str(exc)
            if 'changed' in error or 'already used' in error:
                abort(409, error)
    return render_template('session.html', session=session, seconds=active_seconds(session),
                           request_id=request.form.get('request_id', str(uuid4())), ratings=RATINGS,
                           day=today(g.user), error=error,
                           finishing=(request.args.get('finish') == '1' or
                                      request.form.get('action') == 'complete' or 'outcome' in request.form)
                           and session.state in ('in_progress', 'paused')), 422 if error else 200
