"""Построчные комментарии ментора (зона UI): specs/001-line-comments-ui/.

Docstring каждого теста: [UI FR-nnn] и LC-NN (LC-29). Проверки HTML - по устойчивым
признакам (id, data-field, name, maxlength), не по целым кускам разметки.
"""

from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import LineComment
from app.services import auth
from tests.conftest import PASSWORD

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

# --- хелперы -------------------------------------------------------------


def numbered_code(n: int) -> str:
    return "\n".join(f"line {i}" for i in range(1, n + 1))


def add_comment(db, submission, author, line, text="замечание"):
    comment = LineComment(submission_id=submission.id, author_id=author.id, line=line, text=text)
    db.add(comment)
    db.commit()
    return comment


def post_comment(client, submission_id, line="1", text="замечание", assignment_id=None):
    """Полное тело формы: без него POST даёт ложный 400/404."""
    data = {"line": line, "text": text}
    if assignment_id is not None:
        data["assignment_id"] = str(assignment_id)
    return client.post(
        f"/submissions/{submission_id}/line-comments", data=data, follow_redirects=False
    )


def count_comments(db):
    return len(list(db.scalars(select(LineComment))))


def row_ids(html):
    """Номера найденных якорей строк: id="L{n}"."""
    import re

    return [int(n) for n in re.findall(r'id="L(\d+)"', html)]


# --- Phase 2: строки кода с номерами и якорями ---------------------------


def test_fr001_code_rows_numbered_with_anchors(
    mentor_client, student_client, assignment, student, make_submission
):
    """[UI FR-001] LC-04, LC-05, LC-11, LC-18: у каждой строки номер и якорь L{n}."""
    s = make_submission(assignment, student, code=numbered_code(3))
    for client in (mentor_client, student_client):
        html = client.get(f"/submissions/{s.id}").text
        assert row_ids(html) == [1, 2, 3]
        assert 'class="line-no"' in html


def test_fr001_numbering_follows_lc04(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-001] LC-04: \\r\\n, \\r, финальный \\n, пустая строка и однострочный код."""
    crlf = make_submission(assignment, student, code="a\r\nb\rc\n")
    assert row_ids(mentor_client.get(f"/submissions/{crlf.id}").text) == [1, 2, 3]
    other = make_submission(assignment, student, code="a\n\nb")
    assert row_ids(mentor_client.get(f"/submissions/{other.id}").text) == [1, 2, 3]
    one = make_submission(assignment, student, code="int main() {}")
    assert row_ids(mentor_client.get(f"/submissions/{one.id}").text) == [1]


def test_fr014_no_safe_filter_in_templates():
    """[UI FR-014] LC-19: в шаблонах нет |safe."""
    offenders = [str(p) for p in TEMPLATES.rglob("*.html") if "|safe" in p.read_text("utf-8")]
    assert offenders == []


def test_fr015_page_has_no_javascript(
    mentor_client, student_client, assignment, student, make_submission
):
    """[UI FR-015] LC-18: страница сдачи без <script."""
    s = make_submission(assignment, student, code=numbered_code(2))
    for client in (mentor_client, student_client):
        assert "<script" not in client.get(f"/submissions/{s.id}").text.lower()


# --- US1: ментор комментирует строку ---------------------------------------


def test_fr002_mentor_sees_single_form_without_comment_links(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-002] [UI FR-004] LC-06, LC-09, LC-18: одна форма «номер + текст», без ссылок."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = mentor_client.get(f"/submissions/{s.id}")
    html = resp.text
    assert resp.status_code == 200
    assert html.count('id="line-comment-form"') == 1
    assert f'action="/submissions/{s.id}/line-comments"' in html
    assert 'name="line"' in html
    assert 'inputmode="numeric"' in html
    assert 'name="text"' in html
    assert 'maxlength="2000"' in html
    assert "Отправить" in html
    assert "Комментировать" not in html


def test_fr004_hidden_assignment_id_only_with_queue_filter(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-004] LC-13, LC-18: скрытое assignment_id только при валидном фильтре очереди."""
    s = make_submission(assignment, student, code=numbered_code(2))
    def form_html(url):
        html = mentor_client.get(url).text
        start = html.find('id="line-comment-form"')
        return "" if start < 0 else html[start : html.index("</form>", start)]

    with_filter = form_html(f"/submissions/{s.id}?assignment_id={assignment.id}")
    assert 'name="assignment_id"' in with_filter
    assert f'value="{assignment.id}"' in with_filter
    assert 'name="line"' in with_filter
    assert 'name="assignment_id"' not in form_html(f"/submissions/{s.id}")
    assert 'name="line"' in form_html(f"/submissions/{s.id}?assignment_id=abc")
    assert 'name="assignment_id"' not in form_html(f"/submissions/{s.id}?assignment_id=abc")


def test_fr003_form_visible_in_any_status(
    mentor_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-003] LC-23: форма видна у pending, accepted и changes_requested (с ревью)."""
    from app.models import Review

    for status in ("pending", "accepted", "changes_requested"):
        s = make_submission(assignment, student, status=status, code=numbered_code(2))
        if status != "pending":
            db_session.add(Review(submission_id=s.id, mentor_id=mentor.id, verdict=status, comment="ок"))
            db_session.commit()
        html = mentor_client.get(f"/submissions/{s.id}").text
        assert 'id="line-comment-form"' in html, status


def test_fr005_success_redirects_to_anchor(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-005] [UI FR-016] LC-10, LC-13: 303 на #L{n}, фильтр только валидный."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line="2")
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/submissions/{s.id}#L2"
    resp = post_comment(mentor_client, s.id, line="2", assignment_id=assignment.id)
    assert resp.headers["location"] == f"/submissions/{s.id}?assignment_id={assignment.id}#L2"
    resp = post_comment(mentor_client, s.id, line="2", assignment_id="//evil.example")
    assert resp.headers["location"] == f"/submissions/{s.id}#L2"
    assert count_comments(db_session) == 3


def test_fr006_comment_under_own_line_with_author_and_date(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-006] LC-02, LC-18: комментарий между якорями L2 и L3, автор, дата и текст."""
    s = make_submission(assignment, student, code=numbered_code(3))
    assert post_comment(mentor_client, s.id, line="2", text="Проверь границы").status_code == 303
    html = mentor_client.get(f"/submissions/{s.id}").text
    assert 'class="line-comment"' in html
    pos = html.index("Проверь границы")
    assert html.index('id="L2"') < pos < html.index('id="L3"')
    assert "Ментор" in html[html.index('id="L2"') : html.index('id="L3"')]
    assert " UTC" in html[html.index('id="L2"') : html.index('id="L3"')]


def test_fr006_two_comments_same_line_in_creation_order(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-006] LC-03: два комментария к строке 2 - старый выше."""
    s = make_submission(assignment, student, code=numbered_code(3))
    post_comment(mentor_client, s.id, line="2", text="первый-комментарий")
    post_comment(mentor_client, s.id, line="2", text="второй-комментарий")
    html = mentor_client.get(f"/submissions/{s.id}").text
    assert html.index("первый-комментарий") < html.index("второй-комментарий")


def test_fr007_commented_row_is_marked(
    mentor_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-007] LC-18: строка с комментарием помечена code-row--commented, остальные нет."""
    s = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, s, mentor, 2)
    html = mentor_client.get(f"/submissions/{s.id}").text
    assert html.count("code-row--commented") == 1
    row2 = html[html.index('id="L2"') - 80 : html.index('id="L2"') + 20]
    assert "code-row--commented" in row2


def test_fr018_mentor_sees_comments_of_other_mentors(
    mentor_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-018] LC-21: ментор видит комментарии другого ментора с его именем."""
    other = auth.create_user(db_session, "mentor2", PASSWORD, "mentor", "Ментор Два")
    s = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, s, mentor, 1, "от-первого")
    add_comment(db_session, s, other, 1, "от-второго")
    html = mentor_client.get(f"/submissions/{s.id}").text
    assert "от-первого" in html and "от-второго" in html
    assert "Ментор Два" in html


def test_fr016_queue_link_keeps_filter_after_400(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-016] LC-13: после 400 ссылка «← Очередь ревью» сохраняет фильтр."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line="1", text="", assignment_id=assignment.id)
    assert resp.status_code == 400
    assert 'data-field="text"' in resp.text
    assert f'href="/review?assignment_id={assignment.id}"' in resp.text
    assert count_comments(db_session) == 0


# --- US2: ученик видит комментарии -----------------------------------------


def test_fr008_student_sees_comments_under_lines_3_and_7(
    student_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-008] [UI FR-006] LC-19: комментарии под строками 3 и 7, у остальных нет."""
    s = make_submission(assignment, student, code=numbered_code(8))
    add_comment(db_session, s, mentor, 3, "про-третью")
    add_comment(db_session, s, mentor, 7, "про-седьмую")
    html = student_client.get(f"/submissions/{s.id}").text
    assert html.index('id="L3"') < html.index("про-третью") < html.index('id="L4"')
    assert html.index('id="L7"') < html.index("про-седьмую") < html.index('id="L8"')
    assert html.count("code-row--commented") == 2


def test_fr017_student_sees_comment_while_pending(
    student_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-017] LC-24: комментарий виден ученику у сдачи pending без ревью."""
    s = make_submission(assignment, student, status="pending", code=numbered_code(3))
    add_comment(db_session, s, mentor, 2, "видно-сразу")
    html = student_client.get(f"/submissions/{s.id}").text
    assert "видно-сразу" in html
    assert "Ментор" in html


def test_fr008_student_has_no_comment_form_controls(
    student_client, assignment, student, make_submission
):
    """[UI FR-008] LC-19: у ученика-автора нет формы комментария и полей line/text."""
    s = make_submission(assignment, student, code=numbered_code(3))
    html = student_client.get(f"/submissions/{s.id}").text
    assert 'id="line-comment-form"' not in html
    assert 'name="line"' not in html
    assert 'name="text"' not in html


def test_fr009_foreign_student_gets_404_without_comments(
    make_client, db_session, assignment, student, other_student, mentor, make_submission
):
    """[UI FR-009] LC-14, LC-17: чужая сдача - 404 «Не найдено», комментарии не раскрыты."""
    s = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, s, mentor, 1, "секретное-замечание")
    resp = make_client(other_student).get(f"/submissions/{s.id}")
    assert resp.status_code == 404
    assert "Не найдено" in resp.text
    assert "секретное-замечание" not in resp.text


def test_fr010_student_post_is_403_even_for_missing_submission(
    student_client, db_session, assignment, student, make_submission
):
    """[UI FR-010] LC-14: любой POST ученика - 403, в том числе на несуществующий id."""
    s = make_submission(assignment, student, code=numbered_code(3))
    for sid in (s.id, 999999):
        resp = post_comment(student_client, sid, line="1", text="валидный текст")
        assert resp.status_code == 403, sid
        assert "Доступ запрещён" in resp.text
    assert count_comments(db_session) == 0


def test_fr014_comment_text_is_escaped_for_student_and_mentor(
    mentor_client, student_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-014] LC-19: HTML в тексте комментария показан текстом."""
    s = make_submission(assignment, student, code=numbered_code(2))
    add_comment(db_session, s, mentor, 1, "<b>x</b> & <script>alert(1)</script>")
    for client in (student_client, mentor_client):
        html = client.get(f"/submissions/{s.id}").text
        assert "&lt;b&gt;x&lt;/b&gt;" in html
        assert "<b>x</b>" not in html
        assert "<script>alert" not in html


def test_fr019_new_attempt_has_own_empty_state(
    student_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-019] LC-22, LC-20: комментарии остаются на своей попытке."""
    first = make_submission(assignment, student, status="changes_requested", code=numbered_code(3))
    second = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, first, mentor, 2, "только-к-первой")
    html1 = student_client.get(f"/submissions/{first.id}").text
    html2 = student_client.get(f"/submissions/{second.id}").text
    assert "только-к-первой" in html1
    assert "только-к-первой" not in html2
    assert "Комментариев к строкам пока нет" in html2


# --- US3: состояния и ошибки -----------------------------------------------

EMPTY_HINT = "Комментариев к строкам пока нет"


def test_fr011_empty_state_for_mentor_and_student(
    mentor_client, student_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-011] LC-20: без комментариев - подсказка; с комментарием - нет."""
    empty = make_submission(assignment, student, status="changes_requested", code=numbered_code(2))
    filled = make_submission(assignment, student, code=numbered_code(2))
    add_comment(db_session, filled, mentor, 1)
    for client in (mentor_client, student_client):
        html = client.get(f"/submissions/{empty.id}").text
        assert 'id="no-line-comments"' in html and EMPTY_HINT in html
        assert EMPTY_HINT not in client.get(f"/submissions/{filled.id}").text


def test_fr011_no_empty_state_after_failed_review_rerender(
    mentor_client, db_session, assignment, student, mentor, make_submission
):
    """[UI FR-011] [UI FR-016] LC-12, LC-20: 400 ревью без вердикта показывает комментарии."""
    s = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, s, mentor, 2, "виден-после-400")
    resp = mentor_client.post(
        f"/submissions/{s.id}/review", data={"comment": "текст ревью"}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert 'data-field="verdict"' in resp.text
    assert "виден-после-400" in resp.text
    assert EMPTY_HINT not in resp.text


def test_fr012_empty_text_400_error_and_input_kept(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-012] LC-14, LC-16: пустой текст - 400, ошибка у text, номер сохранён."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line="2", text="   ")
    assert resp.status_code == 400
    assert 'data-field="text"' in resp.text
    assert 'data-field="line"' not in resp.text
    assert 'value="2"' in resp.text
    assert count_comments(db_session) == 0


def test_fr012_too_long_text_400_input_kept(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-012] LC-06, LC-16: текст длиннее лимита - 400, ввод возвращён в форму."""
    s = make_submission(assignment, student, code=numbered_code(3))
    long_text = "x" * 2001
    resp = post_comment(mentor_client, s.id, line="3", text=long_text)
    assert resp.status_code == 400
    assert 'data-field="text"' in resp.text
    assert long_text in resp.text
    assert 'value="3"' in resp.text
    assert count_comments(db_session) == 0


@pytest.mark.parametrize("bad_line", ["99", "05", "abc", "0"])
def test_fr013_invalid_line_400_error_at_line_text_kept(
    mentor_client, db_session, assignment, student, make_submission, bad_line
):
    """[UI FR-013] LC-15, LC-16, LC-25: неверный номер - 400, ошибка у line, текст сохранён."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line=bad_line, text="сохранённый-текст")
    assert resp.status_code == 400
    assert 'data-field="line"' in resp.text
    assert 'data-field="text"' not in resp.text
    assert "сохранённый-текст" in resp.text
    assert f'value="{bad_line}"' in resp.text
    assert count_comments(db_session) == 0


def test_fr013_both_fields_invalid_show_both_errors(
    mentor_client, db_session, assignment, student, make_submission
):
    """[UI FR-013] LC-14, LC-16: неверны оба поля - обе ошибки."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line="99", text="")
    assert resp.status_code == 400
    assert 'data-field="line"' in resp.text and 'data-field="text"' in resp.text
    assert count_comments(db_session) == 0


@pytest.mark.parametrize("sid", ["999999", "99999999999999999999"])
def test_fr013_missing_submission_404_not_400(mentor_client, db_session, sid):
    """[UI FR-013] LC-14, LC-17: нет сдачи или id вне INTEGER - 404 «Не найдено»."""
    resp = mentor_client.post(
        f"/submissions/{sid}/line-comments",
        data={"line": "1", "text": "валидный текст"},
        follow_redirects=False,
    )
    assert resp.status_code == 404
    assert "Не найдено" in resp.text
    assert count_comments(db_session) == 0


def test_fr014_form_values_escaped_on_400(
    mentor_client, assignment, student, make_submission
):
    """[UI FR-014] LC-16: возвращённый в форму ввод экранирован."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(mentor_client, s.id, line="99", text='"><script>alert(1)</script>')
    assert resp.status_code == 400
    assert 'data-field="line"' in resp.text
    assert "<script>alert" not in resp.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text


def test_fr016_anonymous_post_redirects_to_login(
    client, assignment, student, make_submission
):
    """[UI FR-016] LC-14: без сессии POST - 303 на /login."""
    s = make_submission(assignment, student, code=numbered_code(3))
    resp = post_comment(client, s.id, line="1", text="валидный текст")
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"
