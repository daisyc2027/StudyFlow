import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.mark.browser
def test_browser_auth(live_url):
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv("STUDYFLOW_BROWSER", "chromium")).launch()
        page = browser.new_page()
        page.goto(live_url + "/register")
        page.get_by_label("Email", exact=True).fill("browser@example.test")
        page.get_by_label("Password", exact=True).fill("synthetic-password")
        page.get_by_role("button", name="Create account").click()
        expect(page.get_by_role("heading", name="Today")).to_be_visible()
        page.get_by_role("button", name="Log out").click()
        page.get_by_label("Email", exact=True).fill("browser@example.test")
        page.get_by_label("Password", exact=True).fill("synthetic-password")
        page.get_by_role("button", name="Log in", exact=True).click()
        expect(page.get_by_role("heading", name="Today")).to_be_visible()
        Path("docs/evidence").mkdir(exist_ok=True)
        page.screenshot(path="docs/evidence/foundation.png", full_page=True)
        browser.close()


@pytest.mark.browser
def test_browser_inputs(live_url):
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('STUDYFLOW_BROWSER', 'chromium')).launch()
        page = browser.new_page()
        page.goto(live_url + '/register')
        page.get_by_label('Email', exact=True).fill('inputs@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Create account').click()
        page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
        page.get_by_role('link', name='Add subject', exact=True).click()
        page.get_by_label('Subject name').fill('Synthetic economics')
        page.get_by_role('button', name='Save subject').click()
        page.get_by_role('link', name='Add feedback', exact=True).click()
        page.get_by_label('Subject', exact=True).select_option('1')
        page.get_by_label('Title', exact=True).fill('Synthetic essay feedback')
        page.get_by_label('Teacher feedback').fill('Develop evaluation of policy choices.')
        page.get_by_role('button', name='Save feedback').click()
        page.get_by_role('link', name='Add study goal', exact=True).click()
        page.get_by_label('Subject', exact=True).select_option('1')
        page.get_by_label('Topic', exact=True).fill('Price floors')
        page.get_by_label('Study goal').fill('Compare two consequences for consumers.')
        page.get_by_role('button', name='Save study goal').click()
        expect(page.get_by_role('heading', name='Price floors')).to_be_visible()
        page.get_by_role('link', name='Settings', exact=True).click()
        page.get_by_label('Monday minutes').fill('60')
        page.get_by_role('button', name='Save weekly availability').click()
        page.get_by_label('Date', exact=True).fill('2030-01-08')
        page.get_by_label('Available minutes', exact=True).fill('0')
        page.get_by_role('button', name='Save date override').click()
        page.reload()
        expect(page.get_by_label('Monday minutes')).to_have_value('60')
        expect(page.get_by_text('2030-01-08 · 0 min', exact=True)).to_be_visible()
        browser.close()


@pytest.mark.browser
def test_browser_saved_plan(live_url, app):
    # Inputs are persisted via actual HTTP routes; the browser runs the real scheduler.
    from conftest import register
    from test_inputs import add_subject, add_target, weekly
    client = app.test_client()
    register(client, 'plan@example.test')
    add_subject(client)
    add_target(client, start_rating='needs')
    weekly(client, 60)
    with sync_playwright() as pw:
        browser = getattr(pw, os.getenv('STUDYFLOW_BROWSER', 'chromium')).launch()
        page = browser.new_page()
        page.goto(live_url + '/login')
        page.get_by_label('Email', exact=True).fill('plan@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.get_by_role('button', name='Plan my week').click()
        expect(page.locator('.session')).to_have_count(2)
        ids = page.locator('.session').evaluate_all('(els) => els.map(e => e.dataset.sessionId)')
        page.get_by_role('button', name='Plan my week').click()
        assert page.locator('.session').evaluate_all('(els) => els.map(e => e.dataset.sessionId)') == ids
        page.screenshot(path='docs/evidence/initial-plan.png', full_page=True)
        browser.close()


def browser_open_subject(page, subject):
    page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
    page.locator(f'[data-subject-id="{subject}"]').get_by_role('link', name='Open subject').click()


def browser_subject(page, name, level):
    page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
    page.get_by_role('link', name='Add subject', exact=True).click()
    page.get_by_label('Subject name').fill(name)
    page.get_by_label('Level (optional)', exact=True).select_option(level)
    page.get_by_role('button', name='Save subject').click()


def browser_exam(page, subject, title, day):
    browser_open_subject(page, subject)
    page.get_by_role('link', name='Add exam', exact=True).click()
    page.get_by_label('Subject', exact=True).select_option(subject)
    page.get_by_label('Title', exact=True).fill(title)
    page.get_by_label('Exam date').fill(day)
    page.get_by_role('button', name='Save exam').click()


def browser_target(page, subject, topic, rating, exam, feedback=None):
    browser_open_subject(page, subject)
    page.get_by_role('link', name='Add study goal', exact=True).click()
    page.get_by_label('Subject', exact=True).select_option(subject)
    page.get_by_label('Topic', exact=True).fill(topic)
    page.get_by_label('Skill (optional)', exact=True).fill('Explain reasoning')
    page.get_by_label('Study goal').fill('Practise a worked example and explain each step.')
    page.get_by_label('Starting practice need', exact=True).select_option(rating)
    page.get_by_label('Exam (optional)', exact=True).select_option(exam)
    if feedback:
        page.get_by_text('More options', exact=True).click()
        page.get_by_label('Feedback note (optional)', exact=True).select_option(feedback)
    page.get_by_role('button', name='Save study goal').click()


@pytest.mark.browser
def test_full_feedback_plan_practice_repair(live_url):
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.set_default_timeout(8000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        runtime_requests = []
        page.on('request', lambda req: runtime_requests.append(req.url))
        page.goto(live_url + '/register')
        page.get_by_label('Email', exact=True).fill('workflow@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Create account').click()
        page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
        browser_subject(page, 'Mathematics', 'HL')
        browser_subject(page, 'Economics', 'SL')
        page.get_by_role('link', name='Add feedback', exact=True).click()
        page.get_by_label('Subject', exact=True).select_option('2')
        page.get_by_label('Title', exact=True).fill('Synthetic teacher feedback')
        page.get_by_label('Teacher feedback').fill('Develop evaluation of a price floor policy.')
        page.get_by_label('Overall grade (optional)').fill('75% overall')
        page.get_by_role('button', name='Save feedback').click()
        browser_exam(page, '1', 'Synthetic maths exam', '2030-01-12')
        browser_exam(page, '2', 'Synthetic economics exam', '2030-01-11')
        browser_target(page, '1', 'Integration', 'developing', '1')
        browser_target(page, '1', 'Probability', 'needs', '1')
        browser_target(page, '2', 'Price floors', 'needs', '2', '1')
        page.get_by_role('link', name='Settings', exact=True).click()
        for label, minutes in [('Monday minutes', '120'), ('Tuesday minutes', '60'), ('Wednesday minutes', '60')]:
            page.get_by_label(label, exact=True).fill(minutes)
        page.get_by_role('button', name='Save weekly availability').click()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.get_by_role('button', name='Plan my week').click()
        expect(page.locator('.session')).to_have_count(6)
        page.locator('.session').first.get_by_role('link', name='Open session').click()
        page.get_by_role('button', name='Start practice').click()
        page.get_by_role('button', name='Pause practice').click()
        page.reload()
        expect(page.get_by_text('paused', exact=True)).to_be_visible()
        page.get_by_role('button', name='Resume practice').click()
        page.get_by_role('link', name='Finish practice').click()
        page.get_by_role('button', name='Completed independently', exact=True).click()
        expect(page.get_by_text('completed', exact=True)).to_be_visible()
        page.get_by_role('link', name='Progress', exact=True).click()
        expect(page.get_by_text('30 / 60 min initial practice completed', exact=True)).to_be_visible()
        expect(page.locator('.evidence-row').get_by_text('Confident', exact=True)).to_be_visible()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.locator('.session').first.get_by_role('link', name='View attempt').click()
        page.get_by_role('link', name='View target evidence').click()
        expect(page.locator('.evidence-row').get_by_text('Confident', exact=True)).to_be_visible()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.locator('.session').filter(has=page.get_by_role('link', name='Open session')).first.get_by_role('link', name='Open session').click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_role('button', name='Mark missed').click()
        expect(page.get_by_text('missed', exact=True)).to_be_visible()
        page.get_by_role('link', name='Plan', exact=True).click()
        expect(page.get_by_text('Recent plan changes', exact=True)).to_be_visible()
        page.get_by_role('link', name='Settings', exact=True).click()
        page.get_by_label('Date', exact=True).fill('2030-01-07')
        page.get_by_label('Available minutes', exact=True).fill('30')
        page.get_by_role('button', name='Save date override').click()
        page.get_by_role('link', name='Plan', exact=True).click()
        expect(page.get_by_text('30 / 30 min booked · 0 min free', exact=True)).to_be_visible()
        assert page.locator('.session').count() >= 2
        page.screenshot(path=f'docs/evidence/workflow-{engine}.png', full_page=True)
        assert not errors
        page.get_by_role('button', name='Log out').click()
        page.get_by_label('Email', exact=True).fill('workflow@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
        browser_open_subject(page, '2')
        expect(page.get_by_role('heading', name='Price floors · Explain reasoning')).to_be_visible()
        assert all(url.startswith(live_url) for url in runtime_requests)
        browser.close()


@pytest.mark.browser
def test_main_screens_mobile_empty_and_links(live_url, app):
    from conftest import register
    from test_adaptation import setup_plan
    client = app.test_client()
    register(client, 'screens@example.test')
    setup_plan(client)
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.goto(live_url + '/login')
        page.get_by_label('Email', exact=True).fill('screens@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        for path, name in [('/', 'dashboard'), ('/subjects', 'subjects'), ('/subject/1', 'subject'), ('/targets', 'targets'), ('/plan', 'plan'),
                           ('/progress', 'progress'), ('/settings', 'settings'), ('/session/1', 'session')]:
            page.goto(live_url + path)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=f'docs/evidence/{name}-{engine}-desktop.png', full_page=True)
            links = page.locator('a[href]').evaluate_all('(els) => els.map(e => e.getAttribute("href"))')
            for link in set(links):
                if link.startswith('/'):
                    assert page.request.get(live_url + link).status < 400, link
            page.set_viewport_size({'width': 375, 'height': 812})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), path
            page.screenshot(path=f'docs/evidence/{name}-{engine}-mobile.png', full_page=True)
            page.set_viewport_size({'width': 320, 'height': 812})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), path
            page.set_viewport_size({'width': 1440, 'height': 1000})
        assert not errors
        page.get_by_role('button', name='Log out').click()
        page.goto(live_url + '/register')
        page.get_by_label('Email', exact=True).fill('empty@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Create account').click()
        expect(page.get_by_role('heading', name='Build your first week')).to_be_visible()
        page.get_by_role('link', name='Progress', exact=True).click()
        expect(page.get_by_role('heading', name='Your first practice goal starts here')).to_be_visible()
        browser.close()


@pytest.mark.browser
def test_browser_edit_evidence_attachment_lock_move_archive(live_url, app):
    from conftest import register
    from test_adaptation import setup_plan
    from test_experience import PDF
    client = app.test_client()
    register(client, 'actions@example.test')
    setup_plan(client)
    with sync_playwright() as pw:
        engine = os.getenv('STUDYFLOW_BROWSER', 'chromium')
        browser = getattr(pw, engine).launch()
        page = browser.new_page(accept_downloads=True)
        page.set_default_timeout(8000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        page.goto(live_url + '/login')
        page.get_by_label('Email', exact=True).fill('actions@example.test')
        page.get_by_label('Password', exact=True).fill('synthetic-password')
        page.get_by_role('button', name='Log in', exact=True).click()
        page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
        browser_open_subject(page, '1')
        page.get_by_role('link', name='Edit subject', exact=True).click()
        page.get_by_label('Subject name').fill('Synthetic revised maths')
        page.get_by_role('button', name='Save subject').click()
        page.get_by_role('link', name='Add feedback', exact=True).click()
        page.get_by_label('Subject', exact=True).select_option('1')
        page.get_by_label('Title', exact=True).fill('Synthetic reference note')
        page.get_by_label('Teacher feedback').fill('Explain your working.')
        page.get_by_text('Reference PDF (optional)', exact=True).click()
        page.get_by_label('PDF attachment').set_input_files({'name': 'reference.pdf', 'mimeType': 'application/pdf', 'buffer': PDF})
        page.get_by_role('button', name='Save feedback').click()
        with page.expect_download() as info:
            page.get_by_role('link', name='Download reference PDF').click()
        assert Path(info.value.path()).read_bytes() == PDF
        browser_exam(page, '1', 'Synthetic revised exam', '2030-01-10')
        page.get_by_text('Exam options', exact=True).click()
        page.get_by_role('link', name='Edit exam').click()
        page.get_by_label('Exam date').fill('2030-01-11')
        page.get_by_role('button', name='Save exam').click()
        page.get_by_role('link', name='Edit goal', exact=True).click()
        page.get_by_label('Study goal').fill('Explain a revised worked example.')
        page.get_by_label('Exam (optional)', exact=True).select_option('1')
        page.get_by_text('More options', exact=True).click()
        page.get_by_label('Feedback note (optional)', exact=True).select_option('1')
        page.get_by_role('button', name='Save study goal').click()
        page.get_by_role('link', name='Record practice outcome').click()
        page.get_by_label('Practice outcome', exact=True).select_option('needs')
        page.get_by_label('Source', exact=True).select_option('teacher_interpretation')
        page.get_by_label('Task or context').fill('Synthetic interpretation of teacher comments')
        page.get_by_role('button', name='Save outcome').click()
        page.get_by_label('Practice outcome', exact=True).select_option('confident')
        page.get_by_label('Source', exact=True).select_option('teacher_rating')
        page.get_by_text('Target-specific marks & corrections', exact=True).click()
        page.get_by_label('Marks earned', exact=True).fill('8')
        page.get_by_label('Marks possible', exact=True).fill('10')
        page.get_by_label('Task or context').fill('Synthetic teacher-rated task')
        page.get_by_label('Correct an earlier observation', exact=True).select_option('1')
        page.get_by_role('button', name='Save outcome').click()
        expect(page.get_by_text('Corrected', exact=True)).to_be_visible()
        expect(page.locator('.evidence-row').get_by_text('Confident', exact=True)).to_be_visible()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.locator('.session').first.get_by_role('link', name='Open session').click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_role('button', name='Lock session', exact=True).click()
        page.get_by_role('link', name='Settings', exact=True).click()
        page.get_by_label('Date', exact=True).fill('2030-01-07')
        page.get_by_label('Available minutes', exact=True).fill('0')
        page.get_by_role('button', name='Save date override').click()
        page.get_by_role('link', name='Plan', exact=True).click()
        expect(page.get_by_text('Conflict:', exact=False)).to_be_visible()
        page.get_by_role('link', name='Settings', exact=True).click()
        page.get_by_role('button', name='Remove override for 2030-01-07').click()
        page.get_by_label('Timezone').fill('America/Los_Angeles')
        page.get_by_role('button', name='Save timezone').click()
        page.get_by_role('link', name='Plan', exact=True).click()
        page.locator('.session').first.get_by_role('link', name='Open session').click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_role('button', name='Unlock session', exact=True).click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_text('Move to another date', exact=True).click()
        page.get_by_label('New study date').fill('2030-01-08')
        page.get_by_role('button', name='Move session', exact=True).click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_text('Move to another date', exact=True).click()
        page.get_by_label('New study date').fill('2030-01-07')
        page.get_by_role('button', name='Move session', exact=True).click()
        page.get_by_text('Session options', exact=True).click()
        page.get_by_role('button', name='Skip session', exact=True).click()
        expect(page.get_by_text('skipped', exact=True)).to_be_visible()
        page.get_by_role('link', name='Progress', exact=True).click()
        page.get_by_role('button', name='Add 30 minutes of practice').click()
        expect(page.get_by_text('0 / 90 min initial practice completed', exact=True)).to_be_visible()
        page.get_by_role('navigation').get_by_role('link', name='Subjects', exact=True).click()
        browser_open_subject(page, '1')
        page.get_by_text('Goal options & planning details', exact=True).click()
        page.get_by_role('button', name='Archive goal', exact=True).click()
        page.get_by_text('Feedback options', exact=True).click()
        page.get_by_role('button', name='Archive feedback', exact=True).click()
        page.get_by_text('Subject options', exact=True).click()
        page.get_by_role('button', name='Archive subject', exact=True).click()
        page.get_by_text('Archived records', exact=True).click()
        expect(page.get_by_text('Target · Integration', exact=False)).to_be_visible()
        expect(page.get_by_role('link', name='Evidence history', exact=True)).to_be_visible()
        # A real mutating browser request without CSRF must be rejected.
        assert not errors
        assert page.request.post(live_url + '/edit/subject', form={'name': 'CSRF forged'}).status == 400
        browser.close()
