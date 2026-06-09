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
