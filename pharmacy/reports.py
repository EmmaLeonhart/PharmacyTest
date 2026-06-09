"""Read-only report assembly for display and printing. Returns plain dicts."""

from datetime import date, timedelta

from pharmacy import ledger
from pharmacy.models import Drug, LedgerEntry, Lot, User

EXPIRING_SOON_DAYS = 30


def alerts(session, *, low_stock_threshold, today=None):
    """Lots needing attention: expired, expiring within EXPIRING_SOON_DAYS, or
    with derived on-hand at/below low_stock_threshold. One dict per flagged lot,
    tagged with all applicable reasons. Lots with no flags are omitted; lots
    with no expiry date are only checked for low stock. `today` defaults to the
    current date (injectable for testing)."""
    if today is None:
        today = date.today()
    soon_cutoff = today + timedelta(days=EXPIRING_SOON_DAYS)

    rows = []
    for lot in session.query(Lot).order_by(Lot.id):
        reasons = []
        if lot.expiry_date is not None:
            if lot.expiry_date < today:
                reasons.append("expired")
            elif lot.expiry_date <= soon_cutoff:
                reasons.append("expiring_soon")
        on_hand = ledger.on_hand(session, lot.id)
        if on_hand <= low_stock_threshold:
            reasons.append("low_stock")
        if not reasons:
            continue
        drug = session.get(Drug, lot.drug_id)
        rows.append({
            "lot_id": lot.id,
            "lot_number": lot.lot_number,
            "expiry_date": lot.expiry_date,
            "drug_name": drug.name,
            "strength": drug.strength,
            "unit": drug.unit,
            "on_hand": on_hand,
            "reasons": reasons,
        })
    return rows


def lot_history(session, lot_id):
    """Full chronological ledger for one lot, each entry annotated with the
    running on-hand after it. Returns a header dict plus an `entries` list; the
    last entry's running_balance equals the lot's derived on-hand."""
    lot = session.get(Lot, lot_id)
    drug = session.get(Drug, lot.drug_id)
    entries = []
    running = ledger.norm_qty(0)
    query = (session.query(LedgerEntry)
             .filter(LedgerEntry.lot_id == lot_id)
             .order_by(LedgerEntry.id.asc()))
    for e in query:
        running = ledger.norm_qty(running + e.quantity_delta)
        operator = session.get(User, e.user_id)
        witness = session.get(User, e.witness_user_id) if e.witness_user_id else None
        entries.append({
            "id": e.id,
            "timestamp": e.timestamp,
            "type": e.type.value,
            "quantity_delta": e.quantity_delta,
            "running_balance": running,
            "operator": operator.display_name,
            "witness": witness.display_name if witness else None,
            "reason": e.reason,
            "reference": e.reference,
        })
    return {
        "lot_id": lot.id,
        "lot_number": lot.lot_number,
        "expiry_date": lot.expiry_date,
        "drug_name": drug.name,
        "strength": drug.strength,
        "unit": drug.unit,
        "entries": entries,
    }


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
