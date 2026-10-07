from datetime import date, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings, seed, strategies as st

from conftest import post
from test_inputs import add_subject, add_target
from studyflow import db
from studyflow.models import EvidenceEntry, PracticeTarget
from studyflow.services.priority import (Observation, Need, aggregate, priority, effective_deadline)
from studyflow.services.evidence import target_priority

DAY = date(2030, 1, 7)


def observations(*ratings):
    return [Observation(i, DAY, value) for i, value in enumerate(ratings, 1)]


def test_independent_recency_unknown_and_corrections():
    assert aggregate([]) == Need(50, False, 0)
    assert aggregate(observations('needs')).value == 100
    assert aggregate(observations('needs', 'developing')).value == pytest.approx(220 / 3)
    assert aggregate(observations('needs', 'developing', 'confident')).value == pytest.approx(280 / 6)
    assert aggregate(list(reversed(observations('needs', 'developing', 'confident')))).value == pytest.approx(280 / 6)
    assert aggregate(observations('confident', 'needs', 'developing', 'confident')).value == pytest.approx(280 / 6)
    assert aggregate([Observation(1, DAY, 'needs', True), Observation(2, DAY, 'confident')]).value == 20
    reports = observations('needs', 'developing')
    assert aggregate(reports + [Observation(99, DAY + timedelta(days=1), None)]) == aggregate(reports)
    assert aggregate([Observation(10, DAY - timedelta(days=1), 'confident'),
                      Observation(1, DAY, 'needs')]).value == pytest.approx(220 / 3)


def test_priority_exact_deadlines_waiting():
    result = priority(Need(100, True, 1), DAY, DAY - timedelta(days=7), DAY + timedelta(days=30))
    assert result.value == 80
    assert result.urgency == result.waiting == 50
    assert priority(Need(100, True, 1), DAY, DAY, None).value == 60
    assert priority(Need(100, True, 1), DAY, DAY - timedelta(days=40), DAY + timedelta(days=90)).value == 70
    assert effective_deadline(DAY, None) == DAY - timedelta(days=1)
    expired = priority(Need(20, True, 1), DAY, DAY, effective_deadline(DAY, None))
    assert expired.overdue and expired.urgency == 100
    assert not priority(Need(20, True, 1), DAY, DAY, DAY).overdue
    assert priority(Need(20, True, 1), DAY, DAY + timedelta(days=1), None).waiting == 0


@seed(20300107)
@settings(max_examples=150, deadline=None)
@given(st.floats(min_value=0, max_value=100, allow_nan=False), st.integers(-100, 100), st.integers(-100, 100))
def test_priority_bounds_monotonic(need, days, waiting):
    deadline = DAY + timedelta(days=days)
    last = DAY - timedelta(days=waiting)
    result = priority(Need(need, True, 1), DAY, last, deadline)
    assert 0 <= result.value <= 100
    assert priority(Need(min(100, need + 5), True, 1), DAY, last, deadline).value >= result.value
    assert priority(Need(need, True, 1), DAY, last, deadline - timedelta(days=1)).value >= result.value


def evidence_data(version=1, **changes):
    return {'request_id': str(uuid4()), 'version': str(version), 'date': str(DAY),
            'rating': 'needs', 'source': 'self_report', 'note': 'Synthetic practice', **changes}


def test_stored_evidence_retry_correction(user, app):
    add_subject(user)
    add_target(user)
    data = evidence_data()
    assert post(user, '/target/1/evidence', data).status_code == 302
    assert post(user, '/target/1/evidence', data).status_code == 302
    assert post(user, '/target/1/evidence', {**data, 'rating': 'confident'}).status_code == 422
    assert post(user, '/target/1/evidence', evidence_data(version=2, rating='confident',
                                                       supersedes_id='1', source='teacher_rating')).status_code == 302
    with app.app_context():
        assert db.session.query(EvidenceEntry).count() == 2
        assert db.session.get(EvidenceEntry, 1).superseded
        score = target_priority(db.session.get(PracticeTarget, 1), DAY)
        assert score.need.value == 20 and score.need.count == 1
    assert 'Manually recorded teacher skill rating' in user.get('/target/1/evidence').text
    assert post(user, '/target/1/evidence', evidence_data(version=3, supersedes_id='1')).status_code == 422
    assert post(user, '/target/1/evidence', evidence_data(version=1)).status_code == 409


def test_marks_do_not_rate_free_text_or_overall_grade(user, app):
    add_subject(user)
    post(user, '/edit/feedback', {'subject_id': '1', 'title': 'Synthetic',
                                'teacher_text': 'Excellent understanding', 'overall_grade': '90%'})
    add_target(user, feedback_id='1')
    assert post(user, '/target/1/evidence', evidence_data(rating='', earned='8', possible='10')).status_code == 302
    with app.app_context():
        assert target_priority(db.session.get(PracticeTarget, 1), DAY).need == Need(50, False, 0)
    for earned, possible in [('11', '10'), ('-1', '10'), ('5', '0'), ('NaN', '10'), ('2', '')]:
        response = post(user, '/target/1/evidence', evidence_data(version=2, earned=earned, possible=possible))
        assert response.status_code == 422
        assert 'Synthetic practice' in response.text
    assert post(user, '/target/1/evidence', evidence_data(version=2, date='2030-01-08')).status_code == 422


def test_starting_report_and_owner(two_users, app):
    a, b = two_users
    add_subject(b)
    add_target(b, start_rating='developing')
    assert a.get('/target/1/evidence').status_code == 404
    assert post(a, '/target/1/evidence', evidence_data()).status_code == 404
    with app.app_context():
        target = db.session.get(PracticeTarget, 1)
        assert target_priority(target, DAY).need.value == 60
        assert db.session.scalar(db.select(EvidenceEntry)).source == 'self_report'
