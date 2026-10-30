"""Сквозные сценарии построчных комментариев: настоящие роуты, сервис и шаблоны.

Docstring каждого теста: [UI FR-nnn] [Л FR-nnn] LC-NN (LC-29).
"""

from sqlalchemy import select

from app.models import LineComment

CODE = "int a = 1;\nint b = 2;\nreturn a + b;\n"  # N = 3 строки


def comments(db):
    return list(db.scalars(select(LineComment)))


def test_e2e_mentor_comments_line_2_student_sees_escaped(
    mentor_client, student_client, db_session, assignment, student, make_submission
):
    """[UI FR-005] [UI FR-006] [UI FR-008] [UI FR-014] [Л FR-004] [Л FR-013] [Л FR-017] LC-10, LC-19."""
    s = make_submission(assignment, student, code=CODE)
    resp = mentor_client.post(
        f"/submissions/{s.id}/line-comments",
        data={"line": "2", "text": "<b>важно</b>"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/submissions/{s.id}#L2"

    page = student_client.get(f"/submissions/{s.id}")
    assert page.status_code == 200
    html = page.text
    assert "<b>важно" not in html
    pos = html.index("&lt;b&gt;важно&lt;/b&gt;")
    assert html.index('id="L2"') < pos < html.index('id="L3"')
    assert 'id="line-comment-form"' not in html


def test_e2e_boundary_line_n_plus_1_and_int64_overflow(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-013] [Л FR-005] [Л FR-014] LC-14, LC-15, LC-16, LC-25."""
    s = make_submission(assignment, student, code=CODE)
    n = 3
    for bad in (str(n + 1), "9223372036854775808"):
        resp = mentor_client.post(
            f"/submissions/{s.id}/line-comments",
            data={"line": bad, "text": "сохранить-ввод"},
            follow_redirects=False,
        )
        assert resp.status_code == 400, bad
        assert 'data-field="line"' in resp.text
        assert 'data-field="text"' not in resp.text
        assert f'value="{bad}"' in resp.text
        assert "сохранить-ввод" in resp.text
        assert comments(db_session) == []

    ok = mentor_client.post(
        f"/submissions/{s.id}/line-comments",
        data={"line": str(n), "text": "последняя строка"},
        follow_redirects=False,
    )
    assert ok.status_code == 303
    assert ok.headers["location"].endswith("#L3")
    assert len(comments(db_session)) == 1


def test_e2e_foreign_student_gets_404_without_comments(
    make_client, db_session, assignment, student, other_student, mentor, make_submission
):
    """[UI FR-009] [Л FR-009] LC-14, LC-17, LC-19."""
    s = make_submission(assignment, student, code=CODE)
    db_session.add(LineComment(submission_id=s.id, author_id=mentor.id, line=1, text="чужое-замечание"))
    db_session.commit()
    resp = make_client(other_student).get(f"/submissions/{s.id}")
    assert resp.status_code == 404
    assert "Не найдено" in resp.text
    assert "чужое-замечание" not in resp.text
