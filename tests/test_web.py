import pytest

from pharmacy import auth
from pharmacy.db import init_db, make_session
from pharmacy.models import Drug, Role
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
