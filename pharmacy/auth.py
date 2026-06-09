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
