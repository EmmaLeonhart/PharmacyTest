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
