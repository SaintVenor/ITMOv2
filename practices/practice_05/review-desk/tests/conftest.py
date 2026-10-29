import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db, init_db
from app.main import create_app
from app.models import Assignment, Submission
from app.services import auth

PASSWORD = "s3cret-pass"

_real_gensalt = bcrypt.gensalt


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    """Минимальный cost bcrypt в тестах: тот же алгоритм, но быстро."""
    monkeypatch.setattr(bcrypt, "gensalt", lambda rounds=4, prefix=b"2b": _real_gensalt(4, prefix))


@pytest.fixture
def db_session():
    """Отдельная SQLite в памяти на каждый тест."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    init_db(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def app(db_session):
    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mentor(db_session):
    return auth.create_user(db_session, "mentor", PASSWORD, "mentor", "Ментор")


@pytest.fixture
def student(db_session):
    return auth.create_user(db_session, "alice", PASSWORD, "student", "Алиса")


@pytest.fixture
def other_student(db_session):
    return auth.create_user(db_session, "bob", PASSWORD, "student", "Боб")


def login(client, username, password=PASSWORD):
    return client.post(
        "/login", data={"username": username, "password": password}, follow_redirects=False
    )


@pytest.fixture
def make_client(app):
    """Отдельный клиент со своей сессией для каждого пользователя."""
    clients = []

    def _make(user=None):
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        if user is not None:
            resp = login(c, user.username)
            assert resp.status_code == 303, resp.text
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def mentor_client(make_client, mentor):
    return make_client(mentor)


@pytest.fixture
def student_client(make_client, student):
    return make_client(student)


@pytest.fixture
def assignment(db_session, mentor):
    a = Assignment(title="Сумма двух чисел", description="Прочитайте a и b.", author_id=mentor.id)
    db_session.add(a)
    db_session.commit()
    return a


@pytest.fixture
def make_submission(db_session):
    def _make(assignment, student, status="pending", code="int main() {}"):
        attempt = (
            db_session.query(Submission)
            .filter_by(assignment_id=assignment.id, student_id=student.id)
            .count()
            + 1
        )
        s = Submission(
            assignment_id=assignment.id,
            student_id=student.id,
            attempt=attempt,
            code=code,
            status=status,
        )
        db_session.add(s)
        db_session.commit()
        return s

    return _make
