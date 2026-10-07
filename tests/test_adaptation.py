from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from conftest import post, token
from test_inputs import add_subject, add_target, weekly
from test_evidence_priority import evidence_data
from studyflow import db
from studyflow.models import StudySession, PracticeTarget, EvidenceEntry, User, SessionEvent
from studyflow.services.priority import Need
from studyflow.services.evidence import target_priority
from studyflow.services.scheduler import Target, Booking, allocate
from studyflow.services.repair import repair_plan
from studyflow.services.planning import repair

DAY = date(2030, 1, 7)


def setup_plan(user, budget='60', rating=''):
    add_subject(user)
    add_target(user, requested_minutes=budget, start_rating=rating)
    weekly(user, 60)
    post(user, '/plan/generate')


def session_action(user, identifier, name, version, **changes):
    data = {'action': name, 'version': str(version), 'request_id': str(uuid4()), **changes}
    return post(user, f'/session/{identifier}', data), data


def test_pause_timing_refresh_duplicate_complete_no_rating(user, app):
    setup_plan(user)
    start = datetime(2030, 1, 7, 12, tzinfo=timezone.utc)
    assert session_action(user, 1, 'start', 1)[0].status_code == 302
    app.config['CLOCK'] = lambda: start + timedelta(minutes=10)
    assert session_action(user, 1, 'pause', 2)[0].status_code == 302
    app.config['CLOCK'] = lambda: start + timedelta(minutes=40)
    assert '10.0 min' in user.get('/session/1').text
    assert session_action(user, 1, 'resume', 3)[0].status_code == 302
    app.config['CLOCK'] = lambda: start + timedelta(minutes=45)
    response, data = session_action(user, 1, 'complete', 4)
    assert response.status_code == 302
    assert post(user, '/session/1', data).status_code == 302
    with app.app_context():
        session = db.session.get(StudySession, 1)
        assert session.actual_seconds == 900
        assert session.state == 'completed'
        assert db.session.query(EvidenceEntry).count() == 0
        target = db.session.get(PracticeTarget, 1)
        assert target.requested_minutes == 60
        assert target_priority(target, DAY).need == Need(50, False, 0)
        assert db.session.query(SessionEvent).filter_by(session_id=1).count() == 4
    assert session_action(user, 1, 'start', 5)[0].status_code == 422
    assert session_action(user, 2, 'pause', 1)[0].status_code == 422
    assert session_action(user, 2, 'start', 2)[0].status_code == 409


def test_miss_skip_replacement_no_debt(user, app):
    setup_plan(user, rating='needs')
    response, data = session_action(user, 1, 'miss', 1)
    assert response.status_code == 302
    assert post(user, '/session/1', data).status_code == 302
    with app.app_context():
        sessions = list(db.session.scalars(db.select(StudySession)))
        assert sum(s.planned_minutes for s in sessions if s.state == 'planned') == 60
        assert len(sessions) == 3
        assert db.session.get(StudySession, 3).replacement_for_id == 1
        assert db.session.get(PracticeTarget, 1).requested_minutes == 60
        assert target_priority(db.session.get(PracticeTarget, 1), DAY).need.value == 100
        before = [(s.id, s.state, s.date) for s in sessions]
        assert repair(db.session.get(User, 1)) is None
        assert [(s.id, s.state, s.date) for s in db.session.scalars(db.select(StudySession))] == before
    response, data = session_action(user, 3, 'skip', 1)
    assert response.status_code == 302
    assert post(user, '/session/3', data).status_code == 302
    with app.app_context():
        assert db.session.get(StudySession, 4).replacement_for_id == 3
        assert db.session.get(PracticeTarget, 1).requested_minutes == 60


def test_capacity_change_locks_active_and_budget(user, app):
    setup_plan(user, budget='90')
    # Two today, one tomorrow. Protect today's work and make its conflict explicit.
    assert session_action(user, 1, 'start', 1)[0].status_code == 302
    assert session_action(user, 2, 'lock', 1)[0].status_code == 302
    assert post(user, '/settings', {'action': 'override', 'date': str(DAY), 'minutes': '0'}).status_code == 302
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'in_progress'
        assert db.session.get(StudySession, 2).locked
        assert db.session.get(StudySession, 2).date == DAY
    assert 'Conflict:' in user.get('/plan').text
    assert session_action(user, 3, 'move', 1, move_date=str(DAY))[0].status_code == 422
    assert session_action(user, 3, 'move', 1, move_date='2030-01-10')[0].status_code == 302
    # Requested budget can be reduced; protected allocations conflict rather than being destroyed.
    assert post(user, '/edit/target/1', {'subject_id': '1', 'topic': 'Integration', 'goal': 'Explain',
                'requested_minutes': '30', 'version': '1'}).status_code == 302
    assert 'protected reservations exceed' in user.get('/plan').text
    with app.app_context():
        assert db.session.get(StudySession, 3).state == 'cancelled'


def test_reconcile_next_day_preserves_unfinished(user, app):
    setup_plan(user)
    session_action(user, 1, 'start', 1)
    app.config['CLOCK'] = lambda: datetime(2030, 1, 8, 12, tzinfo=timezone.utc)
    html = user.get('/plan').text
    assert 'Unfinished in progress block from' in html
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'in_progress'
        assert db.session.get(StudySession, 2).state == 'missed'
        assert db.session.get(StudySession, 3).replacement_for_id == 2
        count = db.session.query(StudySession).count()
    user.get('/plan')
    with app.app_context():
        assert db.session.query(StudySession).count() == count
        assert db.session.query(SessionEvent).filter_by(request_id='reconcile:2').count() == 1
        assert db.session.query(EvidenceEntry).count() == 0


def test_bounded_displacement_and_no_space():
    targets = [Target(1, 30, 90, DAY), Target(2, 30, 20, None)]
    bookings = [Booking(1, 1, DAY - timedelta(days=1), 'missed'), Booking(2, 2, DAY)]
    result = repair_plan(DAY, targets, {DAY: 30}, bookings)
    assert [a.target_id for a in result.assignments] == [1]
    assert [i for i, _ in result.cancelled] == [2]
    assert result.plan.unallocated[0].target_id == 2 and result.plan.unallocated[0].minutes == 30
    locked = repair_plan(DAY, targets, {DAY: 30}, [Booking(2, 2, DAY, locked=True)])
    assert not locked.cancelled and not locked.assignments
    assert locked.plan.unallocated[0].target_id == 1
    empty = repair_plan(DAY, targets, {DAY: 0}, [])
    assert sum(u.minutes for u in empty.plan.unallocated) == 60
    no_gap = repair_plan(DAY, [Target(1, 30, 29, DAY), targets[1]], {DAY: 30}, [Booking(2, 2, DAY)])
    assert not no_gap.cancelled
    cap = repair_plan(DAY, [Target(1, 120, 100, DAY), Target(2, 120, 10, DAY)],
                      {DAY: 120}, [Booking(i, 2, DAY) for i in range(1, 5)], evidence_only=True)
    assert len(cap.cancelled) == len(cap.assignments) == 2
    assert cap.plan.unallocated


def test_evidence_rebalances_and_rollback(user, app, monkeypatch):
    add_subject(user)
    add_target(user, requested_minutes='30', start_rating='needs')
    add_target(user, requested_minutes='30', topic='Probability', start_rating='confident')
    weekly(user, 0)
    post(user, '/settings', {'action': 'override', 'date': str(DAY), 'minutes': '30'})
    post(user, '/plan/generate')
    # Make the initially allocated target lower priority and the unallocated target higher.
    assert post(user, '/target/1/evidence', evidence_data(rating='confident', supersedes_id='1')).status_code == 302
    assert post(user, '/target/2/evidence', evidence_data(rating='needs', supersedes_id='2')).status_code == 302
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'cancelled'
        assert db.session.get(StudySession, 2).target_id == 2
        original_ids = [s.id for s in db.session.scalars(db.select(StudySession))]
        original_count = db.session.query(EvidenceEntry).count()
        target_version = db.session.get(PracticeTarget, 2).version
    csrf = token(user)
    from studyflow.services import planning
    def fail(*args, **kwargs):
        raise RuntimeError('Injected transaction failure')
    monkeypatch.setattr(planning, 'repair', fail)
    with pytest.raises(RuntimeError, match='Injected'):
        user.post('/target/2/evidence', data={'csrf_token': csrf, **evidence_data(version=target_version)})
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == original_count
        assert db.session.get(PracticeTarget, 2).version == target_version
        assert [s.id for s in db.session.scalars(db.select(StudySession))] == original_ids


def test_deadline_repair_overdue_and_owner(two_users, app):
    a, b = two_users
    setup_plan(b, budget='90')
    assert a.get('/session/1').status_code == 404
    assert post(a, '/session/1', {'action': 'complete', 'version': '1', 'request_id': str(uuid4())}).status_code == 404
    assert post(b, '/edit/target/1', {'subject_id': '1', 'topic': 'Integration', 'goal': 'Explain',
                'requested_minutes': '90', 'deadline': '2030-01-06', 'version': '1'}).status_code == 302
    assert 'Overdue' in b.get('/plan').text
    with app.app_context():
        assert all(s.state == 'cancelled' for s in db.session.scalars(db.select(StudySession)))
        assert db.session.get(PracticeTarget, 1).requested_minutes == 90
        assert db.session.query(EvidenceEntry).count() == 0


def test_completion_outcome_once(user, app):
    setup_plan(user, budget='30')
    session_action(user, 1, 'start', 1)
    result, data = session_action(user, 1, 'complete', 2, rating='needs', earned='4', possible='10', note='Synthetic worksheet')
    assert result.status_code == 302
    assert post(user, '/session/1', data).status_code == 302
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == 1
        entry = db.session.scalar(db.select(EvidenceEntry))
        assert entry.session_id == 1 and entry.earned == 4 and entry.source == 'self_report'
        sessions = list(db.session.scalars(db.select(StudySession)))
        assert len(sessions) == 1 and sessions[0].state == 'completed'
        assert not allocate(DAY, [Target(1, 30, 100, None)], {DAY: 60},
                            [Booking(1, 1, DAY, 'completed')]).assignments


def test_late_completion_waiting_uses_local_actual_date(user, app):
    setup_plan(user, budget='30')
    session_action(user, 1, 'start', 1)
    session_action(user, 1, 'pause', 2)
    app.config['CLOCK'] = lambda: datetime(2030, 1, 8, 17, tzinfo=timezone.utc)
    # Hong Kong has already reached Jan 9; unfinished work remains completable.
    assert session_action(user, 1, 'complete', 3)[0].status_code == 302
    with app.app_context():
        result = target_priority(db.session.get(PracticeTarget, 1), date(2030, 1, 9))
        assert result.waiting == 0
        assert db.session.get(StudySession, 1).date == DAY


def test_past_missed_high_need_displaces_future_lower_need(user, app):
    add_subject(user)
    add_target(user, requested_minutes='30', start_rating='needs')
    add_target(user, requested_minutes='30', start_rating='confident', topic='Probability')
    weekly(user, 0)
    for day in ['2030-01-07', '2030-01-08']:
        post(user, '/settings', {'action': 'override', 'date': day, 'minutes': '30'})
    post(user, '/plan/generate')
    app.config['CLOCK'] = lambda: datetime(2030, 1, 8, 12, tzinfo=timezone.utc)
    user.get('/plan')
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'missed'
        assert db.session.get(StudySession, 2).state == 'cancelled'
        replacement = db.session.get(StudySession, 3)
        assert replacement.target_id == 1 and replacement.replacement_for_id == 1
        assert replacement.date == date(2030, 1, 8)
        assert db.session.query(EvidenceEntry).count() == 2  # Only original explicit reports.
        assert all(t.requested_minutes == 30 for t in db.session.scalars(db.select(PracticeTarget)))
    assert 'Probability' in user.get('/plan').text
    assert post(user, '/settings', {'action': 'override', 'date': '2030-01-08', 'minutes': '0'}).status_code == 302
    with app.app_context():
        assert db.session.get(StudySession, 3).state == 'cancelled'
        assert not list(db.session.scalars(db.select(StudySession).where(StudySession.state == 'planned')))
