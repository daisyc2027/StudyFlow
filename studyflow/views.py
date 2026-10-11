from flask import Blueprint, g, render_template
from uuid import uuid4

from .auth import login_required
from .clock import today
from .inputs import RATINGS
from .services.evidence import SOURCES
from .services.progress import report

bp = Blueprint('main', __name__)


@bp.get('/')
@login_required
def dashboard():
    from .inputs import rows
    from .models import Subject
    from .services.planning import calculate
    data = report(g.user)
    plan = calculate(g.user, place=False)
    active = [i for i in data['items'] if not i.target.archived and not i.target.subject.archived]
    next_session = next(iter(data['unfinished'] or data['today_sessions']), None)
    return render_template('dashboard.html', report=data, day=today(g.user),
                           next_session=next_session, request_id=str(uuid4()),
                           subjects=rows(Subject), active_items=active,
                           has_time=any(d.capacity >= 30 for d in plan.days),
                           waiting_minutes=sum(item.minutes for item in plan.unallocated))


@bp.get('/progress')
@login_required
def progress():
    return render_template('progress.html', report=report(g.user), ratings=RATINGS, sources=SOURCES)


@bp.post('/target/<int:identifier>/add-practice')
@login_required
def add_practice(identifier):
    from flask import abort, flash, redirect, request, url_for
    from . import db
    from .auth import owned
    from .models import PracticeTarget
    from .services.planning import repair
    target = owned(PracticeTarget, identifier)
    if request.form.get('version') != str(target.version):
        abort(409, 'This target changed. Reload before adding practice.')
    if target.archived or target.subject.archived or target.requested_minutes >= 1440:
        abort(409, 'Practice is archived or the 1440-minute budget limit has been reached.')
    target.requested_minutes += 30
    target.version += 1
    repair(g.user, 'explicit extra practice')
    db.session.commit()
    flash('30 minutes added to initial practice.')
    return redirect(url_for('main.progress'))
