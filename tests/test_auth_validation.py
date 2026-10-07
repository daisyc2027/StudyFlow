from conftest import post, register
from studyflow import db
from studyflow.models import User


def test_invalid_account_and_duplicate(client, app):
    result = post(client, '/register', {'email': 'broken', 'password': 'short',
                  'timezone': 'Asia/Hong_Kong'}, '/register')
    assert result.status_code == 422
    assert 'broken' in result.text
    assert post(client, '/register', {'email': 'valid@example.test',
                'password': 'synthetic-password', 'timezone': 'Fake/Zone'},
                '/register').status_code == 422
    assert register(client).status_code == 302
    assert register(client).status_code == 422
    with app.app_context():
        assert db.session.query(User).count() == 1


def test_csrf_does_not_log_out(user):
    assert user.post('/logout', data={'csrf_token': 'forged'}).status_code == 400
    assert user.get('/').status_code == 200
