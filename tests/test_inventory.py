from decimal import Decimal

import pytest

from pharmacy import inventory, ledger
from pharmacy.models import EntryType


def test_receive_creates_lot_and_increments_on_hand(session, actors, drug, ts):
    op, _ = actors
    entry = inventory.receive(
        session, user_id=op.id, drug_id=drug.id, lot_number="L1",
        quantity=20, reference="PO-100", timestamp=ts,
    )
    assert entry.type is EntryType.receive
    assert ledger.on_hand(session, entry.lot_id) == Decimal("20.000")


def test_receive_reuses_existing_lot(session, actors, drug, ts):
    op, _ = actors
    e1 = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                           lot_number="L1", quantity=20, timestamp=ts)
    e2 = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                           lot_number="L1", quantity=5, timestamp=ts)
    assert e1.lot_id == e2.lot_id
    assert ledger.on_hand(session, e1.lot_id) == Decimal("25.000")


def test_dispense_decrements_on_hand(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=20, timestamp=ts)
    inventory.dispense(session, user_id=op.id, lot_id=r.lot_id,
                       quantity=8, reference="RX-1", timestamp=ts)
    assert ledger.on_hand(session, r.lot_id) == Decimal("12.000")


def test_dispense_cannot_go_negative(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=5, timestamp=ts)
    with pytest.raises(inventory.BusinessError):
        inventory.dispense(session, user_id=op.id, lot_id=r.lot_id,
                           quantity=6, timestamp=ts)
    assert ledger.on_hand(session, r.lot_id) == Decimal("5.000")
