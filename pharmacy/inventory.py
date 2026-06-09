"""Inventory service layer. Enforces business rules, then appends ledger
entries. All quantity-changing operations go through here, never by writing
LedgerEntry rows directly."""

from datetime import date

from pharmacy import ledger
from pharmacy.models import Lot


class BusinessError(Exception):
    """Raised when an operation violates an inventory rule."""


def _get_or_create_lot(session, drug_id, lot_number, expiry_date=None):
    lot = (
        session.query(Lot)
        .filter_by(drug_id=drug_id, lot_number=lot_number)
        .one_or_none()
    )
    if lot is None:
        lot = Lot(drug_id=drug_id, lot_number=lot_number, expiry_date=expiry_date)
        session.add(lot)
        session.flush()
    return lot


def receive(session, *, user_id, drug_id, lot_number, quantity,
            expiry_date=None, reference=None, timestamp=None):
    """Record stock coming in. Creates the lot if new. quantity > 0."""
    if quantity <= 0:
        raise BusinessError("Received quantity must be positive.")
    lot = _get_or_create_lot(session, drug_id, lot_number, expiry_date)
    return ledger.append_entry(
        session, user_id=user_id, lot_id=lot.id, type="receive",
        quantity_delta=quantity, reference=reference, timestamp=timestamp,
    )
