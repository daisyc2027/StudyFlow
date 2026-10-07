from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from conftest import post
from studyflow import create_app, db
from studyflow.models import (Subject, FeedbackEntry, PracticeTarget, WeeklyAvailability,
                              DateAvailabilityOverride)


def add_subject(client, name='Synthetic maths'):
    return post(client, '/edit/subject', {'name': name, 'level': 'HL'})


def add_target(client, subject_id=1, **changes):
    data = {'subject_id': str(subject_id), 'topic': 'Integration', 'skill': 'Reasoning',
            'goal': 'Explain a worked example', 'requested_minutes': '60', 'start_rating': '',
            'exam_id': '', 'feedback_id': '', 'deadline': ''}
    return post(client, '/edit/target', {**data, **changes})


def weekly(client, minutes=60):
    return post(client, '/settings', {'action': 'weekly', **{f'day_{i}': str(minutes) for i in range(7)}})


def test_inputs_restart_edit_archive(user, app):
    assert add_subject(user).status_code == 302
    assert post(user, '/edit/feedback', {'subject_id': '1', 'title': 'Synthetic note',
                'teacher_text': 'Explain each step', 'overall_grade': '72% overall'}).status_code == 302
    assert post(user, '/edit/exam', {'subject_id': '1', 'title': 'Synthetic exam',
                                   'date': '2030-01-10'}).status_code == 302
    assert add_target(user, feedback_id='1', exam_id='1').status_code == 302
    assert add_target(user, topic='Probability', feedback_id='1').status_code == 302
    assert weekly(user).status_code == 302
    assert weekly(user, 90).status_code == 302
    assert post(user, '/settings', {'action': 'override', 'date': '2030-01-08', 'minutes': '0'}).status_code == 302
    restarted = create_app(dict(app.config))
    with restarted.app_context():
        assert db.session.query(PracticeTarget).count() == 2
        assert db.session.get(FeedbackEntry, 1).overall_grade == '72% overall'
        assert db.session.query(WeeklyAvailability).count() == 7
        assert db.session.get(DateAvailabilityOverride, 1).minutes == 0
        assert db.session.get(PracticeTarget, 1).start_rating is None
        db.session.remove()
        db.engine.dispose()
    assert post(user, '/edit/subject/1', {'name': 'Renamed', 'level': 'SL', 'version': '1'}).status_code == 302
    assert post(user, '/edit/subject/1', {'name': 'Stale', 'level': '', 'version': '1'}).status_code == 409
    assert post(user, '/edit/feedback/1', {'subject_id': '1', 'title': 'Revised',
                'teacher_text': 'Try another step', 'version': '1'}).status_code == 302
    assert post(user, '/edit/target/1', {'subject_id': '1', 'topic': 'Integration', 'skill': 'Reasoning',
                'goal': 'New goal', 'requested_minutes': '90', 'exam_id': '1',
                'feedback_id': '1', 'version': '1'}).status_code == 302
    for kind in ['target', 'feedback', 'subject']:
        assert post(user, f'/archive/{kind}/1').status_code == 302
    with app.app_context():
        assert db.session.get(PracticeTarget, 1).archived
        assert db.session.get(FeedbackEntry, 1).archived
        assert db.session.get(Subject, 1).archived
        assert db.session.get(PracticeTarget, 1).requested_minutes == 90


@pytest.mark.parametrize('value', ['-1', '1441', '1.5', 'abc', ''])
def test_invalid_availability_atomic(user, app, value):
    weekly(user, 60)
    data = {'action': 'weekly', **{f'day_{i}': '90' for i in range(7)}, 'day_5': value}
    assert post(user, '/settings', data).status_code == 422
    with app.app_context():
        assert all(row.minutes == 60 for row in db.session.scalars(db.select(WeeklyAvailability)))


def test_bad_dates_budgets_and_preserved_form(user):
    add_subject(user)
    for value in ['0', '31', '1500', 'bad']:
        result = add_target(user, requested_minutes=value, topic='Preserved topic')
        assert result.status_code == 422
        assert 'Preserved topic' in result.text
    assert post(user, '/edit/exam', {'subject_id': '1', 'title': 'Invalid',
                                   'date': '2030-02-30'}).status_code == 422
    assert post(user, '/settings', {'action': 'override', 'date': 'bad',
                                   'minutes': '0'}).status_code == 422


def test_owned_links_and_database_integrity(two_users, app):
    a, b = two_users
    add_subject(a, 'A subject')
    add_subject(b, 'B private subject')
    post(b, '/edit/feedback', {'subject_id': '2', 'title': 'B private feedback', 'teacher_text': 'Private'})
    post(b, '/edit/exam', {'subject_id': '2', 'title': 'B private exam', 'date': '2030-01-10'})
    add_target(b, subject_id=2)
    for kind in ['subject', 'feedback', 'exam', 'target']:
        identifier = 2 if kind == 'subject' else 1
        assert a.get(f'/edit/{kind}/{identifier}').status_code == 404
        assert post(a, f'/edit/{kind}/{identifier}', {'version': '1'}).status_code == 404
        assert post(a, f'/archive/{kind}/{identifier}').status_code == 404
    assert 'B private' not in a.get('/targets').text
    assert add_target(a, subject_id=2).status_code == 404
    assert add_target(a, exam_id='1').status_code == 404
    assert add_target(a, feedback_id='1').status_code == 404
    add_subject(a, 'A second subject')
    post(a, '/edit/exam', {'subject_id': '3', 'title': 'Other subject', 'date': '2030-01-10'})
    assert add_target(a, exam_id='2').status_code == 422
    with app.app_context():
        db.session.add(PracticeTarget(user_id=1, subject_id=2, topic='forged', goal='bad',
                                     created_date=date(2030, 1, 7), requested_minutes=60))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_opt_in_seed(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=['seed-demo', '--date', '2030-01-07', '--password',
                                'synthetic-password'])
    assert result.exit_code == 0
    with app.app_context():
        from studyflow.models import Exam
        assert db.session.query(PracticeTarget).count() == 3
        assert db.session.scalar(db.select(Exam)).date == date(2030, 1, 17)
        assert 'Synthetic' in db.session.scalar(db.select(FeedbackEntry)).title
    again = runner.invoke(args=['seed-demo', '--date', '2030-01-07', '--password',
                               'synthetic-password'])
    assert again.exit_code != 0
