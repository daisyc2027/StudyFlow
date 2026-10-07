from flask import Blueprint, abort, flash, g, redirect, request, url_for

from . import db
from .auth import login_required, owned
from .inputs import integer
from .models import PracticeTarget
from .services.planning import repair
from .services.reviews import set_enabled

bp = Blueprint('reviews', __name__)


@bp.post('/target/<int:identifier>/reviews')
@login_required
def toggle(identifier):
    target = owned(PracticeTarget, identifier)
    try:
        key = request.form.get('request_id', '')
        if not key or len(key) > 80:
            raise ValueError('Reload for a valid request identity.')
        if request.form.get('enabled') not in ('on', 'off'):
            raise ValueError('Choose reviews on or off.')
        set_enabled(g.user, target, request.form['enabled'] == 'on',
                    integer(request.form.get('version'), 'Version', 1, 2147483647), key)
        repair(g.user, 'review mode change')
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        abort(409, str(exc))
    flash('Review preference saved. Follow-up review work is separate from the initial practice budget.')
    return redirect(url_for('inputs.targets'))
