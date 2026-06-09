"""Append-only, hash-chained ledger. Pure domain logic — no Flask/HTTP."""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func

from pharmacy.models import EntryType, LedgerEntry

GENESIS_HASH = "0" * 64
QTY_SCALE = Decimal("0.001")


def norm_qty(value):
    """Normalize any numeric input to a 3-dp Decimal so hashing is stable
    across the SQLite Numeric(12, 3) round-trip."""
    return Decimal(str(value)).quantize(QTY_SCALE)


def norm_ts(timestamp):
    """Normalize a timestamp to a stable naive-UTC isoformat so hashing is
    stable across the SQLite DateTime round-trip, which drops tzinfo.

    An aware timestamp is converted to UTC and stripped of tzinfo; a naive
    timestamp (as read back from the DB, where it was stored as UTC) is taken
    as-is. Both paths yield the same canonical string for the same instant."""
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    return timestamp.isoformat()


def canonical(*, timestamp, user_id, lot_id, type_value, quantity_delta,
              reason, witness_user_id, reference):
    """Build the canonical string that gets hashed for an entry."""
    parts = [
        norm_ts(timestamp),
        str(user_id),
        str(lot_id),
        type_value,
        str(quantity_delta),
        reason or "",
        str(witness_user_id) if witness_user_id is not None else "",
        reference or "",
    ]
    return "|".join(parts)


def compute_hash(prev_hash, payload):
    """SHA-256 of the previous hash concatenated with the payload."""
    return hashlib.sha256((prev_hash + payload).encode("utf-8")).hexdigest()


def last_entry(session):
    """Most recently inserted entry, or None."""
    return (
        session.query(LedgerEntry)
        .order_by(LedgerEntry.id.desc())
        .first()
    )


def append_entry(session, *, user_id, lot_id, type, quantity_delta,
                 reason=None, witness_user_id=None, reference=None,
                 timestamp=None):
    """Create and persist a hash-chained ledger entry. Returns the entry."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    type_value = type.value if isinstance(type, EntryType) else type
    qty = norm_qty(quantity_delta)

    prev = last_entry(session)
    prev_hash = prev.entry_hash if prev else GENESIS_HASH

    payload = canonical(
        timestamp=timestamp, user_id=user_id, lot_id=lot_id,
        type_value=type_value, quantity_delta=qty,
        reason=reason, witness_user_id=witness_user_id, reference=reference,
    )
    entry_hash = compute_hash(prev_hash, payload)

    entry = LedgerEntry(
        timestamp=timestamp, user_id=user_id, lot_id=lot_id,
        type=EntryType(type_value), quantity_delta=qty,
        reason=reason, witness_user_id=witness_user_id, reference=reference,
        prev_hash=prev_hash, entry_hash=entry_hash,
    )
    session.add(entry)
    session.flush()
    return entry


def on_hand(session, lot_id):
    """Derived on-hand quantity for a lot = sum of its quantity deltas."""
    total = (
        session.query(func.coalesce(func.sum(LedgerEntry.quantity_delta), 0))
        .filter(LedgerEntry.lot_id == lot_id)
        .scalar()
    )
    return norm_qty(total)


def verify_chain(session):
    """Re-walk the whole ledger in insertion order. Return (ok, first_bad_id).
    ok is False at the first entry whose stored hashes do not match a
    recomputation, which catches any edit or deletion of history."""
    prev_hash = GENESIS_HASH
    for entry in session.query(LedgerEntry).order_by(LedgerEntry.id.asc()):
        payload = canonical(
            timestamp=entry.timestamp, user_id=entry.user_id,
            lot_id=entry.lot_id, type_value=entry.type.value,
            quantity_delta=norm_qty(entry.quantity_delta),
            reason=entry.reason, witness_user_id=entry.witness_user_id,
            reference=entry.reference,
        )
        expected = compute_hash(prev_hash, payload)
        if entry.prev_hash != prev_hash or entry.entry_hash != expected:
            return (False, entry.id)
        prev_hash = entry.entry_hash
    return (True, None)
