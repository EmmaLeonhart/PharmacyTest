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


def dispense(session, *, user_id, lot_id, quantity, reference=None,
             reason=None, timestamp=None):
    """Record stock going out. Rejected if it would drive on-hand negative."""
    if quantity <= 0:
        raise BusinessError("Dispensed quantity must be positive.")
    available = ledger.on_hand(session, lot_id)
    if ledger.norm_qty(quantity) > available:
        raise BusinessError(
            f"Cannot dispense {quantity}; only {available} on hand."
        )
    return ledger.append_entry(
        session, user_id=user_id, lot_id=lot_id, type="dispense",
        quantity_delta=-ledger.norm_qty(quantity), reason=reason,
        reference=reference, timestamp=timestamp,
    )


def dispose(session, *, user_id, lot_id, quantity, witness_user_id,
            reason, timestamp=None):
    """Record destruction/wastage. Requires a distinct witness and a reason."""
    if quantity <= 0:
        raise BusinessError("Disposed quantity must be positive.")
    if witness_user_id is None:
        raise BusinessError("Disposal requires a witness.")
    if witness_user_id == user_id:
        raise BusinessError("Witness must be a different user than the operator.")
    if not (reason or "").strip():
        raise BusinessError("Disposal requires a reason.")
    available = ledger.on_hand(session, lot_id)
    if ledger.norm_qty(quantity) > available:
        raise BusinessError(
            f"Cannot dispose {quantity}; only {available} on hand."
        )
    return ledger.append_entry(
        session, user_id=user_id, lot_id=lot_id, type="dispose",
        quantity_delta=-ledger.norm_qty(quantity), reason=reason,
        witness_user_id=witness_user_id, timestamp=timestamp,
    )
