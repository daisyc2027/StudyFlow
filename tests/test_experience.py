import io
from datetime import datetime, timedelta, timezone

import pytest

from conftest import post
from test_inputs import add_subject
from test_adaptation import setup_plan, session_action
from studyflow import db
from studyflow.models import FeedbackEntry, User, PracticeTarget, StudySession
from studyflow.services.progress import report

PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'


def test_progress_accounting_and_explicit_extra_practice(user, app):
    setup_plan(user)
    session_action(user, 1, 'miss', 1)
    session_action(user, 2, 'start', 1)
    app.config['CLOCK'] = lambda: datetime(2030, 1, 7, 12, tzinfo=timezone.utc) + timedelta(minutes=10)
    session_action(user, 2, 'complete', 2)
    with app.app_context():
        result = report(db.session.get(User, 1))
        assert result['budget'] == 60 and result['credited'] == 30
        assert result['outstanding'] == result['reserved'] == 30
        assert result['actual'] == 10 and result['missed'] == 1
        assert result['unallocated'] == 0
        assert len(result['evidence']) == 0
    html = user.get('/progress').text
    assert '30 / 60 practice minutes satisfied' in html
    assert '10.0' in html
    assert post(user, '/target/1/add-practice', {'version': '1'}).status_code == 302
    assert post(user, '/target/1/add-practice', {'version': '1'}).status_code == 409
    with app.app_context():
        assert db.session.get(PracticeTarget, 1).requested_minutes == 90
        assert sum(s.planned_minutes for s in db.session.scalars(db.select(StudySession))
                   if s.state == 'planned') == 60
    post(user, '/archive/target/1')
    with app.app_context():
        assert report(db.session.get(User, 1))['budget'] == 0
        assert report(db.session.get(User, 1))['actual'] == 10
    assert 'Archived' in user.get('/progress').text


def upload_note(user, content=PDF, name='reference.pdf', mime='application/pdf', **changes):
    data = {'subject_id': '1', 'title': 'Synthetic reference', 'teacher_text': 'Practise explaining',
            'pdf': (io.BytesIO(content), name, mime), **changes}
    return post(user, '/edit/feedback', data)


def test_pdf_owner_private_and_prefilled_context(two_users, app):
    a, b = two_users
    add_subject(b)
    assert upload_note(b).status_code == 302
    response = b.get('/feedback/1/attachment')
    assert response.status_code == 200 and response.data == PDF
    assert 'attachment;' in response.headers['Content-Disposition']
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert a.get('/feedback/1/attachment').status_code == 404
    assert a.get('/edit/target?subject_id=1&feedback_id=1').status_code == 404
    html = b.get('/edit/target?subject_id=1&feedback_id=1').text
    assert 'value="1" selected' in html
    with app.app_context():
        note = db.session.get(FeedbackEntry, 1)
        assert '/' not in note.attachment
        note.attachment = '../../secret'
        db.session.commit()
    assert b.get('/feedback/1/attachment').status_code == 404
    assert b.get('/feedback/999/attachment').status_code == 404


@pytest.mark.parametrize('content,name,mime', [
    (b'bad', 'reference.pdf', 'application/pdf'),
    (PDF, 'reference.txt', 'text/plain'),
    (PDF, '../reference.pdf', 'application/pdf'),
    (PDF, '/tmp/reference.pdf', 'application/pdf'),
    (PDF, 'dir\\reference.pdf', 'application/pdf'),
    (b'%PDF-1.4\n' + b'x' * (4 * 1024 * 1024) + b'%%EOF', 'big.pdf', 'application/pdf'),
])
def test_invalid_upload_no_record(user, app, content, name, mime):
    add_subject(user)
    assert upload_note(user, content, name, mime).status_code == 422
    with app.app_context():
        assert db.session.query(FeedbackEntry).count() == 0


def test_oversize_request(user, app):
    add_subject(user)
    assert upload_note(user, b'x' * (6 * 1024 * 1024)).status_code == 413
    with app.app_context():
        assert db.session.query(FeedbackEntry).count() == 0


def test_attachment_rollback_cleanup(user, app, monkeypatch):
    from pathlib import Path
    from conftest import token
    from studyflow.services import planning
    add_subject(user)
    csrf = token(user)
    def fail(*args, **kwargs):
        raise RuntimeError('Injected upload repair failure')
    monkeypatch.setattr(planning, 'repair', fail)
    with pytest.raises(RuntimeError, match='Injected'):
        user.post('/edit/feedback', data={'csrf_token': csrf, 'subject_id': '1', 'title': 'Synthetic',
                  'teacher_text': 'Reference', 'pdf': (io.BytesIO(PDF), 'reference.pdf', 'application/pdf')})
    with app.app_context():
        assert db.session.query(FeedbackEntry).count() == 0
    assert not list(Path(app.config['UPLOAD_FOLDER']).glob('*.pdf'))
