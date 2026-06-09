"""HTTP routes."""

from functools import wraps

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
)

from pharmacy import auth, inventory, ledger, reports
from pharmacy.models import Drug, Lot, Role, User

bp = Blueprint("main", __name__)


def _form_error(exc):
    """Turn an operation exception into a user-facing flash message. A KeyError
    from a missing form field stringifies to just the bare key name, so name it
    explicitly; other errors already carry a readable message."""
    if isinstance(exc, KeyError):
        return f"Missing required field: {exc.args[0]}."
    return str(exc)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        g.user = g.db.get(User, session["user_id"])
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Like login_required, but additionally requires the admin role. A
    logged-in non-admin gets a 403 page rather than a redirect, so the refusal
    is explicit rather than looking like a missing login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        g.user = g.db.get(User, session["user_id"])
        if g.user is None or g.user.role is not Role.admin:
            return render_template("forbidden.html"), 403
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


DEFAULT_LOW_STOCK_THRESHOLD = 5


@bp.route("/alerts")
@login_required
def alerts():
    try:
        threshold = int(request.args.get("threshold",
                                         DEFAULT_LOW_STOCK_THRESHOLD))
    except ValueError:
        threshold = DEFAULT_LOW_STOCK_THRESHOLD
    rows = reports.alerts(g.db, low_stock_threshold=threshold)
    return render_template("alerts.html", rows=rows, threshold=threshold)


@bp.route("/drugs/new", methods=["GET", "POST"])
@admin_required
def new_drug():
    if request.method == "POST":
        drug = Drug(
            name=request.form["name"],
            strength=request.form.get("strength"),
            form=request.form.get("form"),
            code=request.form.get("code"),
            schedule=request.form.get("schedule"),
            unit=request.form.get("unit") or "unit",
        )
        g.db.add(drug)
        g.db.flush()
        flash(f"Added {drug.name}.", "ok")
        return redirect(url_for("main.dashboard"))
    return render_template("new_drug.html")


def _active_admin_count(db):
    return (db.query(User)
            .filter(User.role == Role.admin, User.active.is_(True))
            .count())


@bp.route("/users")
@admin_required
def users():
    rows = g.db.query(User).order_by(User.username).all()
    return render_template("users.html", users=rows)


@bp.route("/users/new", methods=["POST"])
@admin_required
def new_user():
    try:
        role = Role.admin if request.form.get("role") == "admin" else Role.operator
        auth.create_user(
            g.db,
            username=request.form["username"],
            display_name=request.form["display_name"],
            password=request.form["password"],
            role=role,
        )
        flash("User created.", "ok")
    except (auth.AuthError, KeyError) as exc:
        flash(_form_error(exc), "error")
    return redirect(url_for("main.users"))


@bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    user = g.db.get(User, user_id)
    if user is None:
        flash("No such user.", "error")
    elif (user.role is Role.admin and user.active
          and _active_admin_count(g.db) <= 1):
        flash("Cannot deactivate the last active admin.", "error")
    else:
        user.active = False
        g.db.flush()
        flash(f"Deactivated {user.username}.", "ok")
    return redirect(url_for("main.users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    user = g.db.get(User, user_id)
    if user is None:
        flash("No such user.", "error")
    else:
        try:
            auth.set_password(g.db, user, request.form["password"])
            flash(f"Password reset for {user.username}.", "ok")
        except KeyError as exc:
            flash(_form_error(exc), "error")
    return redirect(url_for("main.users"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        try:
            current = request.form["current_password"]
            new = request.form["new_password"]
        except KeyError as exc:
            flash(_form_error(exc), "error")
            return render_template("account_password.html")
        if auth.authenticate(g.db, g.user.username, current) is None:
            flash("Your current password is incorrect.", "error")
        elif not new:
            flash("New password must not be empty.", "error")
        else:
            auth.set_password(g.db, g.user, new)
            flash("Password changed.", "ok")
            return redirect(url_for("main.dashboard"))
    return render_template("account_password.html")


@bp.route("/receive", methods=["GET", "POST"])
@login_required
def receive():
    if request.method == "POST":
        try:
            inventory.receive(
                g.db, user_id=g.user.id,
                drug_id=int(request.form["drug_id"]),
                lot_number=request.form["lot_number"],
                quantity=float(request.form["quantity"]),
                reference=request.form.get("reference") or None,
            )
            flash("Stock received.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError, KeyError) as exc:
            flash(_form_error(exc), "error")
    drugs = g.db.query(Drug).order_by(Drug.name).all()
    return render_template("receive.html", drugs=drugs)


@bp.route("/dispense", methods=["GET", "POST"])
@login_required
def dispense():
    if request.method == "POST":
        try:
            inventory.dispense(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                quantity=float(request.form["quantity"]),
                reference=request.form.get("reference") or None,
            )
            flash("Dispensed.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError, KeyError) as exc:
            flash(_form_error(exc), "error")
    return render_template("dispense.html", rows=reports.inventory_snapshot(g.db))


@bp.route("/dispose", methods=["GET", "POST"])
@login_required
def dispose():
    if request.method == "POST":
        try:
            inventory.dispose(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                quantity=float(request.form["quantity"]),
                witness_user_id=int(request.form["witness_user_id"]),
                reason=request.form.get("reason", ""),
            )
            flash("Disposal recorded.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError, KeyError) as exc:
            flash(_form_error(exc), "error")
    witnesses = g.db.query(User).filter(User.id != g.user.id,
                                        User.active.is_(True)).all()
    return render_template("dispose.html",
                           rows=reports.inventory_snapshot(g.db),
                           witnesses=witnesses)


@bp.route("/reconcile", methods=["GET", "POST"])
@login_required
def reconcile():
    if request.method == "POST":
        try:
            inventory.reconcile(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                counted_qty=float(request.form["counted_qty"]),
                post_adjustment="post_adjustment" in request.form,
                reason=request.form.get("reason", ""),
            )
            flash("Count recorded.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError, KeyError) as exc:
            flash(_form_error(exc), "error")
    return render_template("reconcile.html",
                           rows=reports.inventory_snapshot(g.db))


@bp.route("/print/inventory")
@login_required
def print_inventory():
    return render_template("print_inventory.html",
                           rows=reports.inventory_snapshot(g.db))


@bp.route("/print/audit")
@login_required
def print_audit():
    return render_template("print_audit.html",
                           rows=reports.audit_log(g.db))


@bp.route("/lots/<int:lot_id>")
@login_required
def lot_history(lot_id):
    if g.db.get(Lot, lot_id) is None:
        flash("No such lot.", "error")
        return redirect(url_for("main.dashboard"))
    return render_template("lot_history.html",
                           hist=reports.lot_history(g.db, lot_id))


@bp.route("/verify")
@login_required
def verify():
    ok, bad_id = ledger.verify_chain(g.db)
    return render_template("verify.html", ok=ok, bad_id=bad_id)
