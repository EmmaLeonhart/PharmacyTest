from datetime import datetime, timezone

from pharmacy import ledger
from pharmacy.__main__ import check
from pharmacy.db import init_db, make_session
from pharmacy.models import Drug, Lot, User


def _seed(db_url):
    engine = init_db(db_url)
    session = make_session(engine)
    user = User(username="op", display_name="Op", password_hash="x")
    drug = Drug(name="Morphine", unit="vial")
    session.add_all([user, drug])
    session.flush()
    lot = Lot(drug_id=drug.id, lot_number="L1")
    session.add(lot)
    session.flush()
    ledger.append_entry(session, user_id=user.id, lot_id=lot.id,
                        type="receive", quantity_delta=10,
                        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    ledger.append_entry(session, user_id=user.id, lot_id=lot.id,
                        type="dispense", quantity_delta=-3,
                        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc))
    session.commit()
    session.close()


def test_check_returns_zero_on_intact_chain(tmp_path):
    db = tmp_path / "pharmacy.db"
    url = f"sqlite:///{db}"
    _seed(url)
    assert check(url) == 0


def test_check_returns_one_on_tampered_chain(tmp_path):
    db = tmp_path / "pharmacy.db"
    url = f"sqlite:///{db}"
    _seed(url)
    # Tamper: mutate a past entry's quantity directly, bypassing append_entry.
    engine = init_db(url)
    session = make_session(engine)
    from pharmacy.models import LedgerEntry
    entry = session.query(LedgerEntry).order_by(LedgerEntry.id.asc()).first()
    entry.quantity_delta = ledger.norm_qty(999)
    session.commit()
    session.close()

    assert check(url) == 1


def test_wsgi_module_exposes_serving_flask_app(monkeypatch):
    # Build against an in-memory DB and a fixed key so no real files are written.
    monkeypatch.setenv("PHARMACY_DB", "sqlite://")
    monkeypatch.setenv("PHARMACY_SECRET_KEY", "test")
    import importlib

    import pharmacy.wsgi as wsgi
    importlib.reload(wsgi)  # rebuild under the patched environment

    from flask import Flask
    assert isinstance(wsgi.app, Flask)
    resp = wsgi.app.test_client().get("/login")
    assert resp.status_code == 200
