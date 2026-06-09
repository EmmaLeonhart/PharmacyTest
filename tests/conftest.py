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
