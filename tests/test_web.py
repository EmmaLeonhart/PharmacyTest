import pytest

from pharmacy import auth
from pharmacy.db import init_db, make_session
from pharmacy.models import Role
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
