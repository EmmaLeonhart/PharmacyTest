from datetime import datetime, timezone
from decimal import Decimal

from pharmacy import ledger


def test_norm_qty_quantizes_to_three_places():
    assert str(ledger.norm_qty(5)) == "5.000"
    assert str(ledger.norm_qty("2.5")) == "2.500"


def test_compute_hash_is_deterministic_and_chains():
    payload = ledger.canonical(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_id=1,
        lot_id=1,
        type_value="receive",
        quantity_delta=ledger.norm_qty(10),
        reason=None,
        witness_user_id=None,
        reference="PO-1",
    )
    h1 = ledger.compute_hash(ledger.GENESIS_HASH, payload)
    h2 = ledger.compute_hash(ledger.GENESIS_HASH, payload)
    assert h1 == h2
    assert len(h1) == 64
    assert ledger.compute_hash("deadbeef", payload) != h1
