# Pharmacy Controlled-Substance Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, multi-user pharmacy controlled-substances tracker whose inventory is an append-only, hash-chained audit ledger, with receive/dispense/dispose/reconcile flows, login, and printable reports.

**Architecture:** Server-rendered Flask app over SQLite (SQLAlchemy). A pure-domain `ledger` module is the source of truth: every action is an immutable, hash-chained `LedgerEntry`; on-hand quantity is derived by summing the ledger, never stored mutably. A thin `inventory` service layer enforces business rules; `auth` handles users/sessions; `reports` assembles printable data; `web/` is routes + Jinja templates.

**Tech Stack:** Python 3, Flask, SQLAlchemy, Werkzeug (password hashing + WSGI), pytest, GitHub Actions.

---

## File Structure

```
pharmacy/
  __init__.py        # package marker + version
  models.py          # SQLAlchemy schema: User, Drug, Lot, LedgerEntry, Count, enums, Base
  db.py              # engine/session factory, init_db()
  ledger.py          # pure domain: hash chain, append_entry, on_hand, verify_chain
  inventory.py       # services: receive, dispense, dispose, reconcile (+ BusinessError)
  auth.py            # create_user, authenticate, password hashing, role checks
  reports.py         # inventory_snapshot, audit_log, reconciliation rows
  web/
    __init__.py      # Flask app factory create_app()
    routes.py        # all routes (auth, inventory ops, reports)
    templates/       # Jinja templates
    static/print.css # print stylesheet
  __main__.py        # `python -m pharmacy` entry; first-run admin bootstrap
tests/
  conftest.py        # in-memory DB session fixture, sample data helpers
  test_ledger.py
  test_inventory.py
  test_auth.py
  test_reports.py
  test_web.py
requirements.txt
pytest.ini
.github/workflows/ci.yml
```

Each module has one responsibility. `ledger.py` has **no** Flask/HTTP imports so it can be tested in isolation.

---

## Task 1: Project scaffold, dependencies, and CI

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `pharmacy/__init__.py`
- Create: `tests/__init__.py`
- Create: `.github/workflows/ci.yml`
- Modify: `.gitignore`

- [ ] **Step 1: Write `requirements.txt`**

```text
Flask>=3.0
SQLAlchemy>=2.0
Werkzeug>=3.0
pytest>=8.0
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 3: Write `pharmacy/__init__.py`**

```python
"""Pharmacy controlled-substance tracker."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Write `tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Append to `.gitignore`**

```text

# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/

# App data
*.sqlite3
pharmacy.db
instance/
```

- [ ] **Step 6: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

- [ ] **Step 7: Install locally and confirm pytest runs**

Run: `pip install -r requirements.txt && pytest`
Expected: pytest runs and reports `no tests ran` (exit code 5) — dependencies install cleanly.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pytest.ini pharmacy/__init__.py tests/__init__.py .github/workflows/ci.yml .gitignore
git commit -m "chore: scaffold package, deps, pytest, and CI"
```

---

## Task 2: Database models

**Files:**
- Create: `pharmacy/models.py`
- Create: `pharmacy/db.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:

```python
from datetime import date
from pharmacy.db import init_db, make_session
from pharmacy.models import User, Drug, Lot, Role, EntryType


def test_can_create_and_query_core_entities():
    engine = init_db("sqlite://")  # in-memory
    session = make_session(engine)

    user = User(username="alice", display_name="Alice", password_hash="x", role=Role.admin)
    drug = Drug(name="Morphine", strength="10mg", form="vial", schedule="CII", unit="vial")
    session.add_all([user, drug])
    session.flush()

    lot = Lot(drug_id=drug.id, lot_number="LOT123", expiry_date=date(2027, 1, 1))
    session.add(lot)
    session.flush()

    assert session.query(User).filter_by(username="alice").one().role is Role.admin
    assert session.query(Lot).one().drug.name == "Morphine"
    assert EntryType.dispense.value == "dispense"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.models'`.

- [ ] **Step 3: Write `pharmacy/models.py`**

```python
"""SQLAlchemy schema for the pharmacy tracker."""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Role(enum.Enum):
    admin = "admin"
    operator = "operator"


class EntryType(enum.Enum):
    receive = "receive"
    dispense = "dispense"
    dispose = "dispose"
    adjust = "adjust"
    count = "count"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.operator)
    active = Column(Boolean, nullable=False, default=True)


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    strength = Column(String)
    form = Column(String)
    code = Column(String)
    schedule = Column(String)  # CII..CV
    unit = Column(String, nullable=False, default="unit")

    lots = relationship("Lot", back_populates="drug")


class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    lot_number = Column(String, nullable=False)
    expiry_date = Column(Date)

    drug = relationship("Drug", back_populates="lots")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    type = Column(Enum(EntryType), nullable=False)
    quantity_delta = Column(Numeric(12, 3), nullable=False)
    reason = Column(String)
    witness_user_id = Column(Integer, ForeignKey("users.id"))
    reference = Column(String)
    prev_hash = Column(String, nullable=False)
    entry_hash = Column(String, nullable=False)


class Count(Base):
    __tablename__ = "counts"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    counted_qty = Column(Numeric(12, 3), nullable=False)
    expected_qty = Column(Numeric(12, 3), nullable=False)
    discrepancy = Column(Numeric(12, 3), nullable=False)
    adjust_entry_id = Column(Integer, ForeignKey("ledger_entries.id"))
```

- [ ] **Step 4: Write `pharmacy/db.py`**

```python
"""Engine and session helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pharmacy.models import Base


def init_db(url="sqlite:///pharmacy.db"):
    """Create the engine and all tables; return the engine."""
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


def make_session(engine):
    """Return a new Session bound to the engine."""
    Session = sessionmaker(bind=engine, future=True)
    return Session()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pharmacy/models.py pharmacy/db.py tests/test_models.py
git commit -m "feat: add SQLAlchemy schema and db helpers"
```

---

## Task 3: Ledger hashing primitives

**Files:**
- Create: `pharmacy/ledger.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Write the failing test**

`tests/test_ledger.py`:

```python
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
    # different prev_hash -> different result
    assert ledger.compute_hash("deadbeef", payload) != h1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ledger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.ledger'`.

- [ ] **Step 3: Write `pharmacy/ledger.py` (primitives only)**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ledger.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/ledger.py tests/test_ledger.py
git commit -m "feat: add ledger hashing primitives"
```

---

## Task 4: Ledger append and on-hand derivation

**Files:**
- Modify: `pharmacy/ledger.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_ledger.py`:

```python
from pharmacy.db import init_db, make_session
from pharmacy.models import User, Drug, Lot


def _seed(session):
    user = User(username="op", display_name="Op", password_hash="x")
    drug = Drug(name="Fentanyl", strength="100mcg", form="vial", unit="vial")
    session.add_all([user, drug])
    session.flush()
    lot = Lot(drug_id=drug.id, lot_number="L1")
    session.add(lot)
    session.flush()
    return user, lot


def test_append_chains_prev_hash_and_derives_on_hand():
    session = make_session(init_db("sqlite://"))
    user, lot = _seed(session)

    e1 = ledger.append_entry(
        session, user_id=user.id, lot_id=lot.id,
        type="receive", quantity_delta=10,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    e2 = ledger.append_entry(
        session, user_id=user.id, lot_id=lot.id,
        type="dispense", quantity_delta=-3,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert e1.prev_hash == ledger.GENESIS_HASH
    assert e2.prev_hash == e1.entry_hash
    assert ledger.on_hand(session, lot.id) == Decimal("7.000")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ledger.py::test_append_chains_prev_hash_and_derives_on_hand -v`
Expected: FAIL — `AttributeError: module 'pharmacy.ledger' has no attribute 'append_entry'`.

- [ ] **Step 3: Add `last_entry`, `append_entry`, `on_hand` to `pharmacy/ledger.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ledger.py -v`
Expected: PASS (all ledger tests).

- [ ] **Step 5: Commit**

```bash
git add pharmacy/ledger.py tests/test_ledger.py
git commit -m "feat: add ledger append and on-hand derivation"
```

---

## Task 5: Chain verification and tamper detection

**Files:**
- Modify: `pharmacy/ledger.py`
- Test: `tests/test_ledger.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_ledger.py`:

```python
def test_verify_chain_detects_tampering():
    session = make_session(init_db("sqlite://"))
    user, lot = _seed(session)
    ledger.append_entry(session, user_id=user.id, lot_id=lot.id,
                        type="receive", quantity_delta=10,
                        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    tampered = ledger.append_entry(session, user_id=user.id, lot_id=lot.id,
                        type="dispense", quantity_delta=-3,
                        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc))

    ok, bad_id = ledger.verify_chain(session)
    assert ok is True
    assert bad_id is None

    # Mutate a past entry's quantity directly, bypassing append_entry.
    tampered.quantity_delta = ledger.norm_qty(-1)
    session.flush()

    ok, bad_id = ledger.verify_chain(session)
    assert ok is False
    assert bad_id == tampered.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ledger.py::test_verify_chain_detects_tampering -v`
Expected: FAIL — `AttributeError: module 'pharmacy.ledger' has no attribute 'verify_chain'`.

- [ ] **Step 3: Add `verify_chain` to `pharmacy/ledger.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ledger.py -v`
Expected: PASS (all ledger tests).

- [ ] **Step 5: Commit**

```bash
git add pharmacy/ledger.py tests/test_ledger.py
git commit -m "feat: add ledger chain verification and tamper detection"
```

---

## Task 6: Shared test fixtures (conftest)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
from datetime import datetime, timezone

import pytest

from pharmacy.db import init_db, make_session
from pharmacy.models import Drug, Lot, User, Role


@pytest.fixture
def session():
    return make_session(init_db("sqlite://"))


@pytest.fixture
def actors(session):
    """An operator and a witness user."""
    op = User(username="op", display_name="Operator",
              password_hash="x", role=Role.operator)
    wit = User(username="wit", display_name="Witness",
               password_hash="x", role=Role.operator)
    session.add_all([op, wit])
    session.flush()
    return op, wit


@pytest.fixture
def drug(session):
    d = Drug(name="Oxycodone", strength="5mg", form="tablet",
             schedule="CII", unit="tablet")
    session.add(d)
    session.flush()
    return d


@pytest.fixture
def ts():
    return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

- [ ] **Step 2: Confirm fixtures import cleanly**

Run: `pytest tests/test_ledger.py -q`
Expected: PASS (existing tests still green; conftest does not break collection).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared db/session fixtures"
```

---

## Task 7: Inventory service — receive

**Files:**
- Create: `pharmacy/inventory.py`
- Test: `tests/test_inventory.py`

- [ ] **Step 1: Write the failing test**

`tests/test_inventory.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inventory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.inventory'`.

- [ ] **Step 3: Write `pharmacy/inventory.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/inventory.py tests/test_inventory.py
git commit -m "feat: add inventory receive service"
```

---

## Task 8: Inventory service — dispense (negative-stock rejection)

**Files:**
- Modify: `pharmacy/inventory.py`
- Test: `tests/test_inventory.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_inventory.py`:

```python
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
    # On-hand unchanged after the rejected dispense.
    assert ledger.on_hand(session, r.lot_id) == Decimal("5.000")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inventory.py -k dispense -v`
Expected: FAIL — `AttributeError: module 'pharmacy.inventory' has no attribute 'dispense'`.

- [ ] **Step 3: Add `dispense` to `pharmacy/inventory.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/inventory.py tests/test_inventory.py
git commit -m "feat: add dispense service with negative-stock rejection"
```

---

## Task 9: Inventory service — dispose (witness required)

**Files:**
- Modify: `pharmacy/inventory.py`
- Test: `tests/test_inventory.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_inventory.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inventory.py -k dispose -v`
Expected: FAIL — `AttributeError: module 'pharmacy.inventory' has no attribute 'dispose'`.

- [ ] **Step 3: Add `dispose` to `pharmacy/inventory.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/inventory.py tests/test_inventory.py
git commit -m "feat: add dispose service requiring a distinct witness and reason"
```

---

## Task 10: Inventory service — reconcile (count + optional adjust)

**Files:**
- Modify: `pharmacy/inventory.py`
- Test: `tests/test_inventory.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_inventory.py`:

```python
def test_reconcile_records_count_and_discrepancy(session, actors, drug, ts):
    op, _ = actors
    r = inventory.receive(session, user_id=op.id, drug_id=drug.id,
                          lot_number="L1", quantity=10, timestamp=ts)
    count = inventory.reconcile(session, user_id=op.id, lot_id=r.lot_id,
                                counted_qty=9, timestamp=ts)
    assert count.expected_qty == Decimal("10.000")
    assert count.counted_qty == Decimal("9.000")
    assert count.discrepancy == Decimal("-1.000")
    # No adjust posted -> on-hand unchanged.
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inventory.py -k reconcile -v`
Expected: FAIL — `AttributeError: module 'pharmacy.inventory' has no attribute 'reconcile'`.

- [ ] **Step 3: Add `reconcile` to `pharmacy/inventory.py`**

Add the import at the top of the file (below the existing imports):

```python
from datetime import datetime, timezone

from pharmacy.models import Count
```

Then add the function:

```python
def reconcile(session, *, user_id, lot_id, counted_qty, post_adjustment=False,
              reason=None, timestamp=None):
    """Record a physical count against expected on-hand. Optionally post an
    `adjust` ledger entry to correct the difference (requires a reason)."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    expected = ledger.on_hand(session, lot_id)
    counted = ledger.norm_qty(counted_qty)
    discrepancy = counted - expected

    adjust_entry = None
    if post_adjustment and discrepancy != 0:
        if not (reason or "").strip():
            raise BusinessError("Posting an adjustment requires a reason.")
        adjust_entry = ledger.append_entry(
            session, user_id=user_id, lot_id=lot_id, type="adjust",
            quantity_delta=discrepancy, reason=reason, timestamp=timestamp,
        )

    count = Count(
        timestamp=timestamp, lot_id=lot_id, user_id=user_id,
        counted_qty=counted, expected_qty=expected, discrepancy=discrepancy,
        adjust_entry_id=adjust_entry.id if adjust_entry else None,
    )
    session.add(count)
    session.flush()
    return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_inventory.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/inventory.py tests/test_inventory.py
git commit -m "feat: add reconcile service with optional audited adjustment"
```

---

## Task 11: Auth — users, password hashing, authentication

**Files:**
- Create: `pharmacy/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

`tests/test_auth.py`:

```python
import pytest

from pharmacy import auth
from pharmacy.models import Role


def test_create_user_hashes_password(session):
    user = auth.create_user(session, username="alice", display_name="Alice",
                            password="s3cret", role=Role.admin)
    assert user.password_hash != "s3cret"
    assert user.role is Role.admin


def test_authenticate_succeeds_with_correct_password(session):
    auth.create_user(session, username="bob", display_name="Bob",
                     password="hunter2")
    user = auth.authenticate(session, "bob", "hunter2")
    assert user is not None
    assert user.username == "bob"


def test_authenticate_fails_with_wrong_password(session):
    auth.create_user(session, username="bob", display_name="Bob",
                     password="hunter2")
    assert auth.authenticate(session, "bob", "wrong") is None


def test_authenticate_rejects_inactive_user(session):
    u = auth.create_user(session, username="bob", display_name="Bob",
                         password="hunter2")
    u.active = False
    session.flush()
    assert auth.authenticate(session, "bob", "hunter2") is None


def test_duplicate_username_rejected(session):
    auth.create_user(session, username="bob", display_name="Bob", password="x")
    with pytest.raises(auth.AuthError):
        auth.create_user(session, username="bob", display_name="Bob2",
                         password="y")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.auth'`.

- [ ] **Step 3: Write `pharmacy/auth.py`**

```python
"""User management and authentication."""

from werkzeug.security import check_password_hash, generate_password_hash

from pharmacy.models import Role, User


class AuthError(Exception):
    """Raised on user-management failures (e.g. duplicate username)."""


def create_user(session, *, username, display_name, password,
                role=Role.operator):
    existing = session.query(User).filter_by(username=username).one_or_none()
    if existing is not None:
        raise AuthError(f"Username {username!r} already exists.")
    user = User(
        username=username,
        display_name=display_name,
        password_hash=generate_password_hash(password),
        role=role,
        active=True,
    )
    session.add(user)
    session.flush()
    return user


def authenticate(session, username, password):
    """Return the User on success, else None."""
    user = session.query(User).filter_by(username=username).one_or_none()
    if user is None or not user.active:
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/auth.py tests/test_auth.py
git commit -m "feat: add user management and authentication"
```

---

## Task 12: Reports — inventory snapshot, audit log, reconciliation rows

**Files:**
- Create: `pharmacy/reports.py`
- Test: `tests/test_reports.py`

- [ ] **Step 1: Write the failing test**

`tests/test_reports.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reports.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.reports'`.

- [ ] **Step 3: Write `pharmacy/reports.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reports.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pharmacy/reports.py tests/test_reports.py
git commit -m "feat: add inventory snapshot and filtered audit-log reports"
```

---

## Task 13: Flask app factory and login/logout

**Files:**
- Create: `pharmacy/web/__init__.py`
- Create: `pharmacy/web/routes.py`
- Create: `pharmacy/web/templates/base.html`
- Create: `pharmacy/web/templates/login.html`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write the failing test**

`tests/test_web.py`:

```python
import pytest

from pharmacy import auth
from pharmacy.db import init_db, make_session
from pharmacy.models import Role
from pharmacy.web import create_app


@pytest.fixture
def app():
    engine = init_db("sqlite://")
    session = make_session(engine)
    auth.create_user(session, username="admin", display_name="Admin",
                     password="pw", role=Role.admin)
    session.commit()
    app = create_app(engine, secret_key="test")
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_required_redirects_to_login(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_succeeds_and_dashboard_loads(client):
    resp = client.post("/login", data={"username": "admin", "password": "pw"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Inventory" in resp.data


def test_login_fails_with_bad_password(client):
    resp = client.post("/login", data={"username": "admin", "password": "no"},
                       follow_redirects=True)
    assert b"Invalid" in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_web.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.web'`.

- [ ] **Step 3: Write `pharmacy/web/__init__.py`**

```python
"""Flask app factory."""

from flask import Flask

from pharmacy.db import make_session


def create_app(engine, secret_key="dev-insecure-change-me"):
    app = Flask(__name__)
    app.secret_key = secret_key
    app.config["ENGINE"] = engine

    @app.before_request
    def _open_session():
        from flask import g
        g.db = make_session(engine)

    @app.teardown_request
    def _close_session(exc):
        from flask import g
        db = g.pop("db", None)
        if db is not None:
            if exc is None:
                db.commit()
            else:
                db.rollback()
            db.close()

    from pharmacy.web.routes import bp
    app.register_blueprint(bp)
    return app
```

- [ ] **Step 4: Write `pharmacy/web/routes.py` (auth routes only for now)**

```python
"""HTTP routes."""

from functools import wraps

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
)

from pharmacy import auth, reports
from pharmacy.models import User

bp = Blueprint("main", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        g.user = g.db.get(User, session["user_id"])
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = auth.authenticate(g.db, request.form["username"],
                                 request.form["password"])
        if user is None:
            flash("Invalid username or password.", "error")
        else:
            session["user_id"] = user.id
            return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@bp.route("/")
@login_required
def dashboard():
    rows = reports.inventory_snapshot(g.db)
    return render_template("dashboard.html", rows=rows)
```

- [ ] **Step 5: Write `pharmacy/web/templates/base.html`**

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{% block title %}Pharmacy Tracker{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='print.css') }}">
</head>
<body>
  <header class="no-print">
    {% if session.get('user_id') %}
      <nav>
        <a href="{{ url_for('main.dashboard') }}">Inventory</a>
        <a href="{{ url_for('main.audit') }}">Audit log</a>
        <a href="{{ url_for('main.logout') }}">Log out</a>
      </nav>
    {% endif %}
  </header>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, message in messages %}
      <p class="flash {{ category }}">{{ message }}</p>
    {% endfor %}
  {% endwith %}
  <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

- [ ] **Step 6: Write `pharmacy/web/templates/login.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Log in</h1>
<form method="post" action="{{ url_for('main.login') }}">
  <label>Username <input name="username" required></label>
  <label>Password <input name="password" type="password" required></label>
  <button type="submit">Log in</button>
</form>
{% endblock %}
```

- [ ] **Step 7: Write a minimal `pharmacy/web/templates/dashboard.html`** (expanded in Task 14)

```html
{% extends "base.html" %}
{% block content %}
<h1>Inventory</h1>
<table>
  <thead><tr><th>Drug</th><th>Lot</th><th>On hand</th><th>Unit</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr>
      <td>{{ r.drug_name }} {{ r.strength }}</td>
      <td>{{ r.lot_number }}</td>
      <td>{{ r.on_hand }}</td>
      <td>{{ r.unit }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 8: Create an empty `pharmacy/web/static/print.css`** (filled in Task 14)

```css
/* print styles added in Task 14 */
```

- [ ] **Step 9: Add a stub `audit` route so `base.html`'s nav link resolves**

Append to `pharmacy/web/routes.py`:

```python
@bp.route("/audit")
@login_required
def audit():
    rows = reports.audit_log(g.db)
    return render_template("audit.html", rows=rows)
```

And create `pharmacy/web/templates/audit.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>Audit log</h1>
<table>
  <thead><tr><th>#</th><th>Time</th><th>Type</th><th>Drug</th><th>Lot</th>
    <th>Δ Qty</th><th>Operator</th><th>Witness</th><th>Reason</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr>
      <td>{{ r.id }}</td><td>{{ r.timestamp }}</td><td>{{ r.type }}</td>
      <td>{{ r.drug_name }}</td><td>{{ r.lot_number }}</td>
      <td>{{ r.quantity_delta }}</td><td>{{ r.operator }}</td>
      <td>{{ r.witness or '' }}</td><td>{{ r.reason or '' }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `pytest tests/test_web.py -v`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add pharmacy/web tests/test_web.py
git commit -m "feat: add Flask app factory, login, and dashboard/audit views"
```

---

## Task 14: Inventory operation routes, forms, and print styles

**Files:**
- Modify: `pharmacy/web/routes.py`
- Create: `pharmacy/web/templates/receive.html`, `dispense.html`, `dispose.html`, `reconcile.html`, `verify.html`
- Modify: `pharmacy/web/templates/base.html` (add nav links)
- Modify: `pharmacy/web/templates/dashboard.html` (add per-lot action links)
- Modify: `pharmacy/web/static/print.css`
- Test: `tests/test_web.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_web.py`:

```python
def _login(client):
    client.post("/login", data={"username": "admin", "password": "pw"})


def test_receive_then_dispense_via_web(client, app):
    _login(client)
    # Need a drug to receive into; create one through the catalog route.
    client.post("/drugs/new", data={"name": "Morphine", "strength": "10mg",
                                     "form": "vial", "schedule": "CII",
                                     "unit": "vial"})
    client.post("/receive", data={"drug_id": "1", "lot_number": "L1",
                                  "quantity": "10", "reference": "PO-1"})
    resp = client.get("/")
    assert b"10.000" in resp.data

    client.post("/dispense", data={"lot_id": "1", "quantity": "4",
                                   "reference": "RX-9"})
    resp = client.get("/")
    assert b"6.000" in resp.data


def test_verify_integrity_reports_ok(client):
    _login(client)
    resp = client.get("/verify")
    assert b"intact" in resp.data.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_web.py -k "receive_then_dispense or verify_integrity" -v`
Expected: FAIL — 404/`BuildError` because `/drugs/new`, `/receive`, `/dispense`, `/verify` don't exist yet.

- [ ] **Step 3: Add catalog + operation routes to `pharmacy/web/routes.py`**

Add these imports at the top:

```python
from pharmacy import inventory, ledger
from pharmacy.models import Drug, EntryType, Role
```

Append these routes:

```python
@bp.route("/drugs/new", methods=["GET", "POST"])
@login_required
def new_drug():
    if request.method == "POST":
        drug = Drug(
            name=request.form["name"],
            strength=request.form.get("strength"),
            form=request.form.get("form"),
            code=request.form.get("code"),
            schedule=request.form.get("schedule"),
            unit=request.form.get("unit") or "unit",
        )
        g.db.add(drug)
        g.db.flush()
        flash(f"Added {drug.name}.", "ok")
        return redirect(url_for("main.dashboard"))
    return render_template("new_drug.html")


@bp.route("/receive", methods=["GET", "POST"])
@login_required
def receive():
    if request.method == "POST":
        try:
            inventory.receive(
                g.db, user_id=g.user.id,
                drug_id=int(request.form["drug_id"]),
                lot_number=request.form["lot_number"],
                quantity=float(request.form["quantity"]),
                reference=request.form.get("reference") or None,
            )
            flash("Stock received.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError) as exc:
            flash(str(exc), "error")
    drugs = g.db.query(Drug).order_by(Drug.name).all()
    return render_template("receive.html", drugs=drugs)


@bp.route("/dispense", methods=["GET", "POST"])
@login_required
def dispense():
    if request.method == "POST":
        try:
            inventory.dispense(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                quantity=float(request.form["quantity"]),
                reference=request.form.get("reference") or None,
            )
            flash("Dispensed.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError) as exc:
            flash(str(exc), "error")
    return render_template("dispense.html", rows=reports.inventory_snapshot(g.db))


@bp.route("/dispose", methods=["GET", "POST"])
@login_required
def dispose():
    if request.method == "POST":
        try:
            inventory.dispose(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                quantity=float(request.form["quantity"]),
                witness_user_id=int(request.form["witness_user_id"]),
                reason=request.form.get("reason", ""),
            )
            flash("Disposal recorded.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError) as exc:
            flash(str(exc), "error")
    witnesses = g.db.query(User).filter(User.id != g.user.id,
                                        User.active.is_(True)).all()
    return render_template("dispose.html",
                           rows=reports.inventory_snapshot(g.db),
                           witnesses=witnesses)


@bp.route("/reconcile", methods=["GET", "POST"])
@login_required
def reconcile():
    if request.method == "POST":
        try:
            inventory.reconcile(
                g.db, user_id=g.user.id,
                lot_id=int(request.form["lot_id"]),
                counted_qty=float(request.form["counted_qty"]),
                post_adjustment="post_adjustment" in request.form,
                reason=request.form.get("reason", ""),
            )
            flash("Count recorded.", "ok")
            return redirect(url_for("main.dashboard"))
        except (inventory.BusinessError, ValueError) as exc:
            flash(str(exc), "error")
    return render_template("reconcile.html",
                           rows=reports.inventory_snapshot(g.db))


@bp.route("/verify")
@login_required
def verify():
    ok, bad_id = ledger.verify_chain(g.db)
    return render_template("verify.html", ok=ok, bad_id=bad_id)
```

- [ ] **Step 4: Update `pharmacy/web/templates/base.html` nav**

Replace the `<nav>` block with:

```html
      <nav>
        <a href="{{ url_for('main.dashboard') }}">Inventory</a>
        <a href="{{ url_for('main.receive') }}">Receive</a>
        <a href="{{ url_for('main.dispense') }}">Dispense</a>
        <a href="{{ url_for('main.dispose') }}">Dispose</a>
        <a href="{{ url_for('main.reconcile') }}">Reconcile</a>
        <a href="{{ url_for('main.audit') }}">Audit log</a>
        <a href="{{ url_for('main.verify') }}">Verify</a>
        <a href="{{ url_for('main.new_drug') }}">Add drug</a>
        <a href="{{ url_for('main.logout') }}">Log out</a>
      </nav>
```

- [ ] **Step 5: Create `pharmacy/web/templates/new_drug.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Add drug</h1>
<form method="post">
  <label>Name <input name="name" required></label>
  <label>Strength <input name="strength"></label>
  <label>Form <input name="form"></label>
  <label>Code/NDC <input name="code"></label>
  <label>Schedule <input name="schedule" placeholder="CII"></label>
  <label>Unit <input name="unit" value="unit"></label>
  <button type="submit">Save</button>
</form>
{% endblock %}
```

- [ ] **Step 6: Create `pharmacy/web/templates/receive.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Receive stock</h1>
<form method="post">
  <label>Drug
    <select name="drug_id" required>
      {% for d in drugs %}<option value="{{ d.id }}">{{ d.name }} {{ d.strength }}</option>{% endfor %}
    </select>
  </label>
  <label>Lot number <input name="lot_number" required></label>
  <label>Quantity <input name="quantity" type="number" step="0.001" required></label>
  <label>Reference (PO) <input name="reference"></label>
  <button type="submit">Receive</button>
</form>
{% endblock %}
```

- [ ] **Step 7: Create `pharmacy/web/templates/dispense.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Dispense</h1>
<form method="post">
  <label>Lot
    <select name="lot_id" required>
      {% for r in rows %}<option value="{{ r.lot_id }}">{{ r.drug_name }} — lot {{ r.lot_number }} ({{ r.on_hand }} {{ r.unit }})</option>{% endfor %}
    </select>
  </label>
  <label>Quantity <input name="quantity" type="number" step="0.001" required></label>
  <label>Reference (RX) <input name="reference"></label>
  <button type="submit">Dispense</button>
</form>
{% endblock %}
```

- [ ] **Step 8: Create `pharmacy/web/templates/dispose.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Dispose / waste</h1>
<form method="post">
  <label>Lot
    <select name="lot_id" required>
      {% for r in rows %}<option value="{{ r.lot_id }}">{{ r.drug_name }} — lot {{ r.lot_number }} ({{ r.on_hand }} {{ r.unit }})</option>{% endfor %}
    </select>
  </label>
  <label>Quantity <input name="quantity" type="number" step="0.001" required></label>
  <label>Witness
    <select name="witness_user_id" required>
      {% for w in witnesses %}<option value="{{ w.id }}">{{ w.display_name }}</option>{% endfor %}
    </select>
  </label>
  <label>Reason <input name="reason" required></label>
  <button type="submit">Record disposal</button>
</form>
{% endblock %}
```

- [ ] **Step 9: Create `pharmacy/web/templates/reconcile.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Reconcile / count</h1>
<form method="post">
  <label>Lot
    <select name="lot_id" required>
      {% for r in rows %}<option value="{{ r.lot_id }}">{{ r.drug_name }} — lot {{ r.lot_number }} (expected {{ r.on_hand }} {{ r.unit }})</option>{% endfor %}
    </select>
  </label>
  <label>Counted quantity <input name="counted_qty" type="number" step="0.001" required></label>
  <label><input type="checkbox" name="post_adjustment"> Post adjustment to correct on-hand</label>
  <label>Reason (if adjusting) <input name="reason"></label>
  <button type="submit">Record count</button>
</form>
{% endblock %}
```

- [ ] **Step 10: Create `pharmacy/web/templates/verify.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Ledger integrity</h1>
{% if ok %}
  <p class="ok">The audit chain is <strong>intact</strong>. No tampering detected.</p>
{% else %}
  <p class="error">Integrity <strong>FAILED</strong> at entry #{{ bad_id }}.
     History may have been altered.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 11: Write `pharmacy/web/static/print.css`**

```css
body { font-family: system-ui, sans-serif; margin: 1.5rem; }
nav a { margin-right: 1rem; }
table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
th, td { border: 1px solid #999; padding: 4px 8px; text-align: left; }
label { display: block; margin: 0.5rem 0; }
.flash.error, .error { color: #b00; }
.flash.ok, .ok { color: #070; }

@media print {
  .no-print { display: none !important; }
  body { margin: 0; }
  a { color: inherit; text-decoration: none; }
}
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `pytest tests/test_web.py -v`
Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add pharmacy/web tests/test_web.py
git commit -m "feat: add receive/dispense/dispose/reconcile/verify routes, forms, and print styles"
```

---

## Task 15: Entry point and first-run admin bootstrap

**Files:**
- Create: `pharmacy/__main__.py`
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

`tests/test_bootstrap.py`:

```python
from pharmacy.db import init_db, make_session
from pharmacy.bootstrap import ensure_admin
from pharmacy.models import Role, User


def test_ensure_admin_creates_first_admin_only_once():
    session = make_session(init_db("sqlite://"))
    created = ensure_admin(session, username="admin", password="pw")
    assert created is True
    assert session.query(User).filter_by(role=Role.admin).count() == 1

    # Second call is a no-op because an admin already exists.
    created_again = ensure_admin(session, username="admin", password="pw")
    assert created_again is False
    assert session.query(User).filter_by(role=Role.admin).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bootstrap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pharmacy.bootstrap'`.

- [ ] **Step 3: Write `pharmacy/bootstrap.py`**

```python
"""First-run helpers."""

from pharmacy import auth
from pharmacy.models import Role, User


def ensure_admin(session, *, username, password):
    """Create an initial admin if no admin exists yet. Returns True if one
    was created, False if an admin already existed."""
    has_admin = session.query(User).filter_by(role=Role.admin).first()
    if has_admin is not None:
        return False
    auth.create_user(session, username=username, display_name="Administrator",
                     password=password, role=Role.admin)
    session.commit()
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_bootstrap.py -v`
Expected: PASS.

- [ ] **Step 5: Write `pharmacy/__main__.py`**

```python
"""Run the tracker: `python -m pharmacy`.

On first run, if no admin exists, one is created from PHARMACY_ADMIN_USER /
PHARMACY_ADMIN_PASSWORD (defaults admin/admin) and the credentials are printed
so staff can log in and change them.
"""

import os
import secrets

from pharmacy.bootstrap import ensure_admin
from pharmacy.db import init_db, make_session
from pharmacy.web import create_app


def main():
    db_url = os.environ.get("PHARMACY_DB", "sqlite:///pharmacy.db")
    engine = init_db(db_url)

    admin_user = os.environ.get("PHARMACY_ADMIN_USER", "admin")
    admin_pw = os.environ.get("PHARMACY_ADMIN_PASSWORD", "admin")
    session = make_session(engine)
    if ensure_admin(session, username=admin_user, password=admin_pw):
        print(f"[first run] Created admin '{admin_user}' with the configured "
              f"password. Log in and change it.")
    session.close()

    secret = os.environ.get("PHARMACY_SECRET_KEY", secrets.token_hex(16))
    app = create_app(engine, secret_key=secret)
    host = os.environ.get("PHARMACY_HOST", "127.0.0.1")
    port = int(os.environ.get("PHARMACY_PORT", "5000"))
    print(f"Pharmacy tracker running at http://{host}:{port}")
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS (all tests).

- [ ] **Step 7: Smoke-test the server starts** (manual)

Run: `python -m pharmacy` then open `http://127.0.0.1:5000`, log in as `admin`/`admin`, confirm the Inventory page loads. Stop with Ctrl+C.

- [ ] **Step 8: Commit**

```bash
git add pharmacy/bootstrap.py pharmacy/__main__.py tests/test_bootstrap.py
git commit -m "feat: add first-run admin bootstrap and python -m pharmacy entry point"
```

---

## Task 16: Printable report views and README usage

**Files:**
- Modify: `pharmacy/web/routes.py` (printable inventory + audit views)
- Create: `pharmacy/web/templates/print_inventory.html`, `print_audit.html`
- Modify: `pharmacy/web/templates/dashboard.html` (Print button)
- Modify: `README.md` (run/usage instructions)
- Test: `tests/test_web.py`

- [ ] **Step 1: Add the failing test**

Append to `tests/test_web.py`:

```python
def test_printable_inventory_renders(client):
    _login(client)
    resp = client.get("/print/inventory")
    assert resp.status_code == 200
    assert b"Inventory report" in resp.data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_web.py -k printable_inventory -v`
Expected: FAIL — 404 for `/print/inventory`.

- [ ] **Step 3: Add print routes to `pharmacy/web/routes.py`**

```python
@bp.route("/print/inventory")
@login_required
def print_inventory():
    return render_template("print_inventory.html",
                           rows=reports.inventory_snapshot(g.db))


@bp.route("/print/audit")
@login_required
def print_audit():
    return render_template("print_audit.html",
                           rows=reports.audit_log(g.db))
```

- [ ] **Step 4: Create `pharmacy/web/templates/print_inventory.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Inventory report</h1>
<button class="no-print" onclick="window.print()">Print</button>
<table>
  <thead><tr><th>Drug</th><th>Schedule</th><th>Lot</th><th>Expiry</th>
    <th>On hand</th><th>Unit</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr><td>{{ r.drug_name }} {{ r.strength }}</td><td>{{ r.schedule or '' }}</td>
      <td>{{ r.lot_number }}</td><td>{{ r.expiry_date or '' }}</td>
      <td>{{ r.on_hand }}</td><td>{{ r.unit }}</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: Create `pharmacy/web/templates/print_audit.html`**

```html
{% extends "base.html" %}
{% block content %}
<h1>Audit log report</h1>
<button class="no-print" onclick="window.print()">Print</button>
<table>
  <thead><tr><th>#</th><th>Time</th><th>Type</th><th>Drug</th><th>Lot</th>
    <th>Δ Qty</th><th>Operator</th><th>Witness</th><th>Reason</th><th>Ref</th></tr></thead>
  <tbody>
  {% for r in rows %}
    <tr><td>{{ r.id }}</td><td>{{ r.timestamp }}</td><td>{{ r.type }}</td>
      <td>{{ r.drug_name }}</td><td>{{ r.lot_number }}</td>
      <td>{{ r.quantity_delta }}</td><td>{{ r.operator }}</td>
      <td>{{ r.witness or '' }}</td><td>{{ r.reason or '' }}</td>
      <td>{{ r.reference or '' }}</td></tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 6: Add Print links to `dashboard.html`** (below the `<h1>`)

```html
<p class="no-print">
  <a href="{{ url_for('main.print_inventory') }}">Printable inventory</a> ·
  <a href="{{ url_for('main.print_audit') }}">Printable audit log</a>
</p>
```

- [ ] **Step 7: Update `README.md` "Getting Started" with run instructions**

Replace the `## Getting Started` section body with:

```markdown
## Getting Started

```
pip install -r requirements.txt
python -m pharmacy
```

Then open <http://127.0.0.1:5000>. On first run an admin account is created
(`admin` / `admin` by default — override with `PHARMACY_ADMIN_USER` /
`PHARMACY_ADMIN_PASSWORD`). Log in and add drugs, then record
receive / dispense / dispose / reconcile actions. Use **Verify** to check the
audit chain, and the **Printable** links to print inventory and audit reports.

Configuration via environment variables: `PHARMACY_DB` (default
`sqlite:///pharmacy.db`), `PHARMACY_HOST`, `PHARMACY_PORT`,
`PHARMACY_SECRET_KEY`.

Run the tests with `pytest`.
```

- [ ] **Step 8: Run the full suite**

Run: `pytest`
Expected: PASS (all tests).

- [ ] **Step 9: Commit**

```bash
git add pharmacy/web README.md tests/test_web.py
git commit -m "feat: add printable inventory/audit reports and usage docs"
```

---

## Self-Review

**Spec coverage:**
- Receive / dispense / dispose / reconcile → Tasks 7–10 (services) + Task 14 (web). ✓
- Printing → Tasks 14 (print.css) + 16 (printable views). ✓
- Append-only hash-chained ledger, on-hand derived → Tasks 3–5. ✓
- Tamper-evidence / verify integrity → Task 5 + `/verify` route in Task 14. ✓
- Multi-user auth, roles, attribution, witness → Tasks 11, 13, 9. ✓
- First-run admin → Task 15. ✓
- Local desktop run → Task 15 `__main__`. ✓
- Data model (User/Drug/Lot/LedgerEntry/Count) → Task 2. ✓
- Tests heaviest on ledger + inventory → Tasks 3–10. ✓
- CI → Task 1. ✓

**Placeholder scan:** No "TBD"/"TODO"/"add error handling" steps; the empty `print.css` and minimal `dashboard.html` in Task 13 are explicitly filled in Task 14. ✓

**Type/name consistency:** `norm_qty`, `canonical`, `compute_hash`, `append_entry`, `on_hand`, `verify_chain`, `BusinessError`, `AuthError`, `create_app(engine, secret_key=...)`, `ensure_admin` used consistently across tasks and tests. Service signatures match their web callers. ✓
