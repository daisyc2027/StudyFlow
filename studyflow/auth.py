from functools import wraps
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .models import User

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_user():
    g.user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def owned(model, identifier):
    item = db.session.get(model, identifier)
    if item is None or item.user_id != g.user.id:
        abort(404)
    return item


@bp.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        tz = request.form.get("timezone", "Asia/Hong_Kong")
        try:
            ZoneInfo(tz)
            if "@" not in email or len(email) > 254 or len(password) < 10:
                raise ValueError("Enter an email and a password of at least 10 characters.")
            user = User(email=email, password_hash=generate_password_hash(password), timezone=tz)
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("main.dashboard"))
        except ZoneInfoNotFoundError:
            error = "Choose a valid IANA timezone, such as Asia/Hong_Kong."
        except ValueError as exc:
            error = str(exc)
        except IntegrityError:
            db.session.rollback()
            error = "That email is already registered."
    return render_template("auth.html", mode="register", error=error), 422 if error else 200


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = db.session.scalar(db.select(User).where(
            User.email == request.form.get("email", "").strip().lower()))
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("main.dashboard"))
        error = "Email or password is incorrect."
    return render_template("auth.html", mode="login", error=error), 422 if error else 200


@bp.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
