"""Read-only report assembly for display and printing. Returns plain dicts."""

from pharmacy import ledger
from pharmacy.models import Drug, EntryType, LedgerEntry, Lot, User


def inventory_snapshot(session):
    """One row per lot with current derived on-hand."""
    rows = []
    for lot in session.query(Lot).order_by(Lot.id):
        drug = session.get(Drug, lot.drug_id)
        rows.append({
            "lot_id": lot.id,
            "lot_number": lot.lot_number,
            "expiry_date": lot.expiry_date,
            "drug_name": drug.name,
            "strength": drug.strength,
            "schedule": drug.schedule,
            "unit": drug.unit,
            "on_hand": ledger.on_hand(session, lot.id),
        })
    return rows


def audit_log(session, *, entry_type=None, lot_id=None, user_id=None,
              start=None, end=None):
    """Filtered, chronological audit entries as display dicts."""
    q = session.query(LedgerEntry).order_by(LedgerEntry.id.asc())
    if entry_type is not None:
        q = q.filter(LedgerEntry.type == entry_type)
    if lot_id is not None:
        q = q.filter(LedgerEntry.lot_id == lot_id)
    if user_id is not None:
        q = q.filter(LedgerEntry.user_id == user_id)
    if start is not None:
        q = q.filter(LedgerEntry.timestamp >= start)
    if end is not None:
        q = q.filter(LedgerEntry.timestamp <= end)

    rows = []
    for e in q:
        operator = session.get(User, e.user_id)
        witness = session.get(User, e.witness_user_id) if e.witness_user_id else None
        lot = session.get(Lot, e.lot_id)
        drug = session.get(Drug, lot.drug_id)
        rows.append({
            "id": e.id,
            "timestamp": e.timestamp,
            "type": e.type.value,
            "drug_name": drug.name,
            "lot_number": lot.lot_number,
            "quantity_delta": e.quantity_delta,
            "operator": operator.display_name,
            "witness": witness.display_name if witness else None,
            "reason": e.reason,
            "reference": e.reference,
            "entry_hash": e.entry_hash,
        })
    return rows
