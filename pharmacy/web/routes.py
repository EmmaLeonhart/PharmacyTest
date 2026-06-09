"""HTTP routes."""

from functools import wraps

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
)

from pharmacy import auth, reports
from pharmacy.models import User

bp = Blueprint("main", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        g.user = g.db.get(User, session["user_id"])
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = auth.authenticate(g.db, request.form["username"],
                                 request.form["password"])
        if user is None:
            flash("Invalid username or password.", "error")
        else:
            session["user_id"] = user.id
            return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/")
@login_required
def dashboard():
    rows = reports.inventory_snapshot(g.db)
    return render_template("dashboard.html", rows=rows)


@bp.route("/audit")
@login_required
def audit():
    rows = reports.audit_log(g.db)
    return render_template("audit.html", rows=rows)
