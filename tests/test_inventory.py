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


def test_dispose_requires_witness_and_reason(session, actors, drug, ts):
    op, wit = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)

    with pytest.raises(inventory.BusinessError):
        inventory.dispose(session, user_id=op.id, lot_id=r.lot_id,
                          quantity=2, witness_user_id=None,
                          reason="expired", timestamp=ts)
    with pytest.raises(inventory.BusinessError):
        inventory.dispose(session, user_id=op.id, lot_id=r.lot_id,
                          quantity=2, witness_user_id=wit.id,
                          reason="", timestamp=ts)

    entry = inventory.dispose(session, user_id=op.id, lot_id=r.lot_id,
                              quantity=2, witness_user_id=wit.id,
                              reason="broken vial", timestamp=ts)
    assert entry.witness_user_id == wit.id
    assert ledger.on_hand(session, r.lot_id) == Decimal("8.000")


def test_dispose_witness_must_differ_from_operator(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    with pytest.raises(inventory.BusinessError):
        inventory.dispose(session, user_id=op.id, lot_id=r.lot_id,
                          quantity=2, witness_user_id=op.id,
                          reason="expired", timestamp=ts)


def test_reconcile_records_count_and_discrepancy(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    count = inventory.reconcile(session, user_id=op.id, lot_id=r.lot_id,
                                counted_qty=9, timestamp=ts)
    assert count.expected_qty == Decimal("10.000")
    assert count.counted_qty == Decimal("9.000")
    assert count.discrepancy == Decimal("-1.000")
    assert ledger.on_hand(session, r.lot_id) == Decimal("10.000")


def test_reconcile_with_adjust_corrects_on_hand(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    count = inventory.reconcile(session, user_id=op.id, lot_id=r.lot_id,
                                counted_qty=9, post_adjustment=True,
                                reason="count short", timestamp=ts)
    assert count.adjust_entry_id is not None
    assert ledger.on_hand(session, r.lot_id) == Decimal("9.000")


def test_reconcile_adjust_requires_reason(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    with pytest.raises(inventory.BusinessError):
        inventory.reconcile(session, user_id=op.id, lot_id=r.lot_id,
                            counted_qty=9, post_adjustment=True,
                            reason="", timestamp=ts)


def test_reconcile_no_discrepancy_posts_no_adjustment(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    count = inventory.reconcile(session, user_id=op.id, lot_id=r.lot_id,
                                counted_qty=10, post_adjustment=True,
                                reason="routine count", timestamp=ts)
    assert count.discrepancy == Decimal("0.000")
    assert count.adjust_entry_id is None
    assert ledger.on_hand(session, r.lot_id) == Decimal("10.000")


def test_dispose_cannot_go_negative(session, actors, drug, ts):
    op, wit = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=3, timestamp=ts)
    with pytest.raises(inventory.BusinessError):
        inventory.dispose(session, user_id=op.id, lot_id=r.lot_id,
                          quantity=4, witness_user_id=wit.id,
                          reason="expired", timestamp=ts)
    assert ledger.on_hand(session, r.lot_id) == Decimal("3.000")


def test_dispense_exactly_on_hand_succeeds(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=5, timestamp=ts)
    inventory.dispense(session, user_id=op.id, lot_id=r.lot_id,
                       quantity=5, timestamp=ts)
    assert ledger.on_hand(session, r.lot_id) == Decimal("0.000")
