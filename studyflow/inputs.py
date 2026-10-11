from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import db
from .auth import login_required, owned
from .clock import today
from .models import (Subject, FeedbackEntry, Exam, PracticeTarget, WeeklyAvailability,
                     DateAvailabilityOverride)

bp = Blueprint('inputs', __name__)
KINDS = {'subject': Subject, 'feedback': FeedbackEntry, 'exam': Exam, 'target': PracticeTarget}
RATINGS = {'needs': 'Needs practice', 'developing': 'Developing', 'confident': 'Confident'}


def rows(model, active=True):
    query = db.select(model).where(model.user_id == g.user.id)
    if active and hasattr(model, 'archived'):
        query = query.where(model.archived.is_(False))
    return list(db.session.scalars(query.order_by(model.id)))


def integer(value, name, minimum=0, maximum=1440):
    try:
        number = int(value)
        if str(number) != str(value).strip() or not minimum <= number <= maximum:
            raise ValueError
        return number
    except (ValueError, TypeError):
        raise ValueError(f'{name} must be a whole number from {minimum} to {maximum}.') from None


def parse_date(value, name='Date', optional=False):
    if optional and not value:
        return None
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except (ValueError, TypeError):
        raise ValueError(f'{name} must be a valid date (YYYY-MM-DD).') from None


def text(form, key, label, limit, required=True):
    value = form.get(key, '').strip()
    if (required and not value) or len(value) > limit:
        raise ValueError(f'{label} is required and must be at most {limit} characters.')
    return value


def linked(model, value, subject_id=None):
    if not value:
        return None
    item = owned(model, integer(value, 'Selection', 1, 2147483647))
    if item.archived or (subject_id and item.subject_id != subject_id):
        raise ValueError('Choose an active record belonging to the same subject.')
    return item.id


@bp.get('/subjects')
@login_required
def subjects():
    return render_template('subjects.html', subjects=rows(Subject),
                           targets=rows(PracticeTarget), exams=rows(Exam),
                           archived=archived_rows())


def archived_rows():
    return {kind: [r for r in rows(model, False) if r.archived] for kind, model in KINDS.items()}


@bp.get('/subject/<int:identifier>')
@login_required
def subject_detail(identifier):
    subject = owned(Subject, identifier)
    return goal_page(subject)


def goal_page(subject=None):
    from .services.evidence import target_priority
    from .services.reviews import summary
    targets = [t for t in rows(PracticeTarget) if (not subject or t.subject_id == subject.id)
               and not t.subject.archived]
    return render_template('targets.html', targets=targets, subject=subject,
                           reviews={t.id: summary(t, today(g.user)) for t in targets},
                           priorities={t.id: target_priority(t, today(g.user)) for t in targets},
                           feedback=[r for r in rows(FeedbackEntry) if subject and r.subject_id == subject.id],
                           exams=[r for r in rows(Exam) if subject and r.subject_id == subject.id],
                           archived=archived_rows())


@bp.get('/targets')
@login_required
def targets():
    return goal_page()


@bp.route('/edit/<kind>', defaults={'identifier': None}, methods=['GET', 'POST'])
@bp.route('/edit/<kind>/<int:identifier>', methods=['GET', 'POST'])
@login_required
def edit(kind, identifier):
    if kind not in KINDS:
        abort(404)
    model = KINDS[kind]
    item = owned(model, identifier) if identifier else None
    error = None
    saved_upload = None
    if request.method == 'POST':
        try:
            if item and int(request.form.get('version', '0')) != item.version:
                abort(409, 'This record changed. Reload before saving again.')
            form = request.form
            values = {}
            if kind == 'subject':
                values['name'] = text(form, 'name', 'Subject name', 100)
                level = form.get('level', '')
                if level not in ('', 'HL', 'SL'):
                    raise ValueError('Choose HL, SL or no level.')
                values['level'] = level or None
            else:
                subject_id = linked(Subject, form.get('subject_id'))
                if not subject_id:
                    raise ValueError('Choose a subject first.')
                # Subject is fixed once linked, preserving historical relationships.
                if item and subject_id != item.subject_id:
                    raise ValueError('A saved record keeps its original subject. Create a new one to change subjects.')
                values['subject_id'] = subject_id
                if kind in ('feedback', 'exam'):
                    values['title'] = text(form, 'title', 'Title', 150)
                if kind == 'feedback':
                    values['teacher_text'] = text(form, 'teacher_text', 'Teacher feedback', 20000)
                    values['overall_grade'] = text(form, 'overall_grade', 'Overall grade', 80, False)
                if kind == 'exam':
                    values['date'] = parse_date(form.get('date'), 'Exam date')
                if kind == 'target':
                    values.update(topic=text(form, 'topic', 'Topic', 100),
                                  skill=text(form, 'skill', 'Skill', 100, False),
                                  goal=text(form, 'goal', 'Practice goal', 500),
                                  feedback_id=linked(FeedbackEntry, form.get('feedback_id'), subject_id),
                                  exam_id=linked(Exam, form.get('exam_id'), subject_id),
                                  deadline=parse_date(form.get('deadline'), 'Last study date', True))
                    minutes = integer(form.get('requested_minutes', '60'), 'Practice budget', 30)
                    if minutes % 30:
                        raise ValueError('Practice budget must be a multiple of 30 minutes.')
                    values['requested_minutes'] = minutes
                    if not item:
                        rating = form.get('start_rating', '')
                        if rating and rating not in RATINGS:
                            raise ValueError('Choose a valid starting practice need.')
                        values.update(start_rating=rating or None, created_date=today(g.user))
            if item:
                for key, value in values.items():
                    setattr(item, key, value)
                item.version += 1
            else:
                item = model(user_id=g.user.id, **values)
                db.session.add(item)
                db.session.flush()
                if kind == 'target':
                    from .services.evidence import starting_evidence
                    starting_evidence(item)
            if kind == 'feedback' and request.files.get('pdf') and request.files['pdf'].filename:
                from .attachments import save_reference
                item.attachment, saved_upload = save_reference(request.files['pdf'])
            from .services.planning import repair
            repair(g.user, 'input change')
            db.session.commit()
            flash(f'{"Study goal" if kind == "target" else kind.title()} saved.')
            return redirect(url_for('inputs.subject_detail', identifier=item.id if kind == 'subject' else item.subject_id))
        except ValueError as exc:
            db.session.rollback()
            if saved_upload:
                saved_upload.unlink(missing_ok=True)
            error = str(exc)
        except Exception:
            db.session.rollback()
            if saved_upload:
                saved_upload.unlink(missing_ok=True)
            raise
    values = request.form if request.method == 'POST' else {
        column.name: getattr(item, column.name) for column in model.__table__.columns
    } if item else {}
    if not item and request.method == 'GET' and kind != 'subject':
        values = dict(values)
        if request.args.get('subject_id'):
            values['subject_id'] = linked(Subject, request.args['subject_id'])
        if kind == 'target' and request.args.get('feedback_id'):
            values['feedback_id'] = linked(FeedbackEntry, request.args['feedback_id'], values.get('subject_id'))
    return render_template('edit.html', kind=kind, item=item, values=values, error=error,
                           subjects=rows(Subject), feedback=rows(FeedbackEntry), exams=rows(Exam),
                           ratings=RATINGS), 422 if error else 200


@bp.post('/archive/<kind>/<int:identifier>')
@login_required
def archive(kind, identifier):
    if kind not in KINDS:
        abort(404)
    item = owned(KINDS[kind], identifier)
    if not item.archived:
        item.archived = True
        item.version += 1
    from .services.planning import repair
    repair(g.user, 'archive')
    db.session.commit()
    flash('Archived. History kept.')
    return redirect(url_for('inputs.subjects') if kind == 'subject' else
                    url_for('inputs.subject_detail', identifier=item.subject_id))


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    error = None
    if request.method == 'POST':
        try:
            if request.form.get('settings_version') != str(g.user.settings_version):
                abort(409, 'Settings changed. Reload before saving again.')
            action = request.form.get('action')
            if action == 'weekly':
                # Validate the complete form before writing any day.
                minutes = [integer(request.form.get(f'day_{i}'), 'Daily availability') for i in range(7)]
                for day, value in enumerate(minutes):
                    row = db.session.scalar(db.select(WeeklyAvailability).where(
                        WeeklyAvailability.user_id == g.user.id, WeeklyAvailability.weekday == day))
                    if row is None:
                        row = WeeklyAvailability(user_id=g.user.id, weekday=day)
                        db.session.add(row)
                    row.minutes = value
            elif action == 'override':
                day = parse_date(request.form.get('date'))
                value = integer(request.form.get('minutes'), 'Available minutes')
                row = db.session.scalar(db.select(DateAvailabilityOverride).where(
                    DateAvailabilityOverride.user_id == g.user.id, DateAvailabilityOverride.date == day))
                if row is None:
                    row = DateAvailabilityOverride(user_id=g.user.id, date=day)
                    db.session.add(row)
                row.minutes = value
            elif action == 'remove_override':
                day = parse_date(request.form.get('date'))
                row = db.session.scalar(db.select(DateAvailabilityOverride).where(
                    DateAvailabilityOverride.user_id == g.user.id, DateAvailabilityOverride.date == day))
                if row:
                    db.session.delete(row)
            elif action == 'timezone':
                tz = request.form.get('timezone', '')
                ZoneInfo(tz)
                g.user.timezone = tz
            else:
                raise ValueError('Choose a settings action.')
            from .services.planning import repair
            repair(g.user, 'input change')
            g.user.settings_version += 1
            db.session.commit()
            flash('Settings saved.')
            return redirect(url_for('inputs.settings'))
        except (ValueError, ZoneInfoNotFoundError) as exc:
            db.session.rollback()
            error = 'Enter a valid IANA timezone.' if isinstance(exc, ZoneInfoNotFoundError) else str(exc)
    return render_template('settings.html', error=error,
                           weekly={row.weekday: row.minutes for row in rows(WeeklyAvailability)},
                           overrides=rows(DateAvailabilityOverride),
                           days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']), 422 if error else 200
