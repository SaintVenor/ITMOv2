import re

from app.models import Review

XSS = '<script>alert("x")</script>'
XSS_ESCAPED = "&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt;"


def add_review(db, submission, mentor, verdict, comment):
    submission.status = verdict
    submission.review = Review(mentor_id=mentor.id, verdict=verdict, comment=comment)
    db.commit()


def test_us5_ac1_student_sees_own_attempts_with_number_date_status_review(
    student_client, db_session, assignment, student, mentor, make_submission
):
    first = make_submission(assignment, student)
    add_review(db_session, first, mentor, "changes_requested", "Не обработан пустой ввод")
    second = make_submission(assignment, student)

    page = student_client.get(f"/assignments/{assignment.id}").text
    rows = re.findall(r'<tr class="attempt" data-attempt="(\d+)">(.*?)</tr>', page, re.S)
    assert [int(n) for n, _ in rows] == [2, 1]

    row2, row1 = rows[0][1], rows[1][1]
    assert f'href="/submissions/{second.id}"' in row2
    assert "Ждёт ревью" in row2
    assert second.created_at.strftime("%Y-%m-%d") in row2

    assert f'href="/submissions/{first.id}"' in row1
    assert "На доработку" in row1
    assert "Не обработан пустой ввод" in row1


def test_us5_ac1_review_visible_on_own_submission_page(
    student_client, db_session, assignment, student, mentor, make_submission
):
    s = make_submission(assignment, student, code="int main() { return 1; }")
    add_review(db_session, s, mentor, "accepted", "Чисто и понятно")

    resp = student_client.get(f"/submissions/{s.id}")
    assert resp.status_code == 200
    assert "return 1;" in resp.text
    assert "Принято" in resp.text
    assert "Чисто и понятно" in resp.text


def test_us5_ac1_no_attempts_yet(student_client, assignment):
    page = student_client.get(f"/assignments/{assignment.id}").text
    assert 'class="attempt"' not in page
    assert "Попыток пока нет" in page


def test_us5_ac1_student_does_not_see_other_students_attempts(
    student_client, db_session, assignment, other_student, mentor, make_submission
):
    s = make_submission(assignment, other_student)
    add_review(db_session, s, mentor, "changes_requested", "Комментарий Бобу")
    page = student_client.get(f"/assignments/{assignment.id}").text
    assert f"/submissions/{s.id}" not in page
    assert "Комментарий Бобу" not in page


def test_us5_assignment_list_shows_status_per_assignment(
    student_client, db_session, assignment, student, mentor, make_submission
):
    s = make_submission(assignment, student)
    add_review(db_session, s, mentor, "changes_requested", "ещё раз")
    make_submission(assignment, student)
    listing = student_client.get("/assignments").text
    assert "Ждёт ревью" in listing


def test_us5_ac2_other_students_submission_is_404(
    student_client, db_session, assignment, other_student, make_submission
):
    s = make_submission(assignment, other_student, code="секретный код")
    resp = student_client.get(f"/submissions/{s.id}")
    assert resp.status_code == 404
    assert "секретный код" not in resp.text

    missing = student_client.get("/submissions/9999")
    assert missing.status_code == 404
    assert resp.text == missing.text


def test_us5_ac2_author_and_mentor_can_open_submission(
    student_client, mentor_client, assignment, student, make_submission
):
    s = make_submission(assignment, student)
    assert student_client.get(f"/submissions/{s.id}").status_code == 200
    assert mentor_client.get(f"/submissions/{s.id}").status_code == 200


def test_us5_ac3_code_is_html_escaped(student_client, mentor_client, assignment, student, make_submission):
    s = make_submission(assignment, student, code=f"if (a < b && c > d) {{}}\n// {XSS}")
    for client in (student_client, mentor_client):
        html = client.get(f"/submissions/{s.id}").text
        assert XSS not in html
        assert XSS_ESCAPED in html
        assert "a &lt; b &amp;&amp; c &gt; d" in html


def test_us5_ac3_review_comment_is_html_escaped(
    student_client, db_session, assignment, student, mentor, make_submission
):
    s = make_submission(assignment, student)
    add_review(db_session, s, mentor, "changes_requested", f"Смотри {XSS}")
    for url in (f"/submissions/{s.id}", f"/assignments/{assignment.id}"):
        html = student_client.get(url).text
        assert XSS not in html
        assert XSS_ESCAPED in html


def test_us5_ac3_resubmitted_code_is_escaped_in_form(student_client, assignment):
    resp = student_client.post(
        f"/assignments/{assignment.id}/submissions", data={"code": "x" * 100_001 + XSS}
    )
    assert resp.status_code == 400
    assert XSS not in resp.text
    assert XSS_ESCAPED in resp.text


def test_us5_ac3_assignment_text_is_escaped(db_session, student_client, mentor):
    from app.models import Assignment

    a = Assignment(title=f"T {XSS}", description=f"D {XSS}", author_id=mentor.id)
    db_session.add(a)
    db_session.commit()
    for url in ("/assignments", f"/assignments/{a.id}"):
        html = student_client.get(url).text
        assert XSS not in html
        assert XSS_ESCAPED in html
