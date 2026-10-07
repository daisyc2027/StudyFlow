from flask import Blueprint, g, render_template

from .auth import login_required
from .clock import today
from .inputs import RATINGS
from .services.evidence import SOURCES
from .services.progress import report

bp = Blueprint('main', __name__)


@bp.get('/')
@login_required
def dashboard():
    return render_template('dashboard.html', report=report(g.user), day=today(g.user))


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
    flash('30 minutes added to this practice budget.')
    return redirect(url_for('main.progress'))
