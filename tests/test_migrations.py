from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError

from studyflow import create_app, db
from studyflow.models import User, PracticeTarget, EvidenceEntry
from conftest import register
from test_adaptation import setup_plan, session_action


def migration_app(tmp_path):
    return create_app({'TESTING': True, 'SECRET_KEY': 'migration-only',
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / "migrated.sqlite"}',
        'UPLOAD_FOLDER': str(tmp_path / 'uploads'),
        'CLOCK': lambda: datetime(2030, 1, 7, 12, tzinfo=timezone.utc)})


def test_fresh_migrations_manual_workflow_seed_and_restart(tmp_path):
    app = migration_app(tmp_path)
    result = app.test_cli_runner().invoke(args=['db', 'upgrade'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.query(User).count() == 0
        assert inspect(db.engine).get_check_constraints('evidence_entry')
    client = app.test_client()
    register(client, 'fresh@example.test')
    setup_plan(client, budget='30')
    session_action(client, 1, 'start', 1)
    session_action(client, 1, 'complete', 2, rating='developing')
    result = app.test_cli_runner().invoke(args=['seed-demo', '--date', '2030-01-07',
                                       '--password', 'synthetic-password'])
    assert result.exit_code == 0, result.output
    assert app.test_cli_runner().invoke(args=['reconcile', '--email', 'fresh@example.test']).exit_code == 0
    assert app.test_cli_runner().invoke(args=['db', 'check']).exit_code == 0
    restarted = create_app(dict(app.config))
    with restarted.app_context():
        assert db.session.query(User).count() == 2
        assert db.session.query(PracticeTarget).count() == 4
        assert db.session.get(EvidenceEntry, 1).rating == 'developing'
        db.session.remove()
        db.engine.dispose()


def test_upgrade_preserves_existing_user_initial_evidence_and_checks(tmp_path):
    app = migration_app(tmp_path)
    result = app.test_cli_runner().invoke(args=['db', 'upgrade', '0742c7029ce4'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        db.session.execute(text("INSERT INTO user (id,email,password_hash,timezone) VALUES (1,'older@example.test','synthetic','Asia/Hong_Kong')"))
        db.session.execute(text("INSERT INTO subject (id,user_id,name,archived,version) VALUES (1,1,'Synthetic retained subject',0,1)"))
        db.session.execute(text("INSERT INTO practice_target (id,user_id,subject_id,topic,skill,goal,start_rating,requested_minutes,created_date,archived,version) VALUES (1,1,1,'Retained topic','','Retained goal','needs',60,'2030-01-07',0,1)"))
        db.session.commit()
    result = app.test_cli_runner().invoke(args=['db', 'upgrade'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        user = db.session.get(User, 1)
        assert user.settings_version == 1 and not user.plan_started
        assert db.session.get(PracticeTarget, 1).goal == 'Retained goal'
        entry = db.session.get(EvidenceEntry, 1)
        assert entry.rating == 'needs' and entry.source == 'self_report'
        assert entry.date == date(2030, 1, 7)
        db.session.add(EvidenceEntry(user_id=1, target_id=1, date=date(2030, 1, 7), source='self_report',
                      note='Invalid marks', earned=12, possible=10, request_id='invalid', payload_hash='invalid'))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        assert db.session.query(EvidenceEntry).count() == 1
