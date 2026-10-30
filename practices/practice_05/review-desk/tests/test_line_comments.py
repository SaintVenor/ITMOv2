"""Построчные комментарии ментора (зона логики): specs/002-line-comments-logic/.

Docstring каждого теста: [Л FR-nnn] и LC-NN (LC-29). Код фичи импортируется
внутри тестов, чтобы файл собирался и до реализации.
"""

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Submission
from app.services import auth

# --- хелперы -------------------------------------------------------------


def numbered_code(n: int) -> str:
    return "\n".join(f"line {i}" for i in range(1, n + 1))


def add_comment(db, submission, author, line, text="замечание"):
    from app.models import LineComment

    comment = LineComment(submission_id=submission.id, author_id=author.id, line=line, text=text)
    db.add(comment)
    db.commit()
    return comment


def post_comment(client, submission_id, line="1", text="замечание", assignment_id=None):
    data = {"line": line, "text": text}
    if assignment_id is not None:
        data["assignment_id"] = assignment_id
    return client.post(
        f"/submissions/{submission_id}/line-comments", data=data, follow_redirects=False
    )


def count_comments(db):
    from app.models import LineComment

    return len(list(db.scalars(select(LineComment))))


# --- Phase 2: схема, строки, вид ----------------------------------------


def test_line_comments_table_columns_and_no_unique():
    """[Л FR-001] [Л FR-007] LC-01: таблица line_comments, поля, NOT NULL, FK, без уникальных."""
    from app.db import Base

    table = Base.metadata.tables["line_comments"]
    cols = table.c
    assert set(cols.keys()) == {"id", "submission_id", "line", "text", "author_id", "created_at"}
    assert cols.id.primary_key
    for name in ("submission_id", "line", "text", "author_id", "created_at"):
        assert not cols[name].nullable, name
    assert {fk.target_fullname for fk in cols.submission_id.foreign_keys} == {"submissions.id"}
    assert {fk.target_fullname for fk in cols.author_id.foreign_keys} == {"users.id"}
    assert cols.created_at.type.timezone is True
    assert cols.created_at.default is not None
    uniques = [c for c in table.constraints if c.__class__.__name__ == "UniqueConstraint"]
    assert not uniques
    assert not any(ix.unique for ix in table.indexes)


def test_line_comments_two_on_same_line_and_line_check(
    db_session, mentor, student, assignment, make_submission
):
    """[Л FR-001] [Л FR-007] LC-01: две записи на строку проходят; line = 0 отклоняет БД."""
    sub = make_submission(assignment, student, code=numbered_code(3))
    add_comment(db_session, sub, mentor, 2, "a")
    add_comment(db_session, sub, mentor, 2, "b")
    assert count_comments(db_session) == 2
    with pytest.raises(IntegrityError):
        add_comment(db_session, sub, mentor, 0, "zero")
    db_session.rollback()


def test_init_db_adds_table_to_existing_db_without_migration():
    """[Л FR-002] LC-01: init_db на старой базе добавляет line_comments, данные целы."""
    from app.db import Base, init_db
    from app.models import User

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    old_tables = [t for name, t in Base.metadata.tables.items() if name != "line_comments"]
    Base.metadata.create_all(bind=engine, tables=old_tables)
    assert "line_comments" not in inspect(engine).get_table_names()
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(User(username="u", display_name="U", password_hash="x", role="student"))
    session.commit()
    init_db(engine)
    assert "line_comments" in inspect(engine).get_table_names()
    assert session.scalar(select(User).where(User.username == "u")) is not None
    session.close()
    engine.dispose()


def test_existing_tables_schema_unchanged():
    """[Л FR-002] LC-01: колонки users/assignments/submissions/reviews как в docs/architecture.md."""
    from app.db import Base

    expected = {
        "users": {"id", "username", "display_name", "password_hash", "role", "created_at"},
        "assignments": {"id", "title", "description", "author_id", "created_at"},
        "submissions": {
            "id", "assignment_id", "student_id", "attempt", "code", "status", "created_at",
        },
        "reviews": {"id", "submission_id", "mentor_id", "verdict", "comment", "created_at"},
    }
    for name, cols in expected.items():
        assert set(Base.metadata.tables[name].c.keys()) == cols, name


@pytest.mark.parametrize(
    "code, expected",
    [
        ("", []),
        ("a\n", ["a"]),
        ("\n", [""]),
        ("a\r\nb\rc", ["a", "b", "c"]),
        ("a\x0cb c", ["a\x0cb c"]),
        ("a\n\nb", ["a", "", "b"]),
        ("a\n\n", ["a", ""]),
    ],
)
def test_split_code_lines_rules(code, expected):
    """[Л FR-003] LC-04: единая функция строки (без splitlines)."""
    from app.services.line_comments import split_code_lines

    assert split_code_lines(code) == expected


def test_line_count_matches_split(db_session, student, assignment, make_submission):
    """[Л FR-003] LC-05: line_count = len(split_code_lines), для пустого кода 0."""
    from app.services.line_comments import line_count, split_code_lines

    code = "a\r\nb\rc\n\nd"
    sub = make_submission(assignment, student, code=code)
    assert line_count(sub) == len(split_code_lines(code)) == 5
    assert line_count(Submission(code="")) == 0


def test_view_fields_and_max_constant():
    """[Л FR-006] [Л FR-008] LC-02, LC-06: LineCommentView и LINE_COMMENT_MAX."""
    import dataclasses

    from app.services.line_comments import LINE_COMMENT_MAX, LineCommentView

    assert LINE_COMMENT_MAX == 2_000
    names = [f.name for f in dataclasses.fields(LineCommentView)]
    assert names == ["id", "line", "text", "author", "created_at"]


# --- Phase 3: чтение (US2) ----------------------------------------------

CONTEXT_KEYS = {
    "line_comments",
    "code_lines",
    "line_count",
    "can_comment",
    "line_comment_errors",
    "line_comment_form",
    "line_comment_max",
}


@pytest.fixture
def mentor2(db_session):
    return auth.create_user(db_session, "mentor2", "s3cret-pass", "mentor", "Ментор Два")


def test_list_order_line_created_id(db_session, mentor, student, assignment, make_submission):
    """[Л FR-008] LC-03: порядок line, created_at, id (вставка в обратном порядке)."""
    from datetime import datetime, timezone

    from app.models import LineComment
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student, code=numbered_code(6))
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    rows = [(5, t1, "e"), (2, t2, "b-late"), (2, t1, "b2"), (2, t1, "b1"), (1, t2, "a")]
    for line, ts, text in rows:
        db_session.add(
            LineComment(submission_id=sub.id, author_id=mentor.id, line=line, text=text, created_at=ts)
        )
    db_session.commit()
    views = list_line_comments(db_session, mentor, sub.id)
    assert [(v.line, v.text) for v in views] == [
        (1, "a"), (2, "b2"), (2, "b1"), (2, "b-late"), (5, "e"),
    ]


def test_list_view_author_is_display_name(db_session, mentor, student, assignment, make_submission):
    """[Л FR-008] LC-02: author - строка display_name, не User; нет username и хэша."""
    from app.services.line_comments import LineCommentView, list_line_comments

    sub = make_submission(assignment, student, code=numbered_code(2))
    add_comment(db_session, sub, mentor, 2, "t")
    [view] = list_line_comments(db_session, student, sub.id)
    assert isinstance(view, LineCommentView)
    assert view.author == "Ментор" and isinstance(view.author, str)
    assert (view.line, view.text) == (2, "t") and view.id and view.created_at


def test_list_empty_is_empty_list(db_session, student, assignment, make_submission):
    """[Л FR-008] LC-07: нет комментариев - пустой список, не ошибка."""
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student)
    assert list_line_comments(db_session, student, sub.id) == []


def test_list_text_returned_unchanged(db_session, mentor, student, assignment, make_submission):
    """[Л FR-013] LC-07: HTML в тексте отдаётся как есть, без очистки."""
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student)
    raw = "<script>alert(1)</script> & <b>x</b>"
    add_comment(db_session, sub, mentor, 1, raw)
    assert list_line_comments(db_session, mentor, sub.id)[0].text == raw


def test_list_access_rules(
    db_session, mentor, mentor2, student, other_student, assignment, make_submission
):
    """[Л FR-009] [Л FR-010] LC-07, LC-19, LC-21: свои/чужие сдачи, комментарии всех менторов."""
    from app.services.errors import NotFound
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student, code=numbered_code(3))
    other = make_submission(assignment, other_student, code=numbered_code(3))
    add_comment(db_session, sub, mentor, 1, "m1")
    add_comment(db_session, sub, mentor2, 1, "m2")
    add_comment(db_session, other, mentor, 2, "other")
    assert [v.text for v in list_line_comments(db_session, student, sub.id)] == ["m1", "m2"]
    assert [v.author for v in list_line_comments(db_session, mentor2, sub.id)] == [
        "Ментор", "Ментор Два",
    ]
    assert [v.text for v in list_line_comments(db_session, mentor, other.id)] == ["other"]
    with pytest.raises(NotFound):
        list_line_comments(db_session, student, other.id)


@pytest.mark.parametrize("bad_id", [2**63, 2**63 - 1, 999999, 0, -1, -(2**63) - 1])
def test_list_missing_submission_not_found(db_session, student, bad_id):
    """[Л FR-011] LC-08: несуществующий id и id вне INTEGER - NotFound, без OverflowError."""
    from app.services.errors import NotFound
    from app.services.line_comments import list_line_comments

    with pytest.raises(NotFound):
        list_line_comments(db_session, student, bad_id)


@pytest.mark.parametrize("status", ["pending", "accepted", "changes_requested"])
def test_list_visible_in_any_status(db_session, mentor, student, assignment, make_submission, status):
    """[Л FR-016] [Л FR-017] LC-23, LC-24: статус и ревью не влияют, ученик видит сразу."""
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student, status=status)
    add_comment(db_session, sub, mentor, 1, "t")
    assert len(list_line_comments(db_session, student, sub.id)) == 1
    assert len(list_line_comments(db_session, mentor, sub.id)) == 1


def test_can_comment_mentor_only(db_session, mentor, student, assignment, make_submission):
    """[Л FR-004] [Л FR-016] [Л FR-018] LC-07, LC-23: True для ментора в любом статусе."""
    from app.models import Review
    from app.services.line_comments import can_comment

    sub = make_submission(assignment, student)
    assert can_comment(mentor, sub) is True
    assert can_comment(student, sub) is False
    sub.review = Review(mentor_id=mentor.id, verdict="accepted", comment="ok")
    sub.status = "accepted"
    db_session.commit()
    assert can_comment(mentor, sub) is True
    assert can_comment(student, sub) is False


def _check_context(ctx, code, user_is_mentor):
    from app.services.line_comments import split_code_lines

    assert CONTEXT_KEYS <= set(ctx.keys())
    assert ctx["code_lines"] == split_code_lines(code)
    assert ctx["line_count"] == len(ctx["code_lines"])
    assert ctx["can_comment"] is user_is_mentor
    assert ctx["line_comment_max"] == 2000
    assert ctx["line_comment_errors"] == {} and ctx["line_comment_form"] == {}


def test_page_context_keys_mentor_and_student(
    db_session, mentor, student, assignment, make_submission, make_client
):
    """[Л FR-018] LC-11, LC-12: ключи контекста на GET страницы сдачи."""
    code = "a\r\nb\rc\n"
    sub = make_submission(assignment, student, code=code)
    add_comment(db_session, sub, mentor, 3, "z")
    add_comment(db_session, sub, mentor, 1, "x")
    for user, is_mentor in ((mentor, True), (student, False)):
        resp = make_client(user).get(f"/submissions/{sub.id}")
        assert resp.status_code == 200
        _check_context(resp.context, code, is_mentor)
        assert [v.line for v in resp.context["line_comments"]] == [1, 3]


def test_review_400_keeps_comments_in_context(
    db_session, mentor, student, assignment, make_submission, make_client
):
    """[Л FR-018] LC-12, LC-20: ревью без вердикта (400) отдаёт ключи и комментарии."""
    sub = make_submission(assignment, student, code=numbered_code(2))
    add_comment(db_session, sub, mentor, 2, "t")
    resp = make_client(mentor).post(
        f"/submissions/{sub.id}/review", data={"verdict": "", "comment": "x"}
    )
    assert resp.status_code == 400
    assert resp.context["submission"].id == sub.id
    _check_context(resp.context, numbered_code(2), True)
    assert [v.text for v in resp.context["line_comments"]] == ["t"]


def test_student_foreign_submission_404_same_as_missing(
    student, other_student, assignment, make_submission, make_client
):
    """[Л FR-009] LC-17, LC-19: чужая сдача для ученика 404 как несуществующая (статус и заголовок)."""
    foreign = make_submission(assignment, other_student)
    c = make_client(student)
    r1 = c.get(f"/submissions/{foreign.id}")
    r2 = c.get("/submissions/999999")
    assert r1.status_code == r2.status_code == 404
    assert r1.context["title"] == r2.context["title"] == "Не найдено"


# --- Phase 4: создание (US1) --------------------------------------------

N = 10


@pytest.fixture
def sub10(db_session, student, assignment, make_submission):
    return make_submission(assignment, student, code=numbered_code(N))


def test_create_success_and_listed(db_session, mentor, sub10):
    """[Л FR-001] [Л FR-008] LC-07: комментарий к строке 3 создан и виден в списке."""
    from app.models import LineComment
    from app.services.line_comments import create_line_comment, list_line_comments

    c = create_line_comment(db_session, mentor, sub10.id, "3", "  Замечание  ")
    assert isinstance(c, LineComment)
    assert (c.submission_id, c.line, c.text, c.author_id) == (sub10.id, 3, "Замечание", mentor.id)
    assert c.created_at is not None
    [v] = list_line_comments(db_session, mentor, sub10.id)
    assert (v.id, v.line, v.text) == (c.id, 3, "Замечание")


def test_create_several_on_same_line_in_creation_order(db_session, mentor, mentor2, sub10):
    """[Л FR-007] [Л FR-010] LC-03, LC-21: несколько комментариев к строке, в т.ч. разных менторов."""
    from app.services.line_comments import create_line_comment, list_line_comments

    for i in range(5):
        create_line_comment(db_session, mentor if i % 2 == 0 else mentor2, sub10.id, "3", f"t{i}")
    views = list_line_comments(db_session, mentor, sub10.id)
    assert [v.text for v in views] == [f"t{i}" for i in range(5)]
    assert {v.author for v in views} == {"Ментор", "Ментор Два"}


@pytest.mark.parametrize("line", ["1", str(N)])
def test_create_boundary_lines_ok(db_session, mentor, sub10, line):
    """[Л FR-003] LC-15: допустимые 1 и N (последняя строка)."""
    from app.services.line_comments import create_line_comment

    assert create_line_comment(db_session, mentor, sub10.id, line, "t").line == int(line)


def test_create_on_empty_code_line_ok(db_session, mentor, student, assignment, make_submission):
    """[Л FR-003] LC-04, LC-15: пустая строка кода - тоже строка."""
    from app.services.line_comments import create_line_comment

    sub = make_submission(assignment, student, code="a\n\nb")
    assert create_line_comment(db_session, mentor, sub.id, "2", "t").line == 2


def test_create_text_stored_without_sanitizing(db_session, mentor, sub10):
    """[Л FR-013] LC-06: только strip и \\r\\n -> \\n, разметка не трогается."""
    from app.services.line_comments import create_line_comment

    c = create_line_comment(db_session, mentor, sub10.id, "1", " <b>x</b>\r\n& y ")
    assert c.text == "<b>x</b>\n& y"


LINE_REJECTED = [
    "", "0", "-1", "05", " 5", "+5", "5.0", "1e1", "1_000", "٣", "²", str(N + 1),
    "9223372036854775808", "9" * 5000, "5\n", "5 ",
]


@pytest.mark.parametrize("line", LINE_REJECTED, ids=lambda v: repr(v)[:30])
def test_create_rejects_bad_line(db_session, mentor, sub10, line):
    """[Л FR-005] LC-15, LC-14, LC-25: таблица разбора номера - ValidationError(line), записи нет."""
    from app.services.errors import ValidationError
    from app.services.line_comments import create_line_comment

    with pytest.raises(ValidationError) as exc:
        create_line_comment(db_session, mentor, sub10.id, line, "текст")
    assert set(exc.value.errors) == {"line"}
    assert exc.value.errors["line"] == f"Номер строки: целое от 1 до {N}"
    assert count_comments(db_session) == 0


def test_create_no_lines_message(db_session, mentor, student, assignment, make_submission):
    """[Л FR-005] LC-14: у кода без строк сообщение «В коде нет строк»."""
    from app.services.errors import ValidationError
    from app.services.line_comments import create_line_comment

    sub = make_submission(assignment, student, code="")
    with pytest.raises(ValidationError) as exc:
        create_line_comment(db_session, mentor, sub.id, "1", "t")
    assert exc.value.errors["line"] == "В коде нет строк"
    assert count_comments(db_session) == 0


@pytest.mark.parametrize("text", ["", "   ", "\n\t ", "x" * 2001])
def test_create_rejects_bad_text(db_session, mentor, sub10, text):
    """[Л FR-006] LC-06, LC-14: пустой/слишком длинный текст - ValidationError(text), метка поля."""
    from app.services.errors import ValidationError
    from app.services.line_comments import create_line_comment

    with pytest.raises(ValidationError) as exc:
        create_line_comment(db_session, mentor, sub10.id, "1", text)
    assert set(exc.value.errors) == {"text"}
    assert exc.value.errors["text"].startswith("Комментарий к строке:")
    assert count_comments(db_session) == 0


def test_create_text_length_boundary(db_session, mentor, sub10):
    """[Л FR-006] LC-06: ровно 2000 символов (и 2000 + пробелы) проходит."""
    from app.services.line_comments import create_line_comment

    assert len(create_line_comment(db_session, mentor, sub10.id, "1", "x" * 2000).text) == 2000
    assert len(create_line_comment(db_session, mentor, sub10.id, "1", "x" * 2000 + "   ").text) == 2000


def test_create_both_fields_invalid_single_error(db_session, mentor, sub10):
    """[Л FR-005] [Л FR-006] LC-08, LC-14: оба поля неверны - одно ValidationError с обоими ключами."""
    from app.services.errors import ValidationError
    from app.services.line_comments import create_line_comment

    with pytest.raises(ValidationError) as exc:
        create_line_comment(db_session, mentor, sub10.id, "0", "")
    assert set(exc.value.errors) == {"line", "text"}
    assert count_comments(db_session) == 0


@pytest.mark.parametrize("line, text", [("3", "ok"), ("0", ""), ("abc", "ok")])
def test_create_student_forbidden_any_input(db_session, student, sub10, line, text):
    """[Л FR-004] [Л FR-012] LC-08, LC-14: ученик (автор) - Forbidden при любом вводе."""
    from app.services.errors import Forbidden
    from app.services.line_comments import create_line_comment

    with pytest.raises(Forbidden):
        create_line_comment(db_session, student, sub10.id, line, text)
    assert count_comments(db_session) == 0


def test_create_student_forbidden_for_missing_submission(db_session, student):
    """[Л FR-012] LC-08: роль проверяется раньше сдачи - Forbidden, а не NotFound."""
    from app.services.errors import Forbidden
    from app.services.line_comments import create_line_comment

    with pytest.raises(Forbidden):
        create_line_comment(db_session, student, 999999, "1", "t")


@pytest.mark.parametrize("sid", [999999, 2**63, 0, -1])
def test_create_missing_submission_not_found_before_validation(db_session, mentor, sid):
    """[Л FR-011] [Л FR-012] LC-08: NotFound раньше валидации (невалидный ввод не даёт 400)."""
    from app.services.errors import NotFound
    from app.services.line_comments import create_line_comment

    with pytest.raises(NotFound):
        create_line_comment(db_session, mentor, sid, "0", "")


def test_create_raises_only_known_errors(db_session, mentor, student, sub10):
    """[Л FR-019] LC-07: только NotFound, Forbidden, ValidationError."""
    from app.services.errors import Forbidden, NotFound, ValidationError
    from app.services.line_comments import create_line_comment

    cases = [(mentor, 999999, "1", "t"), (student, sub10.id, "1", "t"), (mentor, sub10.id, "x", "t")]
    for user, sid, line, text in cases:
        with pytest.raises((Forbidden, NotFound, ValidationError)):
            create_line_comment(db_session, user, sid, line, text)


@pytest.mark.parametrize("status", ["pending", "accepted", "changes_requested"])
def test_create_any_status_no_side_effects(
    db_session, mentor, student, assignment, make_submission, status
):
    """[Л FR-014] [Л FR-015] [Л FR-016] LC-08, LC-23: статус, ревью и попытки не меняются."""
    from app.models import Review
    from app.services.line_comments import create_line_comment
    from app.services.reviews import pending_queue

    sub = make_submission(assignment, student, status=status, code=numbered_code(3))
    if status != "pending":
        sub.review = Review(mentor_id=mentor.id, verdict=status, comment="ok")
        db_session.commit()
    queue_before = [s.id for s in pending_queue(db_session, mentor)]
    create_line_comment(db_session, mentor, sub.id, "2", "t")
    db_session.refresh(sub)
    assert sub.status == status
    assert (sub.review is not None) == (status != "pending")
    assert sub.attempt == 1
    assert [s.id for s in pending_queue(db_session, mentor)] == queue_before
    assert count_comments(db_session) == 1


# --- маршрут -------------------------------------------------------------


def test_route_success_redirect(mentor, sub10, make_client, db_session):
    """[Л FR-018] LC-09, LC-10: 303 на /submissions/{id}#L{n}, комментарий создан."""
    resp = post_comment(make_client(mentor), sub10.id, "4", "t")
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/submissions/{sub10.id}#L4"
    assert count_comments(db_session) == 1


def test_route_redirect_keeps_valid_filter(mentor, sub10, assignment, make_client):
    """[Л FR-018] LC-10, LC-13: валидный assignment_id попадает в Location."""
    resp = post_comment(make_client(mentor), sub10.id, "2", "t", assignment_id=str(assignment.id))
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/submissions/{sub10.id}?assignment_id={assignment.id}#L2"


@pytest.mark.parametrize(
    "raw", ["abc", "//evil.example", "99999999999999999999", "", "999999", "0", "-1"]
)
def test_route_redirect_drops_garbage_filter(mentor, sub10, make_client, raw):
    """[Л FR-018] LC-10, LC-13: мусорный фильтр молча отбрасывается, сырой ввод не в Location."""
    resp = post_comment(make_client(mentor), sub10.id, "2", "t", assignment_id=raw)
    assert resp.status_code == 303
    assert resp.headers["location"] == f"/submissions/{sub10.id}#L2"
    assert "evil" not in resp.headers["location"]


@pytest.mark.parametrize(
    "line, text, keys",
    [("0", "текст", {"line"}), ("2", "   ", {"text"}), ("abc", "", {"line", "text"})],
)
def test_route_400_page_with_errors_and_input(
    mentor, sub10, assignment, make_client, db_session, line, text, keys
):
    """[Л FR-005] [Л FR-006] [Л FR-018] LC-14, LC-16, LC-25: 400, страница сдачи, ошибки, ввод и фильтр."""
    resp = post_comment(make_client(mentor), sub10.id, line, text, assignment_id=str(assignment.id))
    assert resp.status_code == 400
    assert resp.context["submission"].id == sub10.id
    assert set(resp.context["line_comment_errors"]) == keys
    assert resp.context["line_comment_form"] == {"line": line, "text": text}
    assert resp.context["queue_filter"].id == assignment.id
    assert CONTEXT_KEYS <= set(resp.context.keys())
    assert count_comments(db_session) == 0


def test_route_400_garbage_filter_dropped(mentor, sub10, make_client):
    """[Л FR-018] LC-13: при 400 мусорный assignment_id даёт queue_filter None."""
    resp = post_comment(make_client(mentor), sub10.id, "0", "t", assignment_id="//evil.example")
    assert resp.status_code == 400
    assert resp.context["submission"].id == sub10.id
    assert resp.context["queue_filter"] is None


@pytest.mark.parametrize("line, text", [("3", "ok"), ("0", ""), ("abc", "t")])
def test_route_student_forbidden(student, sub10, make_client, db_session, line, text):
    """[Л FR-004] [Л FR-012] LC-14: ученик - 403 «Доступ запрещён» при любом вводе."""
    resp = post_comment(make_client(student), sub10.id, line, text)
    assert resp.status_code == 403
    assert resp.context["title"] == "Доступ запрещён"
    assert count_comments(db_session) == 0


def test_route_student_forbidden_for_missing_id(student, make_client):
    """[Л FR-012] LC-14: ученик с несуществующим id - тоже 403."""
    resp = post_comment(make_client(student), 999999, "1", "t")
    assert resp.status_code == 403


@pytest.mark.parametrize("sid", ["999999", "9223372036854775808", "abc"])
def test_route_not_found_variants(mentor, make_client, db_session, sid):
    """[Л FR-011] LC-14, LC-17: нет сдачи / вне INTEGER / не число - 404 «Не найдено» (текст не проверяется)."""
    resp = post_comment(make_client(mentor), sid, "1", "текст")
    assert resp.status_code == 404
    assert resp.context["title"] == "Не найдено"
    assert count_comments(db_session) == 0


def test_route_get_not_a_page(mentor, sub10, make_client):
    """[Л FR-018] LC-09: GET на маршрут создания не отдаёт страницу (404 или 405)."""
    resp = make_client(mentor).get(f"/submissions/{sub10.id}/line-comments")
    assert resp.status_code in (404, 405)


# --- Phase 5: US3 --------------------------------------------------------


def test_two_mentors_see_each_other_via_route(
    db_session, mentor, mentor2, sub10, make_client
):
    """[Л FR-007] [Л FR-010] LC-21: два ментора комментируют одну строку и видят оба комментария."""
    c1, c2 = make_client(mentor), make_client(mentor2)
    assert post_comment(c1, sub10.id, "5", "от первого").status_code == 303
    assert post_comment(c2, sub10.id, "5", "от второго").status_code == 303
    for c in (c1, c2):
        views = c.get(f"/submissions/{sub10.id}").context["line_comments"]
        assert [(v.line, v.text, v.author) for v in views] == [
            (5, "от первого", "Ментор"),
            (5, "от второго", "Ментор Два"),
        ]


def test_anonymous_redirected_to_login(sub10, client, db_session):
    """[Л FR-012] LC-14: без сессии POST и GET - 303 на /login, комментарий не создан."""
    for resp in (
        post_comment(client, sub10.id, "1", "t"),
        client.get(f"/submissions/{sub10.id}", follow_redirects=False),
    ):
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login"
    assert count_comments(db_session) == 0


def test_student_sees_comment_immediately_in_pending(
    student, other_student, sub10, mentor, make_client
):
    """[Л FR-009] [Л FR-017] LC-19, LC-24: автор видит комментарий у pending-сдачи, чужой ученик - 404."""
    assert sub10.status == "pending"
    assert post_comment(make_client(mentor), sub10.id, "2", "сразу").status_code == 303
    views = make_client(student).get(f"/submissions/{sub10.id}").context["line_comments"]
    assert [v.text for v in views] == ["сразу"]
    assert make_client(other_student).get(f"/submissions/{sub10.id}").status_code == 404


# --- Phase 6: регрессия и трассировка ------------------------------------


def test_baseline_review_unchanged_with_comments(
    db_session, mentor, student, assignment, make_submission, make_client
):
    """[Л FR-001] [Л FR-015] LC-22, LC-23: ревью, повторное ревью, очередь и новые попытки как раньше."""
    from app.services.line_comments import list_line_comments

    sub = make_submission(assignment, student, code=numbered_code(3))
    other = make_submission(assignment, student, status="changes_requested", code="x")
    mc = make_client(mentor)
    assert post_comment(mc, sub.id, "1", "до ревью").status_code == 303
    assert mc.get("/review").context["queue"][0].id == sub.id
    resp = mc.post(
        f"/submissions/{sub.id}/review",
        data={"verdict": "accepted", "comment": "ок"},
        follow_redirects=False,
    )
    assert resp.status_code == 303 and resp.headers["location"] == "/review"
    db_session.refresh(sub)
    assert sub.status == "accepted"
    again = mc.post(f"/submissions/{sub.id}/review", data={"verdict": "accepted", "comment": "ещё"})
    assert again.status_code == 409
    assert post_comment(mc, sub.id, "2", "после ревью").status_code == 303
    assert [v.text for v in list_line_comments(db_session, mentor, sub.id)] == ["до ревью", "после ревью"]
    # другая попытка (отдельная Submission) комментариев не наследует
    assert list_line_comments(db_session, mentor, other.id) == []


def test_every_test_has_traceable_docstring():
    """[Л FR-001] [Л FR-019] LC-29, SC-006: каждый тест ссылается на [Л FR-nnn] и LC-NN; покрыты FR-001..019."""
    import ast
    import re
    from pathlib import Path

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    seen = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            doc = ast.get_docstring(node) or ""
            assert doc.startswith("[Л FR-"), node.name
            assert re.search(r"\bLC-\d\d\b", doc), node.name
            seen |= set(re.findall(r"\[Л FR-(\d{3})\]", doc))
    assert seen == {f"{i:03d}" for i in range(1, 20)}
