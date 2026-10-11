import os
from datetime import date
from uuid import uuid4

import pytest
from playwright.sync_api import sync_playwright, expect

from studyflow import db
from studyflow.models import PracticeTarget, ReviewTask, ReviewState, StudySession
from conftest import post
from test_adaptation import setup_plan, session_action
from test_evidence_priority import evidence_data


def toggle(client, app, enabled='on', target_id=1, **changes):
    with app.app_context():
        version = db.session.get(PracticeTarget, target_id).version
    data = {'enabled': enabled, 'request_id': str(uuid4()), 'version': str(version), **changes}
    return post(client, f'/target/{target_id}/reviews', data), data


def test_review_routes_no_data_capacity_late_outcome_disable(user, app):
    setup_plan(user, budget='30')
    response, data = toggle(user, app)
    assert response.status_code == 302
    assert post(user, '/target/1/reviews', data).status_code == 302
    assert post(user, '/target/1/reviews', {**data, 'enabled': 'off'}).status_code == 409
    assert 'Rated practice needed' in user.get('/targets').text
    session_action(user, 1, 'start', 1)
    session_action(user, 1, 'complete', 2)  # valid, does not invent evidence
    with app.app_context():
        assert db.session.query(ReviewTask).count() == 0
        version = db.session.get(PracticeTarget, 1).version
    assert post(user, '/target/1/evidence', evidence_data(version=version, rating='confident',
        session_id='1', date='2030-01-01')).status_code == 302
    # Selected actual completion Jan 7 overrides entered/submission date.
    with app.app_context():
        assert db.session.get(ReviewState, 1).recommended_due_date == date(2030, 1, 8)
    assert 'Independent' in user.get('/target/1/evidence').text or 'independently' in user.get('/target/1/evidence').text
    assert 'Interval history' in user.get('/target/1/evidence').text
    post(user, '/settings', {'action': 'weekly', **{f'day_{i}': '0' for i in range(7)}})
    html = user.get('/targets').text
    assert 'Not scheduled' in html and '2030-01-08' in html
    assert 'Review' in user.get('/plan').text
    assert '30 min outstanding' in user.get('/progress').text
    assert toggle(user, app, 'off')[0].status_code == 302
    with app.app_context():
        assert db.session.get(ReviewTask, 1).state == 'cancelled'
        assert all(s.state != 'planned' for s in db.session.scalars(db.select(StudySession)))
    assert 'Follow-up reviews: Off' in user.get('/targets').text


def test_review_routes_owner_csrf_and_stale(two_users, app):
    a, b = two_users
    setup_plan(a, budget='30')
    assert b.get('/target/1/evidence').status_code == 404
    assert post(b, '/target/1/reviews', {'enabled': 'on', 'version': '1', 'request_id': 'foreign'}).status_code == 404
    assert a.post('/target/1/reviews', data={'enabled': 'on', 'version': '1', 'request_id': 'csrf'}).status_code == 400
    assert toggle(a, app, version='99')[0].status_code == 409
    assert toggle(a, app)[0].status_code == 302
    with app.app_context():
        assert db.session.get(ReviewState, 1).enabled


@pytest.mark.browser
def test_browser_review_opt_in_no_data_outcome_no_capacity_disable(live_url, app):
    from conftest import register
    client = app.test_client()
    register(client, 'review-ui@example.test')
    setup_plan(client, budget='30')
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        try:
            page = browser.new_page(viewport={'width': 375, 'height': 812})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(live_url + '/login')
            page.get_by_label('Email', exact=True).fill('review-ui@example.test')
            page.get_by_label('Password', exact=True).fill('synthetic-password')
            page.get_by_role('button', name='Log in', exact=True).click()
            page.goto(live_url + '/targets')
            page.get_by_role('button', name='Enable follow-up reviews').click()
            expect(page.get_by_text('Rated practice needed', exact=True)).to_be_visible()
            page.goto(live_url + '/session/1')
            page.get_by_role('button', name='Start practice', exact=True).click()
            page.get_by_role('link', name='Finish practice').click()
            page.get_by_role('button', name='Completed independently', exact=True).click()
            page.goto(live_url + '/targets')
            page.get_by_text('Review details', exact=True).click()
            expect(page.get_by_text('Completed independently; the next interval is 1 day.', exact=False)).to_be_visible()
            expect(page.get_by_text('2030-01-08', exact=True)).to_be_visible()
            page.goto(live_url + '/settings')
            for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']:
                page.get_by_label(f'{day} minutes', exact=True).fill('0')
            page.get_by_role('button', name='Save weekly availability').click()
            page.goto(live_url + '/targets')
            expect(page.get_by_text('Not scheduled', exact=False)).to_be_visible()
            page.goto(live_url + '/progress')
            expect(page.get_by_text('30 / 30 min initial practice completed', exact=True)).to_be_visible()
            expect(page.get_by_role('heading', name='Follow-up review work')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=f'docs/evidence/review-ui-{engine}.png', full_page=True)
            page.get_by_text('Review options', exact=True).click()
            page.get_by_role('button', name='Disable follow-up reviews').click()
            expect(page.get_by_role('heading', name='Follow-up reviews: Off')).to_be_visible()
            assert not errors
        finally:
            browser.close()
