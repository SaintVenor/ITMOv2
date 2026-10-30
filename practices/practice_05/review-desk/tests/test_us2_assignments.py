import re

import pytest
from sqlalchemy import func, select

from app.models import Assignment


def count_assignments(db):
    return db.scalar(select(func.count()).select_from(Assignment))


def field_error(html, field):
    m = re.search(rf'<p class="field-error" data-field="{field}">(.*?)</p>', html, re.S)
    return m.group(1).strip() if m else None


def test_us2_ac1_mentor_sees_form(mentor_client):
    resp = mentor_client.get("/assignments/new")
    assert resp.status_code == 200
    assert 'name="title"' in resp.text
    assert 'name="description"' in resp.text


def test_us2_ac1_valid_assignment_is_created_with_stripped_fields(mentor_client, db_session, mentor):
    resp = mentor_client.post(
        "/assignments/new",
        data={"title": "  Сумма двух чисел  ", "description": "\n Прочитайте a и b.\n  "},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    a = db_session.scalar(select(Assignment))
    assert resp.headers["location"] == f"/assignments/{a.id}"
    assert a.title == "Сумма двух чисел"
    assert a.description == "Прочитайте a и b."
    assert a.author_id == mentor.id

    page = mentor_client.get(f"/assignments/{a.id}")
    assert page.status_code == 200
    assert "Сумма двух чисел" in page.text
    assert "Прочитайте a и b." in page.text


@pytest.mark.parametrize(
    "title,description",
    [("x" * 1, "d"), ("x" * 200, "d"), ("t", "d" * 1), ("t", "d" * 10_000), ("  " + "x" * 200 + "  ", "d")],
)
def test_us2_ac1_boundary_lengths_are_accepted(mentor_client, db_session, title, description):
    resp = mentor_client.post(
        "/assignments/new", data={"title": title, "description": description}, follow_redirects=False
    )
    assert resp.status_code == 303
    assert count_assignments(db_session) == 1


@pytest.mark.parametrize(
    "title,description,bad_field",
    [
        ("", "d", "title"),
        ("   \n\t ", "d", "title"),
        ("x" * 201, "d", "title"),
        ("t", "", "description"),
        ("t", "   \n  ", "description"),
        ("t", "d" * 10_001, "description"),
    ],
)
def test_us2_ac2_invalid_field_rerenders_form_with_error_and_creates_nothing(
    mentor_client, db_session, title, description, bad_field
):
    resp = mentor_client.post(
        "/assignments/new", data={"title": title, "description": description}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert 'name="title"' in resp.text
    assert field_error(resp.text, bad_field)
    other = "description" if bad_field == "title" else "title"
    assert field_error(resp.text, other) is None
    assert count_assignments(db_session) == 0


def test_us2_ac2_both_fields_invalid_show_both_errors(mentor_client, db_session):
    resp = mentor_client.post("/assignments/new", data={"title": " ", "description": " "})
    assert resp.status_code == 400
    assert field_error(resp.text, "title")
    assert field_error(resp.text, "description")
    assert count_assignments(db_session) == 0


def test_us2_ac2_form_keeps_entered_values(mentor_client):
    resp = mentor_client.post("/assignments/new", data={"title": "", "description": "Моё описание"})
    assert "Моё описание" in resp.text


def test_us2_ac2_missing_fields_are_validation_errors(mentor_client, db_session):
    resp = mentor_client.post("/assignments/new", data={})
    assert resp.status_code == 400
    assert field_error(resp.text, "title")
    assert count_assignments(db_session) == 0


def test_us2_ac3_student_cannot_open_form(student_client):
    assert student_client.get("/assignments/new").status_code == 403


def test_us2_ac3_student_cannot_submit_form(student_client, db_session):
    resp = student_client.post("/assignments/new", data={"title": "t", "description": "d"})
    assert resp.status_code == 403
    assert count_assignments(db_session) == 0
