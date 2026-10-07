import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from studyflow import db
from studyflow.models import (User, PracticeTarget, ReviewTask, ReviewState, StudySession,
                              SessionReview, EvidenceEntry, SessionEvent)
from studyflow.services.review import RatedPractice, replay
from studyflow.services.planning import repair, calculate
from conftest import post, token
from test_adaptation import setup_plan, session_action
from test_review_interface import toggle
from test_review_loop import clock, finish, assert_pending
from test_evidence_priority import evidence_data
from test_inputs import add_target, add_subject


def test_every_transition_and_corrected_backdated_replay():
    base = datetime(2030, 1, 1, 12)
    # Independent expected table indexed by old step -1,0,1,2,3,4.
    expected = {'needs': [0,0,0,0,0,0], 'developing': [0,0,0,1,2,3],
                'confident': [0,1,2,3,4,4]}
    for old in range(-1, 5):
        history = [RatedPractice(i+1, i+1, base+timedelta(days=i), 'confident') for i in range(old+1)]
        for rating, steps in expected.items():
            result = replay(history + [RatedPractice(99,99,base+timedelta(days=10),rating)], 'UTC')
            assert result.step == steps[old+1]
    history = [RatedPractice(1,1,base,'confident'),
               RatedPractice(2,2,base+timedelta(days=1),'confident'),
               RatedPractice(3,3,base+timedelta(days=2),'confident')]
    assert replay(history, 'UTC').interval == 7
    corrected = [history[0], RatedPractice(2,2,history[1].completed_at,'confident',True), history[2],
                 RatedPractice(4,2,history[1].completed_at,'needs')]
    assert replay(corrected, 'UTC').interval == 3
    assert replay(corrected, 'UTC').due_date == date(2030,1,6)


def test_due_update_locked_conflict_and_future_horizon(user, app):
    setup_plan(user, budget='60')
    toggle(user, app)
    finish(user, 1, 'confident')
    assert session_action(user, 3, 'lock', 1)[0].status_code == 302
    # Leave second ordinary attempt paused across dates; its later actual completion
    # advances due from Jan 8 to Jan 12 without rewriting locked Jan 8 review.
    session_action(user, 2, 'start', 1)
    session_action(user, 2, 'pause', 2)
    clock(app, 9)
    assert session_action(user, 2, 'complete', 3, rating='confident')[0].status_code == 302
    assert_pending(app, 3, date(2030,1,12),1)
    with app.app_context():
        assert db.session.get(StudySession, 3).date == date(2030,1,8)
        assert db.session.get(StudySession, 3).state == 'missed'  # app-visit reconciliation preserves history
    clock(app,12)
    # Build explicit completed practice at distinct actual dates to reach 30-day cap;
    # this fixture uses real evidence+services, never scheduled synthetic success chains.
    with app.app_context():
        from studyflow.services.evidence import record
        target = db.session.get(PracticeTarget, 1)
        for identifier, day in enumerate([10,11,12], 1):
            session = StudySession(user_id=1,target_id=1,date=date(2030,1,day),state='completed',
                completed_at=datetime(2030,1,day,12),reason='Explicit synthetic historical practice')
            db.session.add(session)
            db.session.flush()
            record(target, request_id=f'actual-{identifier}',date=date(2030,1,day),
                   rating='confident',source='self_report',session_id=session.id)
        repair(db.session.get(User, 1), 'evidence')
        db.session.commit()
        state = db.session.get(ReviewState, 1)
        assert state.interval == 30 and state.recommended_due_date == date(2030,2,11)
        pending = db.session.scalar(db.select(ReviewTask).where(ReviewTask.state == 'pending'))
        assert pending.due_date == date(2030,2,11)
        plan = calculate(db.session.get(User,1),place=False)
        assert any('beyond' in u.reason for u in plan.unallocated if u.target_id < 0)
    before = user.get('/targets').text
    assert 'Beyond this seven-day horizon' in before
    post(user, '/plan/generate')
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 1


def test_same_date_locked_due_change_conflict(user, app):
    setup_plan(user, budget='60')
    toggle(user, app)
    finish(user,1,'confident')
    session_action(user,3,'lock',1)
    session_action(user,2,'start',1)
    session_action(user,2,'pause',2)
    # POST direct mutation avoids visit reconciliation; Jan 8 locked review still future
    # when completion after midnight Jan 8 changes due to Jan 11.
    clock(app,8)
    from studyflow.services.lifecycle import action
    with app.app_context():
        action(db.session.get(User,1),db.session.get(StudySession,2),'complete',3,'late-locked',rating='confident')
        db.session.commit()
        assert db.session.get(StudySession,3).locked and db.session.get(StudySession,3).date == date(2030,1,8)
        assert db.session.get(StudySession,3).state == 'planned'
        assert calculate(db.session.get(User,1),place=False).conflicts
        assert db.session.query(ReviewTask).count() == 1
    assert 'Conflict:' in user.get('/plan').text
    assert session_action(user,3,'start',2)[0].status_code == 422
    assert session_action(user,3,'unlock',2)[0].status_code == 302
    with app.app_context():
        assert db.session.get(StudySession,3).state == 'cancelled'
        assert db.session.get(StudySession,4).date == date(2030,1,11)


def test_review_concurrent_completion_exact_retry(user, app):
    setup_plan(user,budget='30')
    toggle(user,app)
    session_action(user,1,'start',1)
    csrf = token(user)
    with user.session_transaction() as session:
        cookies = dict(session)
    clients = [app.test_client(), app.test_client()]
    for client in clients:
        with client.session_transaction() as session:
            session.update(cookies)
    data = {'csrf_token':csrf,'version':'2','request_id':'concurrent-review','action':'complete','rating':'confident'}
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda client: client.post('/session/1',data=data).status_code,clients))
    assert results == [302,302]
    assert_pending(app,1,date(2030,1,8),1)
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == 1
        assert db.session.query(StudySession).count() == 2
        assert db.session.query(SessionEvent).filter_by(request_id='concurrent-review').count() == 1
    clock(app,8)
    user.get('/plan')
    session_action(user,2,'start',1)
    data = {**data,'csrf_token':token(user),'request_id':'concurrent-review-next'}
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda client: client.post('/session/2',data=data).status_code,clients))
    assert results == [302,302]
    assert_pending(app,3,date(2030,1,11),2)
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == 2
        assert db.session.query(StudySession).count() == 3
        assert db.session.query(SessionEvent).filter_by(request_id='concurrent-review-next').count() == 1


def test_composite_review_links_and_late_session_ownership(two_users, app):
    a,b = two_users
    setup_plan(a,budget='30')
    add_target(a,requested_minutes='30',topic='Other')
    toggle(a,app)
    finish(a,1,'confident')
    with app.app_context():
        version = db.session.get(PracticeTarget,1).version
    assert post(b,'/target/1/evidence',evidence_data(version=version,session_id='1')).status_code == 404
    add_subject(b,'Other account subject')
    add_target(b,subject_id=2,requested_minutes='30')
    assert post(b,'/target/3/evidence',evidence_data(session_id='1')).status_code == 404
    with app.app_context():
        # Cross-user source is rejected by owner/target composite FK.
        db.session.add(ReviewTask(user_id=2,target_id=1,due_date=date(2030,1,8),source_evidence_id=1,state='completed'))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
        db.session.add(ReviewTask(user_id=1,target_id=2,due_date=date(2030,1,8),source_evidence_id=1))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
        session = StudySession(user_id=1,target_id=2,date=date(2030,1,8),reason='Other target')
        db.session.add(session)
        db.session.flush()
        db.session.add(SessionReview(session_id=session.id,user_id=1,target_id=2,task_id=1))
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


@pytest.mark.parametrize('scenario',range(12))
def test_seeded_real_database_mutation_invariants(user, app, scenario):
    rng = random.Random(7122030+scenario)
    setup_plan(user,budget='60')
    toggle(user,app)
    finish(user,1,'confident')
    immutable = {}
    for iteration in range(8):
        clock(app,8+iteration)
        user.get('/plan')
        if rng.randrange(3) == 0:
            post(user,'/settings',{'action':'override','date':f'2030-01-{8+iteration:02d}',
                                  'minutes':str(rng.choice([0,15,30,60]))})
        with app.app_context():
            current = db.session.scalar(db.select(StudySession).where(StudySession.date == date(2030,1,8+iteration),
                                        StudySession.state == 'planned').order_by(StudySession.id))
            identifier, version = (current.id,current.version) if current else (None,None)
        if identifier:
            name = rng.choice(['miss','skip','start'])
            assert session_action(user,identifier,name,version)[0].status_code == 302
            if name == 'start':
                session_action(user,identifier,'complete',version+1,rating=rng.choice(['','needs','developing','confident']))
        with app.app_context():
            target,account = db.session.get(PracticeTarget,1),db.session.get(User,1)
            assert target.requested_minutes == 60
            assert db.session.query(ReviewTask).filter_by(state='pending').count() <= 1
            ordinary = [s for s in db.session.scalars(db.select(StudySession)) if s.kind == 'practice']
            completed = sum(30 for s in ordinary if s.state == 'completed')
            reserved = sum(30 for s in ordinary if s.state in ('planned','in_progress','paused'))
            assert reserved <= max(0,60-completed)
            for task in db.session.scalars(db.select(ReviewTask)):
                attempts = list(db.session.scalars(db.select(StudySession).join(SessionReview,
                    StudySession.id == SessionReview.session_id).where(SessionReview.task_id == task.id)))
                assert sum(s.state in ('planned','in_progress','paused') for s in attempts) <= 1
                assert sum(s.state == 'completed' for s in attempts) <= 1
            plan = calculate(account,place=False)
            assert all(d.used <= d.capacity for d in plan.days)
            for session in db.session.scalars(db.select(StudySession)):
                if session.id in immutable:
                    assert (session.date,session.completed_at,session.state,session.actual_seconds) == immutable[session.id]
                if session.state == 'completed':
                    immutable[session.id] = (session.date,session.completed_at,session.state,session.actual_seconds)
            before = [(s.id,s.date,s.state) for s in db.session.scalars(db.select(StudySession))]
            events = db.session.query(SessionEvent).count()
            assert repair(account) is None
            assert [(s.id,s.date,s.state) for s in db.session.scalars(db.select(StudySession))] == before
            assert db.session.query(SessionEvent).count() == events
            assert db.session.execute(text('PRAGMA foreign_key_check')).all() == []
