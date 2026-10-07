import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()


@event.listens_for(Engine, "connect")
def sqlite_foreign_keys(connection, _):
    if type(connection).__module__.startswith("sqlite3"):
        connection.execute("PRAGMA foreign_keys=ON")


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = Path(app.instance_path) / "secret"
    if not secret_file.exists():
        try:
            with secret_file.open("x") as handle:
                handle.write(secrets.token_hex(32))
            secret_file.chmod(0o600)
        except FileExistsError:
            pass
    app.config.from_mapping(
        SECRET_KEY=secret_file.read_text(),
        SQLALCHEMY_DATABASE_URI=os.getenv("STUDYFLOW_DATABASE", "sqlite:///studyflow.sqlite"),
        UPLOAD_FOLDER=str(Path(app.instance_path) / "uploads"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        CLOCK=lambda: datetime.now(timezone.utc),
    )
    if config:
        app.config.update(config)
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    from flask import g, request
    from sqlalchemy import text

    @app.before_request
    def serialize_mutations():
        # SQLite serializes writes; acquire the lock before reading stale form state.
        if request.method == 'POST':
            db.session.execute(text('BEGIN IMMEDIATE'))

    from . import models  # noqa: F401
    from .auth import bp as auth_bp
    from .views import bp as views_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    from .inputs import bp as inputs_bp
    app.register_blueprint(inputs_bp)
    from .evidence_views import bp as evidence_bp
    app.register_blueprint(evidence_bp)
    from .plan_views import bp as plan_bp
    app.register_blueprint(plan_bp)
    from .session_views import bp as sessions_bp
    app.register_blueprint(sessions_bp)
    from .attachments import bp as attachments_bp
    app.register_blueprint(attachments_bp)
    from .review_views import bp as reviews_bp
    app.register_blueprint(reviews_bp)
    from .cli import register_cli
    register_cli(app)

    @app.before_request
    def reconcile_on_visit():
        from .services.planning import reconcile, repair
        if g.user and request.method == 'GET' and g.user.plan_started:
            db.session.execute(text('BEGIN IMMEDIATE'))
            reconcile(g.user)
            repair(g.user, 'visit reconciliation')
            db.session.commit()

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(409)
    def error_page(error):
        return render_template("error.html", error=error), error.code

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error=error), 500

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
