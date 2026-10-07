import os
from datetime import date, datetime

import pytest
from playwright.sync_api import sync_playwright, expect
from sqlalchemy import text

from studyflow import create_app, db
from studyflow.models import (EvidenceEntry, PracticeTarget, ReviewState, ReviewTask, StudySession,
                              User, SessionEvent)
from studyflow.services.planning import calculate
from conftest import post, token
from test_adaptation import setup_plan, session_action
from test_review_interface import toggle
from test_evidence_priority import evidence_data


def clock(app, day):
    stamp = datetime.fromisoformat(f'2030-01-{day:02d}T12:00:00+00:00')
    app.config['CLOCK'] = lambda: stamp


def finish(client, identifier, rating=None):
    assert session_action(client, identifier, 'start', 1)[0].status_code == 302
    assert session_action(client, identifier, 'complete', 2, rating=rating or '')[0].status_code == 302


def assert_pending(app, interval, due, count=None):
    with app.app_context():
        state = db.session.get(ReviewState, 1)
        pending = list(db.session.scalars(db.select(ReviewTask).where(ReviewTask.state == 'pending')))
        assert state.interval == interval and state.recommended_due_date == due
        assert len(pending) == 1 and pending[0].due_date == due
        if count is not None:
            assert db.session.query(ReviewTask).count() == count
        return pending[0].id


def test_unrated_review_late_outcome_correction_daily_replay(user, app):
    setup_plan(user, budget='60')
    toggle(user, app)
    finish(user, 1, 'confident')
    # Another ordinary completion on the same actual local day changes the daily winner,
    # but cannot advance twice. Both outcomes remain in source history.
    finish(user, 2, 'confident')
    assert_pending(app, 1, date(2030, 1, 8), 1)
    clock(app, 8)
    user.get('/plan')
    finish(user, 3)  # no outcome is valid; does not recreate completed task
    with app.app_context():
        assert db.session.get(ReviewState, 1).awaiting_outcome
        assert db.session.query(ReviewTask).count() == 1
        assert db.session.get(ReviewTask, 1).state == 'completed'
        assert db.session.query(EvidenceEntry).count() == 2
    clock(app, 10)
    with app.app_context():
        version = db.session.get(PracticeTarget, 1).version
    late = evidence_data(version=version, session_id='3', rating='confident', date='2030-01-10')
    assert post(user, '/target/1/evidence', late).status_code == 302
    assert post(user, '/target/1/evidence', late).status_code == 302
    assert_pending(app, 3, date(2030, 1, 11), 2)  # Jan 8 actual practice, not Jan 10 submission
    with app.app_context():
        assert not db.session.get(ReviewState, 1).awaiting_outcome
        entry = db.session.scalar(db.select(EvidenceEntry).where(EvidenceEntry.session_id == 3))
        identifier, version = entry.id, db.session.get(PracticeTarget, 1).version
        completed = db.session.get(StudySession, 3).completed_at
    correction = evidence_data(version=version, rating='needs', supersedes_id=str(identifier), date='2030-01-01')
    assert post(user, '/target/1/evidence', correction).status_code == 302
    assert_pending(app, 1, date(2030, 1, 9), 2)
    with app.app_context():
        assert db.session.get(StudySession, 3).completed_at == completed
        assert db.session.query(EvidenceEntry).count() == 4
        current = db.session.scalar(db.select(StudySession).where(StudySession.state == 'planned'))
        assert current.id == 4 and current.date == date(2030, 1, 11)  # valid saved booking stays stable
    assert 'Delayed' in user.get('/targets').text
    assert 'Overdue' in user.get('/targets').text


def test_due_change_protects_active_paused_locked_and_deadline(user, app):
    setup_plan(user, budget='30')
    toggle(user, app)
    finish(user, 1, 'confident')
    clock(app, 8)
    user.get('/plan')
    assert session_action(user, 2, 'start', 1)[0].status_code == 302
    assert session_action(user, 2, 'pause', 2)[0].status_code == 302
    assert toggle(user, app, 'off')[0].status_code == 302
    with app.app_context():
        session = db.session.get(StudySession, 2)
        assert session.state == 'paused' and session.date == date(2030, 1, 8)
    assert 'Conflict:' in user.get('/plan').text
    assert session_action(user, 2, 'complete', 3, rating='confident')[0].status_code == 302
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 1  # disabled: no successor
    assert toggle(user, app)[0].status_code == 302
    assert_pending(app, 3, date(2030, 1, 11), 2)
    with app.app_context():
        version = db.session.get(PracticeTarget, 1).version
    post(user, '/edit/target/1', {'subject_id': '1', 'topic': 'Integration', 'goal': 'Explain',
        'requested_minutes': '30', 'version': str(version), 'deadline': '2030-01-10'})
    with app.app_context():
        assert db.session.get(ReviewTask, 2).due_date == date(2030, 1, 11)
        assert not list(db.session.scalars(db.select(StudySession).where(StudySession.state == 'planned')))
    assert 'after the study deadline' in user.get('/plan').text


def test_review_evidence_schedule_transaction_rolls_back(user, app, monkeypatch):
    setup_plan(user, budget='30')
    toggle(user, app)
    session_action(user, 1, 'start', 1)
    csrf = token(user)
    from studyflow.services import planning
    real_save = planning.save_assignment
    def fail_after_real_save(*args, **kwargs):
        real_save(*args, **kwargs)
        raise RuntimeError('Injected failure after real review scheduling')
    monkeypatch.setattr(planning, 'save_assignment', fail_after_real_save)
    with pytest.raises(RuntimeError, match='after real review'):
        user.post('/session/1', data={'csrf_token': csrf, 'request_id': 'failure', 'version': '2',
                                     'action': 'complete', 'rating': 'confident'})
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'in_progress'
        assert db.session.get(StudySession, 1).completed_at is None
        assert db.session.query(StudySession).count() == 1
        assert db.session.query(EvidenceEntry).count() == db.session.query(ReviewTask).count() == 0
        assert db.session.get(ReviewState, 1).step == -1
        assert db.session.query(SessionEvent).filter_by(request_id='failure').count() == 0


def test_teacher_general_evidence_not_completed_review_and_archive(user, app):
    setup_plan(user, budget='30')
    toggle(user, app)
    finish(user, 1)
    with app.app_context():
        version = db.session.get(PracticeTarget, 1).version
    for source, link in [('teacher_rating','1'), ('teacher_interpretation','1'), ('self_report','')]:
        assert post(user, '/target/1/evidence', evidence_data(version=version, source=source,
                    session_id=link, rating='confident')).status_code == 302
        version += 1
    with app.app_context():
        assert db.session.get(ReviewState, 1).step == -1
        assert db.session.query(ReviewTask).count() == 0
    post(user, '/target/1/evidence', evidence_data(version=version, session_id='1', rating='confident'))
    assert_pending(app, 1, date(2030, 1, 8), 1)
    post(user, '/archive/target/1')
    with app.app_context():
        assert db.session.get(StudySession, 2).state == 'cancelled'
        assert db.session.get(ReviewTask, 1).state == 'pending'
        assert db.session.get(PracticeTarget, 1).requested_minutes == 30
    assert 'Archived' in user.get('/progress').text


@pytest.mark.browser
def test_browser_complete_dated_review_loop(live_url, app):
    from test_browser import browser_subject, browser_exam, browser_target
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        try:
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors, requests = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            page.on('request', lambda req: requests.append(req.url))
            page.goto(live_url + '/register')
            page.get_by_label('Email', exact=True).fill('dated-review@example.test')
            page.get_by_label('Password', exact=True).fill('synthetic-password')
            page.get_by_role('button', name='Create account').click()
            page.goto(live_url + '/targets')
            browser_subject(page, 'Synthetic mathematics', 'HL')
            browser_subject(page, 'Synthetic economics', 'SL')
            browser_exam(page, '1', 'Synthetic later exam', '2030-03-01')
            browser_target(page, '1', 'Integration', '', '1')
            # Set initial budget to one block through the ordinary edit UI.
            page.get_by_role('link', name='Edit target', exact=True).click()
            page.get_by_text('Practice budget & supporting context', exact=True).click()
            page.get_by_label('Practice budget (minutes)', exact=True).fill('30')
            page.get_by_role('button', name='Save target').click()
            browser_target(page, '2', 'Price floors', '', '')
            page.locator('.card').filter(has=page.get_by_role('heading', name='Price floors · Explain reasoning')).get_by_role('link', name='Edit target', exact=True).click()
            page.get_by_text('Practice budget & supporting context', exact=True).click()
            page.get_by_label('Practice budget (minutes)', exact=True).fill('30')
            page.get_by_role('button', name='Save target').click()
            integration = page.locator('.card').filter(has=page.get_by_role('heading', name='Integration · Explain reasoning'))
            integration.get_by_role('button', name='Enable follow-up reviews').click()
            with app.app_context():
                assert db.session.get(ReviewState, 1).enabled
                assert db.session.get(ReviewState, 2) is None
            page.goto(live_url + '/settings')
            for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
                page.get_by_label(f'{day} minutes', exact=True).fill('60')
            page.get_by_role('button', name='Save weekly availability').click()
            page.goto(live_url + '/plan')
            page.get_by_role('button', name='Generate / Refresh plan').click()
            page.locator('.session').filter(has=page.get_by_role('heading', name='Integration · Explain reasoning')).get_by_role('link', name='Open session').click()
            page.get_by_role('button', name='Start session').click()
            page.get_by_role('button', name='Completed independently', exact=True).click()
            assert_pending(app, 1, date(2030, 1, 8), 1)
            page.goto(live_url + '/plan')
            page.locator('.session').filter(has=page.get_by_role('heading', name='Price floors · Explain reasoning')).get_by_role('link', name='Open session').click()
            page.get_by_role('button', name='Start session').click()
            page.get_by_role('button', name='Finish session', exact=True).click()
            # Fixed, independently calculated actual practice/due dates; no engine oracle.
            for practice_day, interval, due_day, outcome, task_count in [
                (8, 3, 11, 'Completed independently', 2),
                (11, 7, 18, 'Completed independently', 3),
                (18, 1, 19, 'Could not complete', 4)]:
                clock(app, practice_day)
                page.goto(live_url + '/plan')
                page.locator('.session').filter(has=page.get_by_role('link', name='Open session')).get_by_role('link', name='Open session').click()
                expect(page.get_by_text('Review · Separate recurring allocation', exact=True)).to_be_visible()
                page.get_by_role('button', name='Start session').click()
                page.get_by_role('button', name='Pause session').click()
                page.reload()
                page.get_by_role('button', name='Resume session').click()
                page.get_by_role('button', name=outcome, exact=True).click()
                assert_pending(app, interval, date(2030, 1, due_day), task_count)
            clock(app, 19)
            page.goto(live_url + '/plan')
            page.locator('.session').filter(has=page.get_by_role('link', name='Open session')).get_by_role('link', name='Open session').click()
            page.get_by_role('button', name='Mark missed').click()
            assert_pending(app, 1, date(2030, 1, 19), 4)
            with app.app_context():
                assert db.session.query(EvidenceEntry).count() == 4
                attempts = list(db.session.scalars(db.select(StudySession).where(StudySession.state == 'planned')))
                assert len(attempts) == 1 and attempts[0].review_task_id == 4
                assert db.session.get(StudySession, attempts[0].replacement_for_id).state == 'missed'
            page.goto(live_url + '/settings')
            for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
                page.get_by_label(f'{day} minutes', exact=True).fill('0')
            page.get_by_role('button', name='Save weekly availability').click()
            page.goto(live_url + '/plan')
            expect(page.get_by_text('Integration · Review', exact=True)).to_be_visible()
            page.get_by_role('button', name='Generate / Refresh plan').click()
            page.reload()
            page.get_by_role('button', name='Generate / Refresh plan').click()
            page.goto(live_url + '/progress')
            expect(page.get_by_text('90 min completed · 30 min outstanding · 0 min reserved', exact=True)).to_be_visible()
            expect(page.get_by_text('30 / 30 practice minutes satisfied', exact=True)).to_have_count(2)
            page.screenshot(path=f'docs/evidence/review-loop-{engine}-desktop.png', full_page=True)
            page.set_viewport_size({'width': 375, 'height': 812})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=f'docs/evidence/review-loop-{engine}-mobile.png', full_page=True)
            page.get_by_role('button', name='Log out').click()
            page.get_by_label('Email', exact=True).fill('dated-review@example.test')
            page.get_by_label('Password', exact=True).fill('synthetic-password')
            page.get_by_role('button', name='Log in', exact=True).click()
            page.goto(live_url + '/targets')
            expect(page.get_by_role('heading', name='Follow-up reviews: On')).to_have_count(1)
            expect(page.get_by_role('heading', name='Follow-up reviews: Off')).to_have_count(1)
            assert not errors and all(url.startswith(live_url) for url in requests)
            assert_pending(app, 1, date(2030, 1, 19), 4)
            restarted = create_app(dict(app.config))
            with restarted.app_context():
                assert sum(t.requested_minutes for t in db.session.scalars(db.select(PracticeTarget))) == 60
                assert db.session.query(ReviewTask).count() == 4
                assert db.session.query(EvidenceEntry).count() == 4
                assert db.session.execute(text('PRAGMA foreign_key_check')).all() == []
                assert calculate(db.session.get(User, 1), place=False).days[0].used == 0
                db.session.remove()
                db.engine.dispose()
        finally:
            browser.close()


def test_later_rated_practice_resumes_after_unrated_review_at_equal_timestamp(user, app):
    setup_plan(user,budget='30')
    toggle(user,app)
    finish(user,1,'confident')
    clock(app,8)
    user.get('/plan')
    finish(user,2)
    with app.app_context():
        assert db.session.get(ReviewState,1).awaiting_outcome
        version = db.session.get(PracticeTarget,1).version
    assert post(user,'/target/1/add-practice',{'version':str(version)}).status_code == 302
    # Same injected second, later stable session ID: a genuine later rated practice.
    finish(user,3,'confident')
    with app.app_context():
        assert not db.session.get(ReviewState,1).awaiting_outcome
    assert_pending(app,3,date(2030,1,11),2)


def test_actual_completion_timezone_not_scheduled_or_submission_date(user, app):
    setup_plan(user,budget='30')
    toggle(user,app)
    session_action(user,1,'start',1)
    session_action(user,1,'pause',2)
    stamp = datetime.fromisoformat('2030-01-07T17:00:00+00:00')  # Jan 8 Hong Kong
    app.config['CLOCK'] = lambda: stamp
    assert session_action(user,1,'complete',3,rating='confident')[0].status_code == 302
    assert_pending(app,1,date(2030,1,9),1)
    with app.app_context():
        assert db.session.get(StudySession,1).date == date(2030,1,7)
        assert db.session.get(EvidenceEntry,1).date == date(2030,1,8)
        assert db.session.get(ReviewState,1).last_rated_date == date(2030,1,8)
