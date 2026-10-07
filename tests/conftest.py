import re
import threading
from datetime import datetime, timezone

import pytest
from werkzeug.serving import make_server

from studyflow import create_app, db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True, "SECRET_KEY": "test-only-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}",
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "CLOCK": lambda: datetime(2030, 1, 7, 12, tzinfo=timezone.utc),
    })
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def token(client, path="/register"):
    html = client.get(path).text
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def post(client, path, data=None, token_path="/"):
    extra = {}
    if path == '/settings':
        token_path = '/settings'
        html = client.get('/settings').text
        extra['settings_version'] = re.search(r'name="settings_version" value="([^"]+)"', html).group(1)
    return client.post(path, data={"csrf_token": token(client, token_path), **extra, **(data or {})})


def register(client, email="synthetic@example.test"):
    return post(client, "/register", {"email": email, "password": "synthetic-password",
                                    "timezone": "Asia/Hong_Kong"}, "/register")


@pytest.fixture
def user(client):
    register(client)
    return client


@pytest.fixture
def two_users(app):
    a, b = app.test_client(), app.test_client()
    register(a, "a@example.test")
    register(b, "b@example.test")
    return a, b


@pytest.fixture
def live_url(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()
