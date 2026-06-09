"""Run the tracker: `python -m pharmacy`.

On first run, if no admin exists, one is created from PHARMACY_ADMIN_USER /
PHARMACY_ADMIN_PASSWORD (defaults admin/admin) and the credentials are printed
so staff can log in and change them.
"""

import os

from pharmacy.bootstrap import ensure_admin, load_or_create_secret_key
from pharmacy.db import init_db, make_session
from pharmacy.web import create_app


def main():
    db_url = os.environ.get("PHARMACY_DB", "sqlite:///pharmacy.db")
    engine = init_db(db_url)

    admin_user = os.environ.get("PHARMACY_ADMIN_USER", "admin")
    admin_pw = os.environ.get("PHARMACY_ADMIN_PASSWORD", "admin")
    session = make_session(engine)
    if ensure_admin(session, username=admin_user, password=admin_pw):
        print(f"[first run] Created admin '{admin_user}' with the configured "
              f"password. Log in and change it.")
    session.close()

    secret = os.environ.get("PHARMACY_SECRET_KEY")
    if not secret:
        key_file = os.environ.get("PHARMACY_SECRET_KEY_FILE",
                                  "pharmacy_secret.key")
        secret = load_or_create_secret_key(key_file)
    app = create_app(engine, secret_key=secret)
    host = os.environ.get("PHARMACY_HOST", "127.0.0.1")
    port = int(os.environ.get("PHARMACY_PORT", "5000"))
    print(f"Pharmacy tracker running at http://{host}:{port}")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
