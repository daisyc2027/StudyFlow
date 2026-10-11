from flask import Blueprint, flash, g, redirect, render_template, url_for

from . import db
from .auth import login_required
from .clock import today
from .services.planning import snapshot, calculate, generate
from .services.scheduler import horizon
from .models import SessionEvent, ReviewTask

bp = Blueprint('plan', __name__)


@bp.get('/plan')
@login_required
def plan():
    _, targets, sessions, _, _, _ = snapshot(g.user)
    result = calculate(g.user, place=False)
    days = horizon(today(g.user))
    visible = {day: [s for s in sessions if s.date == day and s.state != 'cancelled'] for day in days}
    names = {t.id: t for t in targets}
    for task in db.session.scalars(db.select(ReviewTask).where(ReviewTask.user_id == g.user.id)):
        names[-task.id] = names[task.target_id]
    return render_template('plan.html', days=result.days, sessions=visible, targets=names,
                           unallocated=result.unallocated, conflicts=result.conflicts,
                           suggested=len(calculate(g.user).assignments),
                           events=list(db.session.scalars(db.select(SessionEvent).where(SessionEvent.user_id == g.user.id).order_by(SessionEvent.id.desc()).limit(8))),
                           unfinished=[s for s in sessions if s.state in ('in_progress','paused') and s.date < today(g.user)])


@bp.post('/plan/generate')
@login_required
def generate_plan():
    result = generate(g.user)
    db.session.commit()
    flash(f'{len(result.assignments)} new sessions added.' if result.assignments else 'Your plan is up to date.')
    return redirect(url_for('plan.plan'))
