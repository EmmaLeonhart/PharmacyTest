from pharmacy.db import init_db, make_session
from pharmacy.bootstrap import ensure_admin
from pharmacy.models import Role, User


def test_ensure_admin_creates_first_admin_only_once():
    session = make_session(init_db("sqlite://"))
    created = ensure_admin(session, username="admin", password="pw")
    assert created is True
    assert session.query(User).filter_by(role=Role.admin).count() == 1

    created_again = ensure_admin(session, username="admin", password="pw")
    assert created_again is False
    assert session.query(User).filter_by(role=Role.admin).count() == 1
