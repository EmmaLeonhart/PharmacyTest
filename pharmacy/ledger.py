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


def canonical(*, timestamp, user_id, lot_id, type_value, quantity_delta,
              reason, witness_user_id, reference):
    """Build the canonical string that gets hashed for an entry."""
    parts = [
        timestamp.isoformat(),
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
