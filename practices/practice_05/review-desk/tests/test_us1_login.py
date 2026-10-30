import pytest
from sqlalchemy import select

from app.models import User
from app.services import auth
from tests.conftest import PASSWORD, login

GENERIC_ERROR = "Неверный логин или пароль"


def test_us1_ac1_valid_credentials_create_session_and_redirect(client, student):
    resp = login(client, "alice")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/assignments"

    page = client.get("/assignments", follow_redirects=False)
    assert page.status_code == 200
    assert "Алиса" in page.text


def test_us1_ac1_mentor_also_lands_on_assignments(client, mentor):
    resp = login(client, "mentor")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/assignments"


def test_us1_ac1_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert 'name="username"' in resp.text
    assert 'name="password"' in resp.text


@pytest.mark.parametrize(
    "username,password",
    [("alice", "wrong-password"), ("nobody", PASSWORD), ("nobody", "wrong"), ("", "")],
)
def test_us1_ac2_wrong_credentials_show_single_generic_error(client, student, username, password):
    resp = client.post(
        "/login", data={"username": username, "password": password}, follow_redirects=False
    )
    assert resp.status_code == 200
    assert resp.text.count(GENERIC_ERROR) == 1
    assert "пароль неверен" not in resp.text.lower()
    assert "не найден" not in resp.text.lower()
    assert client.get("/assignments", follow_redirects=False).status_code == 303


def test_us1_ac2_error_is_identical_for_bad_user_and_bad_password(client, student):
    bad_user = client.post("/login", data={"username": "nobody", "password": PASSWORD})
    bad_pass = client.post("/login", data={"username": "alice", "password": "nope"})
    assert bad_user.text.replace("nobody", "") == bad_pass.text.replace("alice", "")


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/"),
        ("get", "/assignments"),
        ("get", "/assignments/new"),
        ("get", "/assignments/1"),
        ("post", "/assignments/1/submissions"),
        ("get", "/submissions/1"),
        ("post", "/submissions/1/review"),
        ("get", "/review"),
        ("post", "/logout"),
        ("get", "/does-not-exist"),
    ],
)
def test_us1_ac3_any_page_without_session_redirects_to_login(client, method, path):
    resp = getattr(client, method)(path, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_us1_ac3_login_page_itself_is_not_redirected(client):
    assert client.get("/login", follow_redirects=False).status_code == 200


def test_us1_ac4_logout_ends_session(student_client):
    assert student_client.get("/assignments", follow_redirects=False).status_code == 200

    resp = student_client.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    after = student_client.get("/assignments", follow_redirects=False)
    assert after.status_code == 303
    assert after.headers["location"] == "/login"


def test_us1_ac5_password_stored_only_as_bcrypt_hash(db_session, student):
    stored = db_session.scalar(select(User).where(User.username == "alice"))
    assert PASSWORD not in stored.password_hash
    assert stored.password_hash.startswith("$2")
    assert auth.verify_password(PASSWORD, stored.password_hash)
    assert not auth.verify_password("other", stored.password_hash)
    columns = {c.name for c in User.__table__.columns}
    assert "password" not in columns
