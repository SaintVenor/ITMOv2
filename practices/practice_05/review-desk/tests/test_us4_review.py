import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.models import Review


def count_reviews(db):
    return db.scalar(select(func.count()).select_from(Review))


def post_review(client, submission_id, verdict="accepted", comment="Отлично"):
    return client.post(
        f"/submissions/{submission_id}/review",
        data={"verdict": verdict, "comment": comment},
        follow_redirects=False,
    )


def test_us4_ac1_queue_shows_only_pending_oldest_first(
    mentor_client, db_session, assignment, student, other_student, make_submission
):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = make_submission(assignment, student, status="pending")
    older = make_submission(assignment, other_student, status="pending")
    done = make_submission(assignment, student, status="accepted")
    returned = make_submission(assignment, other_student, status="changes_requested")
    newer.created_at = base + timedelta(hours=2)
    older.created_at = base + timedelta(hours=1)
    done.created_at = base
    returned.created_at = base
    db_session.commit()

    resp = mentor_client.get("/review")
    assert resp.status_code == 200
    ids = [int(x) for x in re.findall(r'href="/submissions/(\d+)"', resp.text)]
    assert ids == [older.id, newer.id]


def test_us4_ac1_empty_queue(mentor_client):
    resp = mentor_client.get("/review")
    assert resp.status_code == 200
    assert "/submissions/" not in resp.text


def test_us4_mentor_opens_submission_and_sees_review_form(
    mentor_client, assignment, student, make_submission
):
    s = make_submission(assignment, student, code="int main() { return 42; }")
    resp = mentor_client.get(f"/submissions/{s.id}")
    assert resp.status_code == 200
    assert "return 42;" in resp.text
    assert 'name="verdict"' in resp.text
    assert 'name="comment"' in resp.text


@pytest.mark.parametrize("verdict", ["accepted", "changes_requested"])
def test_us4_ac2_review_saves_verdict_comment_and_updates_status(
    mentor_client, db_session, assignment, student, mentor, make_submission, verdict
):
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, verdict, "  Посмотри на граничные случаи.  ")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/review"

    db_session.refresh(s)
    assert s.status == verdict
    review = db_session.scalar(select(Review))
    assert review.submission_id == s.id
    assert review.mentor_id == mentor.id
    assert review.verdict == verdict
    assert review.comment == "Посмотри на граничные случаи."

    page = mentor_client.get(f"/submissions/{s.id}")
    assert "Посмотри на граничные случаи." in page.text
    assert 'name="verdict"' not in page.text
    assert "/submissions/" not in mentor_client.get("/review").text


@pytest.mark.parametrize("comment", ["x", "x" * 5000, "  " + "x" * 5000 + "\n"])
def test_us4_ac2_comment_boundaries_accepted(mentor_client, db_session, assignment, student, make_submission, comment):
    s = make_submission(assignment, student)
    assert post_review(mentor_client, s.id, "accepted", comment).status_code == 303
    assert count_reviews(db_session) == 1


@pytest.mark.parametrize(
    "verdict,comment,bad_field",
    [
        ("approved", "ok", "verdict"),
        ("pending", "ok", "verdict"),
        ("", "ok", "verdict"),
        ("accepted", "", "comment"),
        ("accepted", "  \n ", "comment"),
        ("accepted", "x" * 5001, "comment"),
    ],
)
def test_us4_ac2_invalid_review_rejected(
    mentor_client, db_session, assignment, student, make_submission, verdict, comment, bad_field
):
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, verdict, comment)
    assert resp.status_code == 400
    assert re.search(rf'<p class="field-error" data-field="{bad_field}">.+?</p>', resp.text, re.S)
    assert count_reviews(db_session) == 0
    db_session.refresh(s)
    assert s.status == "pending"


def test_us4_ac3_second_review_is_409(mentor_client, db_session, assignment, student, make_submission):
    s = make_submission(assignment, student)
    assert post_review(mentor_client, s.id, "changes_requested", "Доработай").status_code == 303

    resp = post_review(mentor_client, s.id, "accepted", "Передумал")
    assert resp.status_code == 409
    assert count_reviews(db_session) == 1
    db_session.refresh(s)
    assert s.status == "changes_requested"
    assert s.review.comment == "Доработай"


def test_us4_ac3_second_review_is_409_even_with_invalid_data(
    mentor_client, db_session, assignment, student, make_submission
):
    s = make_submission(assignment, student)
    post_review(mentor_client, s.id)
    assert post_review(mentor_client, s.id, "bogus", "").status_code == 409


def test_us4_review_of_missing_submission_is_404(mentor_client):
    assert post_review(mentor_client, 9999).status_code == 404
    assert mentor_client.get("/submissions/9999").status_code == 404


def test_us4_ac4_student_cannot_review_even_own_submission(
    student_client, db_session, assignment, student, make_submission
):
    s = make_submission(assignment, student)
    assert post_review(student_client, s.id).status_code == 403
    assert count_reviews(db_session) == 0
    db_session.refresh(s)
    assert s.status == "pending"


def test_us4_ac4_student_has_no_review_queue_or_form(student_client, assignment, student, make_submission):
    s = make_submission(assignment, student)
    assert student_client.get("/review").status_code == 403
    assert 'name="verdict"' not in student_client.get(f"/submissions/{s.id}").text
