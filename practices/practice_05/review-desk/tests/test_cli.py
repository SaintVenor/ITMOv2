from sqlalchemy import select

from app import cli
from app.models import User


def test_cli_create_user_asks_password_via_getpass(monkeypatch, db_session, capsys):
    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "pw-123")

    code = cli.main(["create-user", "--username", "mentor", "--role", "mentor"])

    assert code == 0
    user = db_session.scalar(select(User).where(User.username == "mentor"))
    assert user.role == "mentor"
    assert user.display_name == "mentor"
    assert user.password_hash != "pw-123"


def test_cli_create_user_rejects_mismatched_passwords(monkeypatch, db_session):
    answers = iter(["one", "two"])
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))

    assert cli.main(["create-user", "--username", "x", "--role", "student"]) == 1
    assert db_session.scalar(select(User)) is None
