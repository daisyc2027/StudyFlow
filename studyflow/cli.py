from datetime import date, timedelta

import click
from werkzeug.security import generate_password_hash

from . import db
from .models import User, Subject, Exam, FeedbackEntry, PracticeTarget, WeeklyAvailability


def register_cli(app):
    @app.cli.command('seed-demo')
    @click.option('--date', 'seed_date', required=True, help='Synthetic starting date, YYYY-MM-DD')
    @click.option('--email', default='demo@example.test')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def seed_demo(seed_date, email, password):
        """Create an opt-in account with clearly synthetic records. Never overwrite a user."""
        day = date.fromisoformat(seed_date)
        if db.session.scalar(db.select(User).where(User.email == email)):
            raise click.ClickException('Account already exists; no data changed.')
        if len(password) < 10:
            raise click.ClickException('Password must have at least 10 characters.')
        user = User(email=email, password_hash=generate_password_hash(password), timezone='Asia/Hong_Kong')
        db.session.add(user)
        db.session.flush()
        for name, topics in [('Mathematics', ['Integration', 'Probability']),
                             ('Economics', ['Price floors'])]:
            subject = Subject(user_id=user.id, name=name, level='HL')
            db.session.add(subject)
            db.session.flush()
            exam = Exam(user_id=user.id, subject_id=subject.id, title='Synthetic practice exam',
                        date=day + timedelta(days=10))
            feedback = FeedbackEntry(user_id=user.id, subject_id=subject.id,
                                     title='Synthetic feedback', teacher_text='Synthetic: practise explaining each step.')
            db.session.add_all([exam, feedback])
            db.session.flush()
            for topic in topics:
                target = PracticeTarget(user_id=user.id, subject_id=subject.id,
                    feedback_id=feedback.id, exam_id=exam.id, topic=topic, skill='Explain reasoning',
                    goal='Practise one worked example and explain each step.', start_rating='developing',
                    requested_minutes=60, created_date=day)
                db.session.add(target)
                db.session.flush()
                from .services.evidence import starting_evidence
                starting_evidence(target)
        for weekday in range(7):
            db.session.add(WeeklyAvailability(user_id=user.id, weekday=weekday, minutes=60))
        db.session.commit()
        click.echo(f'Synthetic account created: {email}. Seed date: {day}.')

    @app.cli.command('reconcile')
    @click.option('--email', required=True)
    def reconcile_command(email):
        """Reconcile one local account's past planned sessions, without a daemon."""
        from sqlalchemy import text
        from .services.planning import reconcile, repair
        db.session.execute(text('BEGIN IMMEDIATE'))
        user = db.session.scalar(db.select(User).where(User.email == email))
        if not user:
            raise click.ClickException('No such account.')
        reconcile(user)
        repair(user, 'explicit reconciliation')
        db.session.commit()
        click.echo('Reconciled past planned work; active/paused sessions remain unfinished.')
