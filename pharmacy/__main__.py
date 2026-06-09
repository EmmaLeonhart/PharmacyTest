"""Run the tracker: `python -m pharmacy`.

On first run, if no admin exists, one is created from PHARMACY_ADMIN_USER /
PHARMACY_ADMIN_PASSWORD (defaults admin/admin) and the credentials are printed
so staff can log in and change them.

`python -m pharmacy check` runs a one-shot audit-chain integrity check and exits
0 (intact) or 1 (tampering detected) — intended to be scheduled by the operator
via their own cron / Task Scheduler.
"""

import os
import sys

from pharmacy import ledger
from pharmacy.db import init_db, make_session
from pharmacy.web import build_app_from_env


def check(db_url):
    """Run the audit-chain integrity check against db_url. Returns an exit
    code: 0 if intact, 1 if tampering is detected."""
    engine = init_db(db_url)
    session = make_session(engine)
    try:
        ok, bad_id = ledger.verify_chain(session)
    finally:
        session.close()
    if ok:
        print("Audit chain intact. No tampering detected.")
        return 0
    print(f"Audit chain INTEGRITY FAILED at entry #{bad_id}. "
          f"History may have been altered.")
    return 1


def main():
    db_url = os.environ.get("PHARMACY_DB", "sqlite:///pharmacy.db")

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.exit(check(db_url))

    app = build_app_from_env()
    host = os.environ.get("PHARMACY_HOST", "127.0.0.1")
    port = int(os.environ.get("PHARMACY_PORT", "5000"))
    print(f"Pharmacy tracker running at http://{host}:{port}")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
