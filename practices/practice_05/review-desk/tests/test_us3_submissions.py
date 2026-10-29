import re

import pytest
from sqlalchemy import func, select

from app.models import Assignment, Submission


def submissions(db, **filters):
    return list(db.scalars(select(Submission).filter_by(**filters).order_by(Submission.id)))


def count_submissions(db):
    return db.scalar(select(func.count()).select_from(Submission))


def submit(client, assignment_id, code="int main() { return 0; }"):
    return client.post(
        f"/assignments/{assignment_id}/submissions", data={"code": code}, follow_redirects=False
    )


def test_us3_student_sees_assignment_list_and_opens_assignment(student_client, assignment):
    listing = student_client.get("/assignments")
    assert listing.status_code == 200
    assert f'href="/assignments/{assignment.id}"' in listing.text
    assert assignment.title in listing.text

    page = student_client.get(f"/assignments/{assignment.id}")
    assert page.status_code == 200
    assert assignment.description in page.text
    assert 'name="code"' in page.text


def test_us3_ac1_valid_code_creates_pending_submission(student_client, db_session, assignment, student):
    code = "  #include <iostream>\nint main() {}\n  "
    resp = submit(student_client, assignment.id, code)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/assignments/{assignment.id}"
    [s] = submissions(db_session)
    assert s.student_id == student.id
    assert s.assignment_id == assignment.id
    assert s.status == "pending"
    assert s.code == code.strip()


def test_us3_ac1_code_of_max_length_is_accepted(student_client, db_session, assignment):
    assert submit(student_client, assignment.id, "x" * 100_000).status_code == 303
    assert count_submissions(db_session) == 1


@pytest.mark.parametrize("code", ["", "   \n\t  ", "x" * 100_001])
def test_us3_ac1_invalid_code_is_rejected(student_client, db_session, assignment, code):
    resp = submit(student_client, assignment.id, code)
    assert resp.status_code == 400
    assert re.search(r'<p class="field-error" data-field="code">.+?</p>', resp.text, re.S)
    assert count_submissions(db_session) == 0


def test_us3_ac1_missing_code_field_is_rejected(student_client, db_session, assignment):
    resp = student_client.post(f"/assignments/{assignment.id}/submissions", data={})
    assert resp.status_code == 400
    assert count_submissions(db_session) == 0


def test_us3_ac2_attempts_numbered_per_assignment_and_student(
    db_session, make_client, mentor, student, other_student, assignment
):
    second = Assignment(title="Вторая", description="d", author_id=mentor.id)
    db_session.add(second)
    db_session.commit()

    alice, bob = make_client(student), make_client(other_student)

    assert submit(alice, assignment.id).status_code == 303
    assert submit(bob, assignment.id).status_code == 303
    assert submit(alice, second.id).status_code == 303

    # Ментор вернул первую попытку Алисы на доработку — она сдаёт снова.
    first = submissions(db_session, assignment_id=assignment.id, student_id=student.id)[0]
    first.status = "changes_requested"
    db_session.commit()
    assert submit(alice, assignment.id).status_code == 303

    def attempts(a, s):
        return [x.attempt for x in submissions(db_session, assignment_id=a.id, student_id=s.id)]

    assert attempts(assignment, student) == [1, 2]
    assert attempts(assignment, other_student) == [1]
    assert attempts(second, student) == [1]
    assert submissions(db_session, assignment_id=assignment.id, student_id=student.id)[1].status == "pending"


@pytest.mark.parametrize(
    "previous_status,message",
    [("pending", "ждёт ревью"), ("accepted", "уже принята")],
)
def test_us3_ac3_new_submission_blocked_while_pending_or_after_accepted(
    student_client, db_session, assignment, student, make_submission, previous_status, message
):
    make_submission(assignment, student, status=previous_status)

    resp = submit(student_client, assignment.id)

    assert resp.status_code == 409
    assert message in resp.text
    assert count_submissions(db_session) == 1


def test_us3_ac3_accepted_blocks_even_after_earlier_changes_requested(
    student_client, db_session, assignment, student, make_submission
):
    make_submission(assignment, student, status="changes_requested")
    make_submission(assignment, student, status="accepted")
    assert submit(student_client, assignment.id).status_code == 409
    assert count_submissions(db_session) == 2


def test_us3_ac3_blocked_assignment_page_hides_form_and_explains(
    student_client, assignment, student, make_submission
):
    make_submission(assignment, student, status="pending")
    page = student_client.get(f"/assignments/{assignment.id}")
    assert 'name="code"' not in page.text
    assert "ждёт ревью" in page.text


def test_us3_ac3_other_students_pending_does_not_block(
    student_client, db_session, assignment, other_student, make_submission
):
    make_submission(assignment, other_student, status="pending")
    assert submit(student_client, assignment.id).status_code == 303


def test_us3_ac4_submission_to_missing_assignment_is_404(student_client, db_session):
    assert submit(student_client, 9999).status_code == 404
    assert count_submissions(db_session) == 0


def test_us3_ac5_mentor_cannot_submit(mentor_client, db_session, assignment):
    assert submit(mentor_client, assignment.id).status_code == 403
    assert count_submissions(db_session) == 0


def test_us3_ac5_mentor_sees_no_submit_form(mentor_client, assignment):
    page = mentor_client.get(f"/assignments/{assignment.id}")
    assert page.status_code == 200
    assert 'name="code"' not in page.text


def test_us3_ac1_browser_crlf_line_endings_are_normalized(student_client, db_session, assignment):
    assert submit(student_client, assignment.id, "int a;\r\nint b;\r\n").status_code == 303
    [s] = submissions(db_session)
    assert s.code == "int a;\nint b;"
