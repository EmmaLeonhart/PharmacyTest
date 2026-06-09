from pharmacy.db import init_db, make_session
from pharmacy.bootstrap import ensure_admin, load_or_create_secret_key
from pharmacy.models import Role, User


def test_ensure_admin_creates_first_admin_only_once():
    session = make_session(init_db("sqlite://"))
    created = ensure_admin(session, username="admin", password="pw")
    assert created is True
    assert session.query(User).filter_by(role=Role.admin).count() == 1

    created_again = ensure_admin(session, username="admin", password="pw")
    assert created_again is False
    assert session.query(User).filter_by(role=Role.admin).count() == 1


def test_secret_key_is_persisted_and_stable(tmp_path):
    key_file = tmp_path / "secret.key"
    first = load_or_create_secret_key(str(key_file))
    assert key_file.exists()
    assert first  # non-empty
    # A second call reads the same persisted key rather than regenerating.
    second = load_or_create_secret_key(str(key_file))
    assert second == first


def test_secret_key_creates_parent_dirs(tmp_path):
    key_file = tmp_path / "nested" / "dir" / "secret.key"
    key = load_or_create_secret_key(str(key_file))
    assert key_file.exists()
    assert key
