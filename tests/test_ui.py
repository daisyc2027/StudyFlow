"""Presentation journeys still use real SQLite, lifecycle and scheduler services."""
import re
import os

import pytest
from playwright.sync_api import sync_playwright, expect

from conftest import post
from test_inputs import add_subject, add_target, weekly
from test_adaptation import setup_plan, session_action


def test_today_setup_and_direct_start(user, app):
    assert 'Add your first subject' in user.get('/').text
    add_subject(user)
    assert 'Add a study goal' in user.get('/').text
    add_target(user)
    assert 'Set study time' in user.get('/').text
    weekly(user)
    assert 'Create my plan' in user.get('/').text
    post(user, '/plan/generate')
    html = user.get('/').text
    assert 'Start practice' in html
    key = re.search(r'name="request_id" value="([^"]+)"', html).group(1)
    response = post(user, '/session/1', {'request_id': key, 'version': '1', 'action': 'start'})
    assert response.status_code == 302
    assert 'Continue practice' in user.get('/').text
    session_action(user, 1, 'pause', 2)
    assert 'Resume practice' in user.get('/').text


def test_today_surfaces_unfinished_before_planned(user, app):
    from datetime import datetime, timezone
    setup_plan(user)
    session_action(user, 1, 'start', 1)
    app.config['CLOCK'] = lambda: datetime(2030, 1, 8, 12, tzinfo=timezone.utc)
    html = user.get('/').text
    assert 'Unfinished from 2030-01-07' in html
    assert 'Continue practice' in html
    assert html.count('aria-current=page') == 1


def test_subject_detail_context_and_ownership(two_users):
    a, b = two_users
    add_subject(a, 'A subject')
    add_subject(b, 'B private subject')
    add_target(a)
    add_target(b, subject_id=2, topic='Private topic')
    assert 'A subject' in a.get('/subjects').text
    assert 'B private' not in a.get('/subjects').text
    assert a.get('/subject/2').status_code == 404
    assert 'Private topic' not in a.get('/subject/1').text
    for kind in ['feedback', 'exam', 'target']:
        assert a.get(f'/edit/{kind}?subject_id=2').status_code == 404
        assert 'value="1" selected' in a.get(f'/edit/{kind}?subject_id=1').text
    response = post(a, '/edit/feedback', {'subject_id': '1', 'title': 'Original note',
                                        'teacher_text': 'Keep this exact teacher text. ' * 15})
    assert response.location.endswith('/subject/1')
    assert 'Read original feedback' in a.get('/subject/1').text
    assert ('Keep this exact teacher text. ' * 15).strip() in a.get('/subject/1').text


def test_finish_check_in_get_preserves_state_and_invalid_marks(user, app):
    from studyflow import db
    from studyflow.models import StudySession, EvidenceEntry
    setup_plan(user, budget='30')
    session_action(user, 1, 'start', 1)
    response = user.get('/session/1?finish=1')
    assert 'How did it go?' in response.text
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'in_progress'
        assert db.session.query(EvidenceEntry).count() == 0

    key = re.search(r'name="request_id" value="([^"]+)"', response.text).group(1)
    response = post(user, '/session/1', {'action': 'complete', 'version': '2',
        'request_id': key, 'earned': '9', 'possible': '8', 'note': 'Keep my context'})
    assert response.status_code == 422
    assert 'How did it go?' in response.text and 'Keep my context' in response.text
    with app.app_context():
        assert db.session.get(StudySession, 1).state == 'in_progress'
        assert db.session.query(EvidenceEntry).count() == 0

def test_today_existing_plan_without_capacity_is_not_onboarding(user):
    setup_plan(user)
    weekly(user, 0)
    html = user.get('/').text
    assert 'Build your first week' not in html
    assert '60 min waiting' in html
    assert 'Review waiting work' in html


def test_today_includes_waiting_review_separately(user, app):
    from test_review_interface import toggle
    setup_plan(user, budget='30')
    toggle(user, app)
    session_action(user, 1, 'start', 1)
    session_action(user, 1, 'complete', 2, rating='confident')
    weekly(user, 0)
    html = user.get('/').text
    assert '30 min waiting' in html
    assert 'Build your first week' not in html



@pytest.mark.browser
def test_today_direct_start_and_mobile_navigation(live_url, app):
    from conftest import register
    client = app.test_client()
    register(client, 'today@example.test')
    setup_plan(client)
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.goto(live_url + '/login')
        page.get_by_label('Email', exact=True).fill('today@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        expect(page.get_by_role('navigation').get_by_role('link')).to_have_count(4)
        page.screenshot(path=f'docs/evidence/today-{engine}-desktop.png', full_page=True)
        page.set_viewport_size({'width': 320, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=f'docs/evidence/today-{engine}-mobile.png', full_page=True)
        page.get_by_role('button', name='Start practice').click()
        expect(page.get_by_role('button', name='Pause practice')).to_be_visible()
        page.get_by_role('button', name='Pause practice').click()
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        page.get_by_role('button', name='Resume practice').click()
        expect(page.get_by_role('button', name='Pause practice')).to_be_visible()
        page.screenshot(path=f'docs/evidence/focus-{engine}-mobile.png', full_page=True)
        page.get_by_role('link', name='Finish practice').click()
        expect(page.get_by_role('heading', name='How did it go?')).to_be_visible()
        page.screenshot(path=f'docs/evidence/finish-{engine}-mobile.png', full_page=True)
        page.get_by_role('link', name='Back to practice').click()
        expect(page.get_by_role('button', name='Pause practice')).to_be_visible()
        page.get_by_role('link', name='Finish practice').click()
        page.get_by_role('button', name='Finish without a rating', exact=True).click()
        expect(page.get_by_text('completed', exact=True)).to_be_visible()
        from studyflow import db
        from studyflow.models import StudySession, EvidenceEntry, PracticeTarget
        with app.app_context():
            assert db.session.get(StudySession, 1).state == 'completed'
            assert db.session.query(EvidenceEntry).count() == 0
            assert db.session.get(PracticeTarget, 1).requested_minutes == 60
        browser.close()


@pytest.mark.browser
def test_today_first_use_keyboard_and_unrated_finish(live_url, app):
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        page = browser.new_page(viewport={'width': 375, 'height': 812})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(live_url + '/register')
        page.get_by_label('Email', exact=True).fill('first-use@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Create account').click()
        page.get_by_role('link', name='Add your first subject').click()
        page.get_by_label('Subject name').fill('Biology')
        page.get_by_role('button', name='Save subject').click()
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        page.get_by_role('link', name='Add a study goal').click()
        expect(page.get_by_label('Subject', exact=True)).to_have_value('1')
        page.get_by_label('Topic', exact=True).fill('Cell membranes')
        page.get_by_label('Study goal').fill('Explain transport across a membrane.')
        page.get_by_label('Initial practice (minutes)', exact=True).fill('30')
        page.get_by_role('button', name='Save study goal').click()
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        page.get_by_role('link', name='Set study time').click()
        page.get_by_label('Monday minutes', exact=True).fill('30')
        page.get_by_role('button', name='Save weekly availability').click()
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        page.get_by_role('button', name='Create my plan').click()
        expect(page.locator('.session')).to_have_count(1)
        page.locator('.date-strip a').last.click()
        assert page.url.endswith('#day-2030-01-13')
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        # Native links/forms support keyboard activation without a frontend framework.
        start = page.get_by_role('button', name='Start practice')
        start.focus()
        page.keyboard.press('Enter')
        expect(page.get_by_role('button', name='Pause practice')).to_be_visible()
        page.get_by_role('link', name='Finish practice').click()
        page.get_by_role('button', name='Finish without a rating', exact=True).click()
        page.get_by_role('navigation').get_by_role('link', name='Progress', exact=True).click()
        expect(page.get_by_text('30 / 30 min initial practice completed', exact=True)).to_be_visible()
        expect(page.get_by_text('No outcomes reported. Ratings are optional.', exact=True)).to_be_visible()
        page.get_by_role('navigation').get_by_role('link', name='Today', exact=True).click()
        expect(page.get_by_role('heading', name='You’re clear for today')).to_be_visible()
        assert not errors
        from studyflow import db
        from studyflow.models import EvidenceEntry, PracticeTarget, StudySession
        with app.app_context():
            assert db.session.query(EvidenceEntry).count() == 0
            assert db.session.get(PracticeTarget, 1).requested_minutes == 30
            assert db.session.get(StudySession, 1).state == 'completed'
        browser.close()
