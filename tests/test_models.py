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
