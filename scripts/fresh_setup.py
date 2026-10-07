"""Release smoke: production CLI, fresh SQLite, real browser, opt-in seed, teardown."""
from datetime import datetime, timedelta
from pathlib import Path
import os
import socket
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    evidence = ROOT / 'docs' / 'evidence'
    lines = []
    env = {**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(ROOT / '.browsers')}
    with TemporaryDirectory(prefix='studyflow-release-') as directory:
        path = Path(directory) / 'fresh.sqlite'
        env['STUDYFLOW_DATABASE'] = f'sqlite:///{path}'
        def command(*args):
            result = subprocess.run([sys.executable, '-m', 'flask', '--app', 'studyflow', *args],
                                    env=env, capture_output=True, text=True, timeout=30)
            lines.append(f'flask {" ".join(args)}: exit {result.returncode}\n{result.stdout}{result.stderr}')
            if result.returncode:
                raise RuntimeError(lines[-1])
        command('db', 'upgrade')
        with sqlite3.connect(path) as connection:
            assert connection.execute('SELECT COUNT(*) FROM user').fetchone()[0] == 0
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with (evidence / 'fresh-server.log').open('w') as log:
            server = subprocess.Popen([sys.executable, '-m', 'flask', '--app', 'studyflow', 'run',
                '--host', '127.0.0.1', '--port', str(port)], env=env, stdout=log, stderr=log)
            base = f'http://127.0.0.1:{port}'
            try:
                for _ in range(100):
                    try:
                        with urlopen(base + '/health', timeout=1) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Fresh server exited; see fresh-server.log') from None
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Fresh server failed to become ready.')
                day = datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
                with sync_playwright() as pw:
                    browser = pw.chromium.launch()
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    page.set_default_timeout(8000)
                    requests, errors = [], []
                    page.on('request', lambda req: requests.append(req.url))
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(base + '/register')
                    page.get_by_label('Email', exact=True).fill('release@example.test')
                    page.get_by_label('Password', exact=True).fill('synthetic-password')
                    page.get_by_role('button', name='Create account').click()
                    page.get_by_role('navigation').get_by_role('link', name='Feedback & Targets').click()
                    page.get_by_role('link', name='Add subject', exact=True).click()
                    page.get_by_label('Subject name').fill('Release synthetic subject')
                    page.get_by_role('button', name='Save subject').click()
                    page.get_by_role('link', name='Add feedback', exact=True).click()
                    page.get_by_label('Subject', exact=True).select_option('1')
                    page.get_by_label('Title', exact=True).fill('Release synthetic note')
                    page.get_by_label('Teacher feedback').fill('Explain each step and practise evaluation.')
                    page.get_by_role('button', name='Save feedback').click()
                    page.get_by_role('link', name='Add exam', exact=True).click()
                    page.get_by_label('Subject', exact=True).select_option('1')
                    page.get_by_label('Title', exact=True).fill('Release synthetic exam')
                    page.get_by_label('Exam date').fill((day + timedelta(days=7)).isoformat())
                    page.get_by_role('button', name='Save exam').click()
                    page.get_by_role('link', name='Create target from this feedback').click()
                    page.get_by_label('Topic', exact=True).fill('Explain a policy')
                    page.get_by_label('Practice goal').fill('Compare two consequences in a worked example.')
                    page.get_by_label('Exam (optional)', exact=True).select_option('1')
                    page.get_by_role('button', name='Save target').click()
                    page.get_by_role('link', name='Settings', exact=True).click()
                    for label in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        page.get_by_label(label + ' minutes').fill('60')
                    page.get_by_role('button', name='Save weekly availability').click()
                    page.get_by_role('link', name='Study Plan', exact=True).click()
                    page.get_by_role('button', name='Generate / Refresh plan').click()
                    expect(page.locator('.session')).to_have_count(2)
                    page.locator('.session').first.get_by_role('link', name='Open session').click()
                    page.get_by_role('button', name='Start session').click()
                    page.get_by_role('button', name='Pause session').click()
                    page.get_by_role('button', name='Finish session').click()
                    page.get_by_role('link', name='Progress', exact=True).click()
                    expect(page.get_by_text('30 / 60 practice minutes satisfied', exact=True)).to_be_visible()
                    page.get_by_role('link', name='Study Plan', exact=True).click()
                    page.locator('.session').filter(has=page.get_by_role('link', name='Open session')).first.get_by_role('link', name='Open session').click()
                    page.get_by_role('button', name='Mark missed').click()
                    page.get_by_role('link', name='Settings', exact=True).click()
                    page.get_by_label('Date', exact=True).fill(day.isoformat())
                    page.get_by_label('Available minutes', exact=True).fill('0')
                    page.get_by_role('button', name='Save date override').click()
                    page.get_by_role('link', name='Study Plan', exact=True).click()
                    expect(page.get_by_text('Conflict:', exact=False)).to_be_visible()
                    page.screenshot(path=str(evidence / 'fresh-production-workflow.png'), full_page=True)
                    page.get_by_role('button', name='Log out').click()
                    page.get_by_label('Email', exact=True).fill('release@example.test')
                    page.get_by_label('Password', exact=True).fill('synthetic-password')
                    page.get_by_role('button', name='Log in', exact=True).click()
                    page.get_by_role('navigation').get_by_role('link', name='Feedback & Targets').click()
                    expect(page.get_by_role('heading', name='Explain a policy')).to_be_visible()
                    # Preserve the original no-outcome checks before explicitly entering
                    # a late outcome. Then verify review tables/services on a normal CLI launch.
                    with sqlite3.connect(path) as connection:
                        assert connection.execute('SELECT COUNT(*) FROM evidence_entry').fetchone()[0] == 0
                        assert connection.execute('SELECT requested_minutes FROM practice_target').fetchone()[0] == 60
                        assert connection.execute("SELECT COUNT(*) FROM study_session WHERE state IN ('planned','in_progress','paused')").fetchone()[0] == 1
                        assert connection.execute("SELECT COUNT(*) FROM study_session WHERE state='completed'").fetchone()[0] == 1
                        assert connection.execute('SELECT COUNT(*) FROM review_task').fetchone()[0] == 0
                    page.get_by_role('button', name='Enable follow-up reviews').click()
                    expect(page.get_by_text('Rated practice needed', exact=True)).to_be_visible()
                    page.get_by_role('link', name='Record practice outcome').click()
                    page.get_by_label('Completed session (optional)', exact=True).select_option('1')
                    page.get_by_label('Practice outcome', exact=True).select_option('confident')
                    page.get_by_role('button', name='Save outcome').click()
                    expect(page.get_by_text((day + timedelta(days=1)).isoformat(), exact=True).first).to_be_visible()
                    page.goto(base + '/plan')
                    expect(page.get_by_text(f'Recommended {day + timedelta(days=1)} · Scheduled {day + timedelta(days=1)}', exact=True)).to_be_visible()
                    page.screenshot(path=str(evidence / 'fresh-production-review.png'), full_page=True)
                    lines.append('Fresh normal-server review opt-in, unrated no-data state, late explicit outcome and shared greedy reservation: PASS.')
                    assert all(url.startswith(base) for url in requests) and not errors
                    lines.append(f'Fresh normal Flask server + manual browser workflow: PASS; local date {day}; Chromium {browser.version}; runtime requests localhost only.')
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
                lines.append('Fresh test server stopped explicitly.')
        with sqlite3.connect(path) as connection:
            assert connection.execute('SELECT COUNT(*) FROM evidence_entry').fetchone()[0] == 1
            assert connection.execute('SELECT requested_minutes FROM practice_target').fetchone()[0] == 60
            assert connection.execute("SELECT COUNT(*) FROM study_session s WHERE state IN ('planned','in_progress','paused') AND NOT EXISTS (SELECT 1 FROM session_review r WHERE r.session_id=s.id)").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM study_session WHERE state='completed'").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM review_task WHERE state='pending'").fetchone()[0] == 1
            assert connection.execute('SELECT COUNT(*) FROM session_review').fetchone()[0] == 1
            assert connection.execute('SELECT interval FROM review_state').fetchone()[0] == 1
        command('seed-demo', '--date', day.isoformat(), '--email', 'release-demo@example.test',
                '--password', 'synthetic-password')
        command('reconcile', '--email', 'release@example.test')
        command('db', 'check')
        with sqlite3.connect(path) as connection:
            assert connection.execute('SELECT COUNT(*) FROM user').fetchone()[0] == 2
            assert connection.execute('SELECT COUNT(*) FROM practice_target').fetchone()[0] == 4
            assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        lines.append('Opt-in seed, restart-independent database inspection, finite workload and foreign-key check: PASS.')
    (evidence / 'fresh-setup.log').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
