"""First-run helpers."""

import os
import secrets

from pharmacy import auth
from pharmacy.models import Role, User


def load_or_create_secret_key(path):
    """Return the secret key stored at `path`, creating and persisting a new
    one if the file does not yet exist. Persisting the key keeps Flask sessions
    valid across restarts (a freshly random key every start would log everyone
    out on each restart)."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read().strip()
        if existing:
            return existing
    key = secrets.token_hex(32)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(key)
    return key


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
