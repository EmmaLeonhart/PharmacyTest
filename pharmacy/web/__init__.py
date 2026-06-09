"""Flask app factory."""

from flask import Flask

from pharmacy.db import make_session


def create_app(engine, secret_key="dev-insecure-change-me"):
    app = Flask(__name__)
    app.secret_key = secret_key
    app.config["ENGINE"] = engine

    @app.before_request
    def _open_session():
        from flask import g
        g.db = make_session(engine)

    @app.teardown_request
    def _close_session(exc):
        from flask import g
        db = g.pop("db", None)
        if db is not None:
            if exc is None:
                db.commit()
            else:
                db.rollback()
            db.close()

    from pharmacy.web.routes import bp
    app.register_blueprint(bp)
    return app


def build_app_from_env():
    """Construct a fully configured app from environment variables. Shared by
    the `python -m pharmacy` server path and the WSGI entrypoint so the two
    cannot drift. Reads PHARMACY_DB, PHARMACY_ADMIN_USER/PASSWORD, and
    PHARMACY_SECRET_KEY / PHARMACY_SECRET_KEY_FILE; ensures a first-run admin
    exists and resolves a stable secret key."""
    import os

    from pharmacy.bootstrap import ensure_admin, load_or_create_secret_key
    from pharmacy.db import init_db

    db_url = os.environ.get("PHARMACY_DB", "sqlite:///pharmacy.db")
    engine = init_db(db_url)

    admin_user = os.environ.get("PHARMACY_ADMIN_USER", "admin")
    admin_pw = os.environ.get("PHARMACY_ADMIN_PASSWORD", "admin")
    session = make_session(engine)
    if ensure_admin(session, username=admin_user, password=admin_pw):
        print(f"[first run] Created admin '{admin_user}'. Log in and change "
              f"the password.")
    session.close()

    secret = os.environ.get("PHARMACY_SECRET_KEY")
    if not secret:
        secret = load_or_create_secret_key(
            os.environ.get("PHARMACY_SECRET_KEY_FILE", "pharmacy_secret.key"))
    return create_app(engine, secret_key=secret)
