from datetime import datetime, timezone
from decimal import Decimal

from pharmacy import ledger


def test_norm_qty_quantizes_to_three_places():
    assert str(ledger.norm_qty(5)) == "5.000"
    assert str(ledger.norm_qty("2.5")) == "2.500"


def test_compute_hash_is_deterministic_and_chains():
    payload = ledger.canonical(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_id=1,
        lot_id=1,
        type_value="receive",
        quantity_delta=ledger.norm_qty(10),
        reason=None,
        witness_user_id=None,
        reference="PO-1",
    )
    h1 = ledger.compute_hash(ledger.GENESIS_HASH, payload)
    h2 = ledger.compute_hash(ledger.GENESIS_HASH, payload)
    assert h1 == h2
    assert len(h1) == 64
    assert ledger.compute_hash("deadbeef", payload) != h1


from pharmacy.db import init_db, make_session
from pharmacy.models import User, Drug, Lot


def _seed(session):
    user = User(username="op", display_name="Op", password_hash="x")
    drug = Drug(name="Fentanyl", strength="100mcg", form="vial", unit="vial")
    session.add_all([user, drug])
    session.flush()
    lot = Lot(drug_id=drug.id, lot_number="L1")
    session.add(lot)
    session.flush()
    return user, lot


def test_append_chains_prev_hash_and_derives_on_hand():
    session = make_session(init_db("sqlite://"))
    user, lot = _seed(session)

    e1 = ledger.append_entry(
        session, user_id=user.id, lot_id=lot.id,
        type="receive", quantity_delta=10,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    e2 = ledger.append_entry(
        session, user_id=user.id, lot_id=lot.id,
        type="dispense", quantity_delta=-3,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert e1.prev_hash == ledger.GENESIS_HASH
    assert e2.prev_hash == e1.entry_hash
    assert ledger.on_hand(session, lot.id) == Decimal("7.000")
