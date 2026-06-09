from decimal import Decimal

from pharmacy import inventory, reports
from pharmacy.models import EntryType


def test_inventory_snapshot_lists_lots_with_on_hand(session, actors, drug, ts):
    op, _ = actors
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="L1", quantity=10, timestamp=ts)
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="L2", quantity=4, timestamp=ts)
    rows = reports.inventory_snapshot(session)
    by_lot = {r["lot_number"]: r for r in rows}
    assert by_lot["L1"]["on_hand"] == Decimal("10.000")
    assert by_lot["L1"]["drug_name"] == "Oxycodone"
    assert by_lot["L2"]["on_hand"] == Decimal("4.000")


def test_audit_log_filters_by_type(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    inventory.dispense(session, user_id=op.id, lot_id=r.lot_id,
                       quantity=2, timestamp=ts)
    all_rows = reports.audit_log(session)
    assert len(all_rows) == 2
    disp = reports.audit_log(session, entry_type=EntryType.dispense)
    assert len(disp) == 1
    assert disp[0]["type"] == "dispense"
    assert disp[0]["operator"] == "Operator"


def test_alerts_flags_expired_expiring_and_low_stock(session, actors, drug, ts):
    from datetime import date

    op, _ = actors
    today = date(2026, 6, 9)

    # Expired: expiry in the past, plenty on hand.
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="EXP", quantity=10,
                      expiry_date=date(2026, 1, 1), timestamp=ts)
    # Expiring soon: within 30 days of `today`, plenty on hand.
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="SOON", quantity=10,
                      expiry_date=date(2026, 6, 19), timestamp=ts)
    # Low stock: far-future expiry, on-hand at/below threshold.
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="LOW", quantity=3,
                      expiry_date=date(2027, 1, 1), timestamp=ts)
    # Healthy: far-future expiry, plenty on hand -> not flagged.
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="OK", quantity=10,
                      expiry_date=date(2027, 1, 1), timestamp=ts)

    rows = reports.alerts(session, low_stock_threshold=5, today=today)
    by_lot = {r["lot_number"]: r for r in rows}

    assert "OK" not in by_lot  # healthy lot is not flagged at all
    assert "expired" in by_lot["EXP"]["reasons"]
    assert "expiring_soon" in by_lot["SOON"]["reasons"]
    assert "low_stock" in by_lot["LOW"]["reasons"]


def test_alerts_lot_with_no_expiry_only_checks_stock(session, actors, drug, ts):
    from datetime import date

    op, _ = actors
    inventory.receive(session, user_id=op.id, drug_id=drug.id,
                      lot_number="NOEXP", quantity=2, timestamp=ts)  # no expiry
    rows = reports.alerts(session, low_stock_threshold=5,
                          today=date(2026, 6, 9))
    by_lot = {r["lot_number"]: r for r in rows}
    assert by_lot["NOEXP"]["reasons"] == ["low_stock"]
