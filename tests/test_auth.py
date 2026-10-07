from studyflow import db
from studyflow.models import User
from conftest import post, register


def test_accounts_health_csrf(client, app):
    assert client.get("/health").json == {"status": "ok"}
    assert client.get("/").status_code == 302
    assert client.post("/register", data={"email": "a@b.test"}).status_code == 400
    assert register(client).status_code == 302
    assert "Your study space" in client.get("/").text
    assert post(client, "/logout").status_code == 302
    assert post(client, "/login", {"email": "synthetic@example.test", "password": "wrong"},
                "/login").status_code == 422
    assert post(client, "/login", {"email": "synthetic@example.test",
                "password": "synthetic-password"}, "/login").status_code == 302
    with app.app_context():
        stored = db.session.scalar(db.select(User))
        assert stored.password_hash != "synthetic-password"


def test_two_users_exist(two_users, app):
    with app.app_context():
        assert db.session.query(User).count() == 2
