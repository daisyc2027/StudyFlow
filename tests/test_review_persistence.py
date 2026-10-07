from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from studyflow import db
from studyflow.models import (User, PracticeTarget, EvidenceEntry, ReviewTask, ReviewState,
                              StudySession, SessionReview)
from studyflow.services.reviews import set_enabled, sync_target
from studyflow.services.evidence import record
from studyflow.services.progress import report
from conftest import post
from test_adaptation import setup_plan, session_action
from test_migrations import migration_app


def enable(app, value=True, key=None):
    with app.app_context():
        user, target = db.session.get(User, 1), db.session.get(PracticeTarget, 1)
        version = target.version
        key = key or str(uuid4())
        set_enabled(user, target, value, version, key)
        db.session.commit()
        return version, key


def test_enable_existing_outcome_uniqueness_correction_and_separate_credit(user, app):
    setup_plan(user, budget='30')
    session_action(user, 1, 'start', 1)
    session_action(user, 1, 'complete', 2, rating='confident')
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 0
    version, key = enable(app)
    with app.app_context():
        target, account = db.session.get(PracticeTarget, 1), db.session.get(User, 1)
        assert not set_enabled(account, target, True, version, key)
        sync_target(target)
        state = db.session.get(ReviewState, 1)
        task = db.session.scalar(db.select(ReviewTask))
        assert state.enabled and state.interval == 1 and task.due_date == date(2030, 1, 8)
        assert db.session.query(ReviewTask).count() == 1
        db.session.add(ReviewTask(user_id=1, target_id=1, due_date=date(2030, 1, 9)))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
        target = db.session.get(PracticeTarget, 1)
        old = db.session.scalar(db.select(EvidenceEntry))
        correction, _ = record(target, request_id='correction', date=date(2030, 1, 7), rating='needs',
                               source='self_report', supersedes_id=old.id)
        sync_target(target)
        assert correction.session_id == 1 and old.superseded
        assert db.session.query(ReviewTask).count() == 1
        assert task.source_evidence_id == correction.id
        # Add a real completed review attempt: it credits its own obligation only.
        session = StudySession(user_id=1, target_id=1, date=date(2030, 1, 8), state='completed',
                               completed_at=__import__('datetime').datetime(2030, 1, 8, 12), reason='Synthetic review')
        db.session.add(session)
        db.session.flush()
        db.session.add(SessionReview(session_id=session.id, user_id=1, target_id=1, task_id=task.id))
        db.session.flush()
        sync_target(target)
        assert state.awaiting_outcome and task.state == 'completed'
        assert db.session.query(ReviewTask).count() == 1
        summary = report(account)
        assert summary['budget'] == summary['credited'] == 30 and summary['outstanding'] == 0
        db.session.commit()
    user.get('/progress')
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 1


def test_no_data_disabling_ownership_and_rollback(two_users, app):
    a, b = two_users
    setup_plan(a, budget='30')
    enable(app)
    with app.app_context():
        state = db.session.get(ReviewState, 1)
        assert state.step == -1 and state.recommended_due_date is None
        assert not state.awaiting_outcome and db.session.query(ReviewTask).count() == 0
        with pytest.raises(ValueError):
            set_enabled(db.session.get(User, 2), db.session.get(PracticeTarget, 1), True, 2, 'foreign')
        db.session.rollback()
        set_enabled(db.session.get(User, 1), db.session.get(PracticeTarget, 1), False, 2, 'rollback')
        db.session.rollback()
        assert db.session.get(ReviewState, 1).enabled
    assert b.get('/target/1/evidence').status_code == 404
    assert post(b, '/session/1', {'action': 'start', 'version': '1', 'request_id': 'foreign'}).status_code == 404
    enable(app, False)
    with app.app_context():
        assert not db.session.get(ReviewState, 1).enabled
        assert db.session.get(PracticeTarget, 1).requested_minutes == 30


def test_review_upgrade_retains_populated_base_and_defaults_off(tmp_path):
    app = migration_app(tmp_path)
    runner = app.test_cli_runner()
    assert runner.invoke(args=['db', 'upgrade', '393457d12ea6']).exit_code == 0
    from sqlalchemy import text
    with app.app_context():
        db.session.execute(text("INSERT INTO user (id,email,password_hash,timezone,plan_started,settings_version) VALUES (1,'upgrade@example.test','synthetic','UTC',1,1)"))
        db.session.execute(text("INSERT INTO subject (id,user_id,name,archived,version) VALUES (1,1,'Retained',0,1)"))
        db.session.execute(text("INSERT INTO practice_target (id,user_id,subject_id,topic,skill,goal,requested_minutes,created_date,archived,version) VALUES (1,1,1,'Retained','','Retained',30,'2030-01-07',0,1)"))
        db.session.execute(text("INSERT INTO study_session (id,user_id,target_id,date,planned_minutes,actual_seconds,state,locked,version,reason,completed_at) VALUES (1,1,1,'2030-01-07',30,90,'completed',0,3,'Retained','2030-01-07 12:00:00')"))
        db.session.execute(text("INSERT INTO evidence_entry (user_id,target_id,date,rating,source,note,session_id,superseded,request_id,payload_hash) VALUES (1,1,'2030-01-07','confident','self_report','Retained',1,0,'retained','retained')"))
        db.session.commit()
    result = runner.invoke(args=['db', 'upgrade'])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.get(StudySession, 1).actual_seconds == 90
        assert db.session.get(StudySession, 1).kind == 'practice'
        assert db.session.query(ReviewState).count() == db.session.query(ReviewTask).count() == 0
        assert db.session.execute(text('PRAGMA foreign_key_check')).all() == []
    enable(app)
    with app.app_context():
        assert db.session.get(ReviewState, 1).recommended_due_date == date(2030, 1, 8)
    assert runner.invoke(args=['db', 'check']).exit_code == 0
