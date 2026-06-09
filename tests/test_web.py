import pytest

from pharmacy import auth
from pharmacy.db import init_db, make_session
from pharmacy.models import Drug, Role, User
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


def _login(client):
    client.post("/login", data={"username": "admin", "password": "pw"})


def test_receive_then_dispense_via_web(client, app):
    _login(client)
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


def test_printable_inventory_renders(client):
    _login(client)
    resp = client.get("/print/inventory")
    assert resp.status_code == 200
    assert b"Inventory report" in resp.data


def test_malformed_post_flashes_instead_of_500(client):
    _login(client)
    # POST to /receive missing every required field -> should flash, not 500.
    resp = client.post("/receive", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Missing required field" in resp.data


def _add_operator(app, username="op", password="oppw"):
    """Create an operator against the app's engine."""
    session = make_session(app.config["ENGINE"])
    auth.create_user(session, username=username, display_name="Operator",
                     password=password, role=Role.operator)
    session.commit()


def _login_as(client, username, password):
    client.post("/login", data={"username": username, "password": password})


def test_operator_cannot_add_drug(client, app):
    _add_operator(app)
    _login_as(client, "op", "oppw")
    resp = client.post("/drugs/new", data={"name": "Morphine", "unit": "vial"})
    assert resp.status_code == 403
    # The drug must not have been created.
    session = make_session(app.config["ENGINE"])
    assert session.query(Drug).count() == 0


def test_admin_can_add_drug(client, app):
    _login(client)  # admin
    resp = client.post("/drugs/new",
                       data={"name": "Morphine", "unit": "vial"},
                       follow_redirects=True)
    assert resp.status_code == 200
    session = make_session(app.config["ENGINE"])
    assert session.query(Drug).filter_by(name="Morphine").count() == 1


def _user_id(app, username):
    session = make_session(app.config["ENGINE"])
    return session.query(User).filter_by(username=username).one().id


def test_admin_can_create_operator_who_can_log_in(client, app):
    _login(client)  # admin
    resp = client.post("/users/new",
                       data={"username": "nurse", "display_name": "Nurse",
                             "password": "np", "role": "operator"},
                       follow_redirects=True)
    assert resp.status_code == 200
    # The new operator can authenticate.
    fresh = app.test_client()
    login = fresh.post("/login", data={"username": "nurse", "password": "np"},
                       follow_redirects=True)
    assert login.status_code == 200
    assert b"Inventory" in login.data


def test_operator_cannot_reach_users(client, app):
    _add_operator(app)
    _login_as(client, "op", "oppw")
    resp = client.get("/users")
    assert resp.status_code == 403


def test_cannot_deactivate_last_active_admin(client, app):
    _login(client)  # admin (the only one)
    admin_id = _user_id(app, "admin")
    resp = client.post(f"/users/{admin_id}/deactivate", follow_redirects=True)
    assert resp.status_code == 200
    assert b"last active admin" in resp.data.lower()
    # Admin remains active.
    session = make_session(app.config["ENGINE"])
    assert session.query(User).filter_by(username="admin").one().active is True


def test_admin_can_deactivate_operator(client, app):
    _add_operator(app)
    _login(client)  # admin
    op_id = _user_id(app, "op")
    client.post(f"/users/{op_id}/deactivate", follow_redirects=True)
    session = make_session(app.config["ENGINE"])
    assert session.query(User).filter_by(username="op").one().active is False


def test_admin_can_reset_operator_password(client, app):
    _add_operator(app)
    _login(client)  # admin
    op_id = _user_id(app, "op")
    client.post(f"/users/{op_id}/reset-password",
                data={"password": "brand-new"}, follow_redirects=True)
    fresh = app.test_client()
    old = fresh.post("/login", data={"username": "op", "password": "oppw"},
                     follow_redirects=True)
    assert b"Invalid" in old.data
    new = fresh.post("/login", data={"username": "op", "password": "brand-new"},
                     follow_redirects=True)
    assert b"Inventory" in new.data


def test_operator_does_not_see_users_nav_link(client, app):
    _add_operator(app)
    _login_as(client, "op", "oppw")
    resp = client.get("/")
    assert b'href="/users"' not in resp.data


def test_user_can_change_own_password(client, app):
    _add_operator(app)
    _login_as(client, "op", "oppw")
    resp = client.post("/account/password",
                       data={"current_password": "oppw",
                             "new_password": "changed-pw"},
                       follow_redirects=True)
    assert resp.status_code == 200
    fresh = app.test_client()
    old = fresh.post("/login", data={"username": "op", "password": "oppw"},
                     follow_redirects=True)
    assert b"Invalid" in old.data
    new = fresh.post("/login", data={"username": "op", "password": "changed-pw"},
                     follow_redirects=True)
    assert b"Inventory" in new.data


def test_password_change_refused_with_wrong_current(client, app):
    _add_operator(app)
    _login_as(client, "op", "oppw")
    resp = client.post("/account/password",
                       data={"current_password": "WRONG",
                             "new_password": "changed-pw"},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"current password is incorrect" in resp.data.lower()
    # Password unchanged: original still works, attempted new one does not.
    fresh = app.test_client()
    assert b"Inventory" in fresh.post(
        "/login", data={"username": "op", "password": "oppw"},
        follow_redirects=True).data
    fresh2 = app.test_client()
    assert b"Invalid" in fresh2.post(
        "/login", data={"username": "op", "password": "changed-pw"},
        follow_redirects=True).data


def test_password_change_requires_login(client):
    resp = client.get("/account/password", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_alerts_page_renders(client, app):
    _login(client)
    # A low-stock lot should surface on the alerts page.
    client.post("/drugs/new", data={"name": "Codeine", "unit": "tablet"})
    client.post("/receive", data={"drug_id": "1", "lot_number": "LO",
                                  "quantity": "1"})
    resp = client.get("/alerts?threshold=5")
    assert resp.status_code == 200
    assert b"Alerts" in resp.data
    assert b"low_stock" in resp.data
