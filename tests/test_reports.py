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
