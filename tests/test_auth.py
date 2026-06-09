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
