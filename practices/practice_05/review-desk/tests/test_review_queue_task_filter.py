"""Фильтр очереди ревью по задаче.

Спека: openspec/changes/review-queue-task-filter/specs/review-queue/spec.md
(требования RQF-1…RQF-12, сценарии S1…S20).

S2 (без параметра очередь не меняется) покрыт baseline-тестом
tests/test_us4_review.py::test_us4_ac1_queue_shows_only_pending_oldest_first.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Assignment

INT64_MAX = 2**63 - 1

INVALID_VALUES = [
    "0",
    "-1",
    "05",
    " 5",
    "+5",
    "5.0",
    "1_000",
    "1e3",
    "٥",
    "²",
    str(INT64_MAX + 1),
    "99999999999999999999",
    "   ",
]


def submission_ids(html):
    return [int(x) for x in re.findall(r'href="/submissions/(\d+)', html)]


@pytest.fixture
def other_assignment(db_session, mentor):
    a = Assignment(title="Разворот строки", description="Разверните строку.", author_id=mentor.id)
    db_session.add(a)
    db_session.commit()
    return a


def test_rqf1_filter_shows_only_pending_of_task_oldest_first(
    mentor_client, db_session, assignment, other_assignment, student, other_student, make_submission
):
    """RQF-1 / S1: фильтр показывает только pending-сдачи задачи, старые сверху."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = make_submission(assignment, student)
    older = make_submission(assignment, other_student)
    done = make_submission(assignment, student, status="accepted")
    foreign = make_submission(other_assignment, student)
    newer.created_at = base + timedelta(hours=2)
    older.created_at = base + timedelta(hours=1)
    done.created_at = base
    foreign.created_at = base
    db_session.commit()

    resp = mentor_client.get("/review", params={"assignment_id": assignment.id})
    assert resp.status_code == 200
    assert submission_ids(resp.text) == [older.id, newer.id]


def test_rqf1_empty_value_means_no_filter(
    mentor_client, assignment, other_assignment, student, make_submission
):
    """RQF-1 / S3: ?assignment_id= — полная очередь, как без параметра."""
    a = make_submission(assignment, student)
    b = make_submission(other_assignment, student)

    resp = mentor_client.get("/review?assignment_id=")
    assert resp.status_code == 200
    assert sorted(submission_ids(resp.text)) == sorted([a.id, b.id])


def test_rqf1_repeated_param_last_wins(
    mentor_client, assignment, other_assignment, student, make_submission
):
    """RQF-1 / S8: при повторе параметра используется последнее значение."""
    make_submission(assignment, student)
    b = make_submission(other_assignment, student)

    resp = mentor_client.get(
        "/review", params=[("assignment_id", assignment.id), ("assignment_id", other_assignment.id)]
    )
    assert resp.status_code == 200
    assert submission_ids(resp.text) == [b.id]


def test_rqf3_unknown_task_is_404(mentor_client, assignment):
    """RQF-3 / S6: несуществующий id задачи — 404 «Задача не найдена»."""
    resp = mentor_client.get("/review", params={"assignment_id": "9999"})
    assert resp.status_code == 404
    assert "Задача не найдена" in resp.text


def test_rqf3_int64_max_is_404_not_500(mentor_client):
    """RQF-3 / S6b: предельное значение 2^63-1 — 404, не 500."""
    resp = mentor_client.get("/review", params={"assignment_id": str(INT64_MAX)})
    assert resp.status_code == 404
    assert "Задача не найдена" in resp.text


def test_rqf4_non_numeric_was_ignored_now_404(mentor_client, assignment, student, make_submission):
    """RQF-4 / S7a: ?assignment_id=abc раньше давал 200 с полной очередью, теперь 404."""
    make_submission(assignment, student)
    resp = mentor_client.get("/review", params={"assignment_id": "abc"})
    assert resp.status_code == 404
    assert "Задача не найдена" in resp.text


@pytest.mark.parametrize("value", INVALID_VALUES)
def test_rqf4_invalid_values_are_404(mentor_client, db_session, mentor, value):
    """RQF-4 / S7b: неканоничные и запредельные значения — 404, не 200 и не 500."""
    # Задача с id=5 существует, чтобы "05", " 5", "+5", "5.0", "٥" не совпали
    # с 404 случайно из-за отсутствия задачи.
    for i in range(5):
        db_session.add(Assignment(title=f"Задача {i}", description="x", author_id=mentor.id))
    db_session.commit()

    resp = mentor_client.get("/review", params={"assignment_id": value})
    assert resp.status_code == 404
    assert "Задача не найдена" in resp.text


@pytest.mark.parametrize("value", ["existing", "abc", "9999", ""])
def test_rqf5_student_gets_403_with_any_value(student_client, assignment, value):
    """RQF-5 / S9: студент получает 403 при любом значении параметра."""
    raw = str(assignment.id) if value == "existing" else value
    resp = student_client.get("/review", params={"assignment_id": raw})
    assert resp.status_code == 403


def test_rqf5_anonymous_redirected_to_login(client):
    """RQF-5 / S10: без сессии — редирект на /login."""
    resp = client.get("/review?assignment_id=abc", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def options(html):
    """[(value, selected, label)] пунктов <select name="assignment_id">."""
    select = re.search(r'<select name="assignment_id">(.*?)</select>', html, re.S)
    assert select, "нет <select name=\"assignment_id\">"
    return [
        (value, bool(sel), label.strip())
        for value, sel, label in re.findall(
            r'<option value="([^"]*)"( selected)?>(.*?)</option>', select.group(1), re.S
        )
    ]


def heading(html):
    return re.search(r"<h1>(.*?)</h1>", html, re.S).group(1).strip()


RESET_LINK = '<a href="/review">Сбросить фильтр</a>'


def test_rqf2_task_without_pending_shows_filtered_empty_state(
    mentor_client, assignment, other_assignment, student, make_submission
):
    """RQF-2 / S4: задача есть, pending-сдач нет — отдельное пустое состояние."""
    make_submission(assignment, student, status="accepted")
    make_submission(other_assignment, student)

    resp = mentor_client.get("/review", params={"assignment_id": assignment.id})
    assert resp.status_code == 200
    assert f"Нет сдач, ждущих ревью, по задаче {assignment.title}" in resp.text
    assert RESET_LINK in resp.text
    assert "Непроверенных сдач нет." not in resp.text
    assert "/submissions/" not in resp.text


def test_rqf2_unfiltered_empty_keeps_general_message(mentor_client, assignment):
    """RQF-2 / S5: пустая очередь без фильтра — прежний общий текст."""
    resp = mentor_client.get("/review")
    assert resp.status_code == 200
    assert "Непроверенных сдач нет." in resp.text
    assert "Нет сдач, ждущих ревью, по задаче" not in resp.text
    assert "Сбросить фильтр" not in resp.text


def test_rqf6_form_without_filter(mentor_client, assignment, other_assignment):
    """RQF-6 / S11a: форма есть и при пустой очереди, выбран пункт «Все задачи»."""
    resp = mentor_client.get("/review")
    assert resp.status_code == 200
    assert re.search(r'<form method="get" action="/review"[^>]*>', resp.text)
    opts = options(resp.text)
    assert opts[0] == ("", True, "Все задачи")
    assert {(v, label) for v, _, label in opts[1:]} == {
        (str(assignment.id), assignment.title),
        (str(other_assignment.id), other_assignment.title),
    }
    assert not any(sel for _, sel, _ in opts[1:])
    assert re.search(r'<button type="submit"[^>]*>Показать</button>', resp.text)
    assert heading(resp.text) == "Очередь ревью"
    assert "Сбросить фильтр" not in resp.text


def test_rqf6_form_marks_selected_task_and_reset_link(
    mentor_client, assignment, other_assignment, student, make_submission
):
    """RQF-6 / S11b: активный фильтр выбран, заголовок с названием, есть «Сбросить фильтр»."""
    make_submission(assignment, student)

    resp = mentor_client.get("/review", params={"assignment_id": assignment.id})
    assert resp.status_code == 200
    selected = [v for v, sel, _ in options(resp.text) if sel]
    assert selected == [str(assignment.id)]
    assert heading(resp.text) == f"Очередь ревью · {assignment.title}"
    assert RESET_LINK in resp.text


def test_rqf7_open_links_carry_filter_only_when_active(
    mentor_client, assignment, student, make_submission
):
    """RQF-7 / S12: «Открыть» несёт ?assignment_id=N только при активном фильтре."""
    s = make_submission(assignment, student)

    filtered = mentor_client.get("/review", params={"assignment_id": assignment.id}).text
    assert f'href="/submissions/{s.id}?assignment_id={assignment.id}"' in filtered

    plain = mentor_client.get("/review").text
    assert f'href="/submissions/{s.id}"' in plain
    assert "?assignment_id=" not in plain


def test_rqf12_task_title_escaped(mentor_client, db_session, mentor):
    """RQF-12 / S20: название задачи экранируется в заголовке, пустом состоянии и <select>."""
    a = Assignment(title="<script>alert(1)</script>", description="x", author_id=mentor.id)
    db_session.add(a)
    db_session.commit()

    resp = mentor_client.get("/review", params={"assignment_id": a.id})
    assert resp.status_code == 200
    assert "<script>alert(1)</script>" not in resp.text
    escaped = "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert heading(resp.text) == f"Очередь ревью · {escaped}"
    assert f"Нет сдач, ждущих ревью, по задаче {escaped}" in resp.text
    assert (str(a.id), True, escaped) in options(resp.text)


def back_link(html):
    m = re.search(r'<a href="([^"]*)">← Очередь ревью</a>', html)
    return m.group(1) if m else None


def hidden_filter(html):
    m = re.search(r'<input type="hidden" name="assignment_id" value="([^"]*)">', html)
    return m.group(1) if m else None


def test_rqf8_submission_page_keeps_filter(mentor_client, assignment, student, make_submission):
    """RQF-8 / S13: валидный фильтр — ссылка в отфильтрованную очередь и скрытое поле."""
    s = make_submission(assignment, student)
    resp = mentor_client.get(f"/submissions/{s.id}", params={"assignment_id": assignment.id})
    assert resp.status_code == 200
    assert back_link(resp.text) == f"/review?assignment_id={assignment.id}"
    assert hidden_filter(resp.text) == str(assignment.id)


def test_rqf8_filter_for_other_task_is_kept(
    mentor_client, assignment, other_assignment, student, make_submission
):
    """RQF-8 / S13b: фильтр по другой задаче сохраняется как есть."""
    s = make_submission(assignment, student)
    resp = mentor_client.get(f"/submissions/{s.id}", params={"assignment_id": other_assignment.id})
    assert resp.status_code == 200
    assert back_link(resp.text) == f"/review?assignment_id={other_assignment.id}"
    assert hidden_filter(resp.text) == str(other_assignment.id)


@pytest.mark.parametrize("value", ["abc", "0", "9999", "99999999999999999999"])
def test_rqf8_submission_page_ignores_invalid_filter(
    mentor_client, assignment, student, make_submission, value
):
    """RQF-8 / S14: невалидный или несуществующий фильтр молча игнорируется."""
    s = make_submission(assignment, student)
    resp = mentor_client.get(f"/submissions/{s.id}", params={"assignment_id": value})
    assert resp.status_code == 200
    assert back_link(resp.text) == "/review"
    assert 'name="assignment_id"' not in resp.text


def test_rqf8_no_hidden_field_without_filter(mentor_client, assignment, student, make_submission):
    """RQF-8 / S14b: без фильтра — ссылка на /review, скрытого поля нет."""
    s = make_submission(assignment, student)
    resp = mentor_client.get(f"/submissions/{s.id}")
    assert resp.status_code == 200
    assert back_link(resp.text) == "/review"
    assert 'name="assignment_id"' not in resp.text


def test_rqf8_student_unaffected_by_param(student_client, assignment, student, make_submission):
    """RQF-8 / S14c: студенту параметр безразличен."""
    s = make_submission(assignment, student)
    plain = student_client.get(f"/submissions/{s.id}")
    assert plain.status_code == 200
    for value in ["abc", str(assignment.id)]:
        resp = student_client.get(f"/submissions/{s.id}", params={"assignment_id": value})
        assert resp.status_code == 200
        assert resp.text == plain.text
    assert back_link(plain.text) is None
    assert 'name="verdict"' not in plain.text


def post_review(client, submission_id, verdict="accepted", comment="Отлично", **extra):
    return client.post(
        f"/submissions/{submission_id}/review",
        data={"verdict": verdict, "comment": comment, **extra},
        follow_redirects=False,
    )


def test_rqf9_review_redirects_to_filtered_queue(
    mentor_client, db_session, assignment, student, make_submission
):
    """RQF-9 / S15: успешное ревью с фильтром — 303 в отфильтрованную очередь."""
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, assignment_id=str(assignment.id))
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/review?assignment_id={assignment.id}"
    db_session.refresh(s)
    assert s.review is not None


@pytest.mark.parametrize("extra", [{}, {"assignment_id": ""}])
def test_rqf9_review_without_filter_redirects_to_plain_queue(
    mentor_client, db_session, assignment, student, make_submission, extra
):
    """RQF-9 / S16: без поля или с пустым полем — Location ровно /review."""
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, **extra)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/review"
    db_session.refresh(s)
    assert s.review is not None


def test_rqf9_last_review_lands_on_filtered_empty_state(
    mentor_client, assignment, student, make_submission
):
    """RQF-9 / S19: после ревью последней pending-сдачи — пустое отфильтрованное состояние."""
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, assignment_id=str(assignment.id))
    page = mentor_client.get(resp.headers["location"])
    assert page.status_code == 200
    assert f"Нет сдач, ждущих ревью, по задаче {assignment.title}" in page.text
    assert [v for v, sel, _ in options(page.text) if sel] == [str(assignment.id)]


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "0",
        "05",
        "9999",
        "99999999999999999999",
        "//evil.example",
        "https://evil.example/",
        "/review?x=1",
        "1/../../evil",
    ],
)
def test_rqf10_bad_filter_falls_back_no_open_redirect(
    mentor_client, db_session, assignment, student, make_submission, value
):
    """RQF-10 / S17: невалидное скрытое поле — ревью сохранено, Location ровно /review."""
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, assignment_id=value)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/review"
    db_session.refresh(s)
    assert s.review is not None
    assert s.status == "accepted"


def test_rqf11_invalid_review_keeps_filter(
    mentor_client, db_session, assignment, student, make_submission
):
    """RQF-11 / S18: ошибка валидации ревью — 400, фильтр сохранён в поле и ссылке."""
    s = make_submission(assignment, student)
    resp = post_review(mentor_client, s.id, verdict="", assignment_id=str(assignment.id))
    assert resp.status_code == 400
    assert re.search(r'<p class="field-error" data-field="verdict">.+?</p>', resp.text, re.S)
    assert hidden_filter(resp.text) == str(assignment.id)
    assert back_link(resp.text) == f"/review?assignment_id={assignment.id}"
    db_session.refresh(s)
    assert s.review is None


def test_rqf11_second_review_with_filter_is_409(
    mentor_client, assignment, student, make_submission
):
    """RQF-11 / S18b: повторное ревью с фильтром — 409, как в baseline."""
    s = make_submission(assignment, student)
    assert post_review(mentor_client, s.id, assignment_id=str(assignment.id)).status_code == 303
    resp = post_review(mentor_client, s.id, assignment_id=str(assignment.id))
    assert resp.status_code == 409
