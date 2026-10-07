from datetime import date, datetime, timedelta, timezone

from hypothesis import given, seed, settings, strategies as st

from studyflow import db
from studyflow.models import (StudySession, ReviewTask, PracticeTarget, User, EvidenceEntry)
from studyflow.services.scheduler import Target, Booking, allocate, horizon
from studyflow.services.repair import repair_plan
from studyflow.services.planning import repair, calculate
from test_adaptation import setup_plan, session_action
from test_review_persistence import enable
from conftest import post

DAY = date(2030, 1, 7)


def test_shared_balancing_not_before_and_deadline():
    jobs = [Target(1, 30, 100, None), Target(-1, 30, 100, None, not_before=DAY, balance_id=1),
            Target(2, 30, 80, None)]
    plan = allocate(DAY, jobs, {DAY: 60}, [])
    assert [a.target_id for a in plan.assignments] == [1, 2]
    due = Target(-1, 30, 100, DAY+timedelta(days=1), not_before=DAY+timedelta(days=2), balance_id=1)
    result = allocate(DAY, [due], {DAY+timedelta(days=2): 60}, [])
    assert not result.assignments and 'after the study deadline' in result.unallocated[0].reason
    future = Target(-1, 30, 100, None, not_before=DAY+timedelta(days=7), balance_id=1)
    assert 'beyond' in allocate(DAY, [future], {d: 60 for d in horizon(DAY)}, []).unallocated[0].reason
    protected = repair_plan(DAY, [due], {DAY: 30}, [Booking(1, -1, DAY, locked=True)])
    assert not protected.cancelled and protected.plan.conflicts


def test_actual_review_reservations_miss_disable_and_stability(user, app):
    setup_plan(user, budget='30')
    enable(app)
    session_action(user, 1, 'start', 1)
    session_action(user, 1, 'complete', 2, rating='confident')
    with app.app_context():
        review = db.session.get(StudySession, 2)
        assert review.kind == 'review' and review.date == date(2030, 1, 8)
        assert db.session.get(ReviewTask, 1).due_date == date(2030, 1, 8)
        assert not calculate(db.session.get(User, 1)).assignments
        assert repair(db.session.get(User, 1)) is None
    post(user, '/plan/generate')
    user.get('/plan')
    with app.app_context():
        assert db.session.query(StudySession).count() == 2
    app.config['CLOCK'] = lambda: datetime(2030, 1, 8, 12, tzinfo=timezone.utc)
    assert session_action(user, 2, 'miss', 1)[0].status_code == 302
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 1
        assert db.session.query(EvidenceEntry).count() == 1
        replacement = db.session.get(StudySession, 3)
        assert replacement.review_task_id == 1 and replacement.replacement_for_id == 2
        assert db.session.get(PracticeTarget, 1).requested_minutes == 30
    post(user, '/settings', {'action': 'override', 'date': '2030-01-08', 'minutes': '0'})
    with app.app_context():
        assert db.session.get(StudySession, 3).state == 'cancelled'
        assert db.session.get(StudySession, 4).date == date(2030, 1, 9)
    session_action(user, 4, 'lock', 1)
    enable(app, False)
    with app.app_context():
        repair(db.session.get(User, 1))
        assert db.session.get(StudySession, 4).locked
        assert calculate(db.session.get(User, 1), place=False).conflicts
        db.session.commit()
    session_action(user, 4, 'unlock', 2)
    with app.app_context():
        assert db.session.get(StudySession, 4).state == 'cancelled'
        assert db.session.get(ReviewTask, 1).state == 'cancelled'


@seed(7112030)
@settings(max_examples=180, deadline=None)
@given(st.lists(st.integers(0, 120), min_size=7, max_size=7),
       st.integers(-2, 10), st.integers(-1, 9), st.integers(0, 100))
def test_mixed_invariants(capacity, due_offset, deadline_offset, priority):
    dates = horizon(DAY)
    cap = dict(zip(dates, capacity))
    due, deadline = DAY+timedelta(days=due_offset), DAY+timedelta(days=deadline_offset)
    jobs = [Target(1, 90, priority, None),
            Target(-1, 30, priority, deadline, not_before=due, balance_id=1), Target(2, 60, 50, None)]
    plan = allocate(DAY, jobs, cap, [])
    assert plan == allocate(DAY, jobs, cap, [])
    for day in dates:
        assert sum(30 for a in plan.assignments if a.date == day) <= cap[day]
    assert sum(30 for a in plan.assignments if a.target_id == -1) <= 30
    assert sum(30 for a in plan.assignments if a.target_id == 1) <= 90
    assert all(due <= a.date <= deadline for a in plan.assignments if a.target_id == -1)
    bookings = [Booking(i, a.target_id, a.date, locked=i % 2 == 0) for i, a in enumerate(plan.assignments, 1)]
    changed = {d: max(0, m-30) for d, m in cap.items()}
    fixed = repair_plan(DAY, jobs, changed, bookings, evidence_only=True)
    assert len(fixed.cancelled) <= len(bookings)
    assert len(fixed.assignments) <= 336 + 2*len(bookings)
    assert not any(i in {b.id for b in bookings if b.locked} for i, _ in fixed.cancelled)
    retained = [b for b in bookings if b.id not in {i for i, _ in fixed.cancelled}]
    combined = retained + [Booking(-i, a.target_id, a.date) for i, a in enumerate(fixed.assignments, 1)]
    for day in dates:
        protected = sum(b.minutes for b in bookings if b.locked and b.date == day)
        assert sum(b.minutes for b in combined if b.date == day) <= max(changed[day], protected)
    assert all(due <= a.date <= deadline for a in fixed.assignments if a.target_id == -1)
    assert sum(b.minutes for b in combined if b.target_id == -1) <= 30
