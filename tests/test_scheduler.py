from collections import Counter
from datetime import date, timedelta

import pytest
from hypothesis import given, seed, settings, strategies as st

from conftest import post
from test_inputs import add_subject, add_target, weekly
from studyflow import db
from studyflow.models import StudySession
from studyflow.services.scheduler import Target, Booking, allocate

DAY = date(2030, 1, 7)


@pytest.mark.parametrize('minutes,count,remainder', [(0, 0, 0), (29, 0, 29), (30, 1, 0),
                                                    (45, 1, 15), (60, 2, 0)])
def test_capacity_block_examples(minutes, count, remainder):
    result = allocate(DAY, [Target(1, 120, 80, None)], {DAY: minutes}, [])
    assert len(result.assignments) == count
    assert result.days[0].used == 30 * count
    assert result.days[0].remainder == remainder
    assert sum(u.minutes for u in result.unallocated) == 120 - count * 30


def test_demand_deadline_ties_and_spacing():
    target = Target(1, 60, 80, DAY)
    bookings = [Booking(1, 1, DAY, 'completed'), Booking(2, 1, DAY + timedelta(days=10))]
    result = allocate(DAY, [target], {DAY: 120}, bookings)
    assert not result.assignments and not result.unallocated
    result = allocate(DAY, [Target(1, 1440, 90, None), Target(2, 60, 20, None)], {DAY: 30}, [])
    assert result.assignments[0].target_id == 1
    equal = [Target(2, 60, 50, None), Target(1, 60, 50, DAY)]
    result = allocate(DAY, equal, {DAY: 60}, [])
    assert [a.target_id for a in result.assignments] == [1, 2]
    assert allocate(DAY, list(reversed(equal)), {DAY: 60}, []) == result
    expired = allocate(DAY, [Target(1, 60, 100, DAY - timedelta(days=1))], {DAY: 60}, [])
    assert not expired.assignments and 'Overdue' in expired.unallocated[0].reason
    limited = allocate(DAY, [Target(1, 60, 50, DAY)], {DAY + timedelta(days=1): 120}, [])
    assert not limited.assignments and limited.unallocated[0].minutes == 60
    completed = allocate(DAY, [Target(1, 30, 50, None)], {DAY: 30}, [Booking(1, 1, DAY, 'completed')])
    assert not completed.assignments and completed.days[0].used == 30
    missed = allocate(DAY, [Target(1, 30, 50, None)], {DAY: 30}, [Booking(1, 1, DAY, 'missed')])
    assert len(missed.assignments) == 1
    assert len(allocate(DAY, [Target(1, 30, 50, None), Target(2, 30, 50, None)],
                        {DAY: 30}, []).assignments) == 1


@seed(4042030)
@settings(max_examples=120, deadline=None)
@given(st.lists(st.tuples(st.integers(1, 12), st.integers(0, 100), st.integers(-2, 10)), min_size=1, max_size=6),
       st.lists(st.integers(0, 240), min_size=7, max_size=7))
def test_generated_plan_invariants(data, minutes):
    targets = [Target(i, blocks * 30, score, DAY + timedelta(days=deadline))
               for i, (blocks, score, deadline) in enumerate(data, 1)]
    capacity = {DAY + timedelta(days=i): m for i, m in enumerate(minutes)}
    result = allocate(DAY, targets, capacity, [])
    assert allocate(DAY, targets, capacity, []) == result
    used, allocated = Counter(), Counter()
    for a in result.assignments:
        used[a.date] += 30
        allocated[a.target_id] += 30
        assert a.date <= targets[a.target_id - 1].deadline
    for day, total in used.items():
        assert total <= capacity[day]
    balances = {u.target_id: u.minutes for u in result.unallocated}
    for target in targets:
        assert allocated[target.id] + balances.get(target.id, 0) == target.budget
    saved = [Booking(i, a.target_id, a.date) for i, a in enumerate(result.assignments, 1)]
    assert not allocate(DAY, targets, capacity, saved).assignments


def test_generation_stable_ids_and_unplaced(user, app):
    add_subject(user)
    add_target(user, start_rating='needs', deadline='2030-01-07')
    add_target(user, topic='Probability', requested_minutes='60')
    weekly(user, 0)
    post(user, '/settings', {'action': 'override', 'date': '2030-01-07', 'minutes': '45'})
    before = user.get('/plan').text
    assert '0 / 45 min booked' in before
    assert '60 min' in before
    assert post(user, '/plan/generate').status_code == 302
    with app.app_context():
        sessions = list(db.session.scalars(db.select(StudySession)))
        assert len(sessions) == 1 and sessions[0].target_id == 1
        identifiers = [s.id for s in sessions]
    assert post(user, '/plan/generate').status_code == 302
    with app.app_context():
        assert [s.id for s in db.session.scalars(db.select(StudySession))] == identifiers
    assert '15 min below block size' in user.get('/plan').text
