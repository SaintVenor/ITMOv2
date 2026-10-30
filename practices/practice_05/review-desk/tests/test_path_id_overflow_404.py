"""Известная проблема B: переполнение SQLite INTEGER в числовых id пути.

Спека: openspec/changes/path-id-overflow-404/specs/path-id-bounds/spec.md.
Покрывает требования «Переполняющий id задачи при просмотре задачи»,
«Переполняющий id задачи при отправке решения», «Переполняющий id сдачи
при просмотре сдачи», «Переполняющий id сдачи при ревью» (сценарии на
границе 2^63-1 и 2^63, сверхдлинное число, симметричная нижняя граница),
а также baseline-кейсы, которые capability не должна менять: нечисловой
id (`handle_bad_path`) и существующий id (счастливый путь).
"""

import pytest
from sqlalchemy.orm import Session

from app.models import Assignment, Submission

SQLITE_INT_MAX = 2**63 - 1
SQLITE_INT_MIN = -(2**63)

# В диапазоне SQLite INTEGER, но такой строки нет — обычный 404, не связанный с переполнением.
IN_RANGE_MISSING_ID = SQLITE_INT_MAX

# Вне диапазона — сегодня даёт 500 (OverflowError в SQLite), должно стать 404.
OVERFLOW_IDS = [
    pytest.param(SQLITE_INT_MAX + 1, id="2^63"),
    pytest.param(SQLITE_INT_MIN - 1, id="-2^63-1"),
    pytest.param(99999999999999999999, id="huge-positive"),
]


@pytest.fixture
def tracked_gets(monkeypatch):
    """Список вызовов Session.get(Assignment|Submission, ...) за время теста.

    Вызовы Session.get(User, ...) из auth.get_user (зависимость current_user,
    срабатывает на каждый запрос из-за сессии) не считаются.
    """
    calls = []
    original_get = Session.get

    def spy_get(self, entity, ident, *args, **kwargs):
        if entity in (Assignment, Submission):
            calls.append((entity, ident))
        return original_get(self, entity, ident, *args, **kwargs)

    monkeypatch.setattr(Session, "get", spy_get)
    return calls


def submit(client, assignment_id, code="print(1)"):
    return client.post(
        f"/assignments/{assignment_id}/submissions", data={"code": code}, follow_redirects=False
    )


def review(client, submission_id, verdict="accepted", comment="Отлично"):
    return client.post(
        f"/submissions/{submission_id}/review",
        data={"verdict": verdict, "comment": comment},
        follow_redirects=False,
    )


# ---- GET /assignments/{assignment_id} ----


def test_get_assignment_in_range_missing_is_404(mentor_client):
    resp = mentor_client.get(f"/assignments/{IN_RANGE_MISSING_ID}")
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", OVERFLOW_IDS)
def test_get_assignment_overflow_id_is_404_not_500(mentor_client, tracked_gets, bad_id):
    resp = mentor_client.get(f"/assignments/{bad_id}")
    assert resp.status_code == 404
    assert tracked_gets == []  # до SQLite не дошло

    baseline = mentor_client.get(f"/assignments/{IN_RANGE_MISSING_ID}")
    assert resp.text == baseline.text  # тот же рендер, что для обычного отсутствующего id


def test_get_assignment_non_numeric_id_is_404(mentor_client):
    resp = mentor_client.get("/assignments/abc")
    assert resp.status_code == 404


def test_get_assignment_existing_id_is_200(mentor_client, assignment):
    resp = mentor_client.get(f"/assignments/{assignment.id}")
    assert resp.status_code == 200


# ---- POST /assignments/{assignment_id}/submissions ----


def test_create_submission_in_range_missing_is_404(student_client):
    resp = submit(student_client, IN_RANGE_MISSING_ID)
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", OVERFLOW_IDS)
def test_create_submission_overflow_id_is_404_not_500(student_client, tracked_gets, bad_id):
    resp = submit(student_client, bad_id)
    assert resp.status_code == 404
    assert tracked_gets == []

    baseline = submit(student_client, IN_RANGE_MISSING_ID)
    assert resp.text == baseline.text


def test_create_submission_non_numeric_id_is_404(student_client):
    resp = submit(student_client, "abc")
    assert resp.status_code == 404


def test_create_submission_existing_id_is_303(student_client, assignment):
    resp = submit(student_client, assignment.id)
    assert resp.status_code == 303


# ---- GET /submissions/{submission_id} ----


def test_get_submission_in_range_missing_is_404(mentor_client):
    resp = mentor_client.get(f"/submissions/{IN_RANGE_MISSING_ID}")
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", OVERFLOW_IDS)
def test_get_submission_overflow_id_is_404_not_500(mentor_client, tracked_gets, bad_id):
    resp = mentor_client.get(f"/submissions/{bad_id}")
    assert resp.status_code == 404
    assert tracked_gets == []

    baseline = mentor_client.get(f"/submissions/{IN_RANGE_MISSING_ID}")
    assert resp.text == baseline.text


def test_get_submission_non_numeric_id_is_404(mentor_client):
    resp = mentor_client.get("/submissions/abc")
    assert resp.status_code == 404


def test_get_submission_existing_id_is_200(mentor_client, assignment, student, make_submission):
    submission = make_submission(assignment, student)
    resp = mentor_client.get(f"/submissions/{submission.id}")
    assert resp.status_code == 200


# ---- POST /submissions/{submission_id}/review ----


def test_create_review_in_range_missing_is_404(mentor_client):
    resp = review(mentor_client, IN_RANGE_MISSING_ID)
    assert resp.status_code == 404


@pytest.mark.parametrize("bad_id", OVERFLOW_IDS)
def test_create_review_overflow_id_is_404_not_500(mentor_client, tracked_gets, bad_id):
    resp = review(mentor_client, bad_id)
    assert resp.status_code == 404
    assert tracked_gets == []

    baseline = review(mentor_client, IN_RANGE_MISSING_ID)
    assert resp.text == baseline.text


def test_create_review_non_numeric_id_is_404(mentor_client):
    resp = review(mentor_client, "abc")
    assert resp.status_code == 404


def test_create_review_existing_id_is_303(mentor_client, assignment, student, make_submission):
    submission = make_submission(assignment, student)
    resp = review(mentor_client, submission.id)
    assert resp.status_code == 303
