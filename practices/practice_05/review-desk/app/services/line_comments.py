import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import ROLE_MENTOR, LineComment, Submission, User
from app.services.auth import ensure_role
from app.services.errors import NotFound, ValidationError
from app.services.submissions import get_submission_for
from app.services.validation import clean_text, fits_sqlite_int

LINE_COMMENT_MAX = 2_000

# Явный [0-9], а не \d: \d в Python совпадает и с "٣". fullmatch, а не $.
_CANONICAL_LINE = re.compile(r"[1-9][0-9]*", re.ASCII)
_LINE_MAX_DIGITS = 19  # длиннее 2^63-1 заведомо вне диапазона; защита int() от гигантских строк


@dataclass(frozen=True)
class LineCommentView:
    id: int
    line: int
    text: str
    author: str
    created_at: datetime


def split_code_lines(code: str) -> list[str]:
    """Единственное правило «строки кода» (LC-04): \\r\\n и \\r - перевод строки."""
    lines = code.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def line_count(submission) -> int:
    return len(split_code_lines(submission.code))


def can_comment(user: User, submission) -> bool:
    return user.role == ROLE_MENTOR


def list_line_comments(db: Session, user: User, submission_id: int) -> list[LineCommentView]:
    submission = get_submission_for(db, user, submission_id)
    stmt = (
        select(LineComment)
        .where(LineComment.submission_id == submission.id)
        .options(joinedload(LineComment.author))
        .order_by(LineComment.line, LineComment.created_at, LineComment.id)
    )
    return [
        LineCommentView(c.id, c.line, c.text, c.author.display_name, c.created_at)
        for c in db.scalars(stmt)
    ]


def _parse_line(raw: str, total: int) -> tuple[int | None, str | None]:
    error = f"Номер строки: целое от 1 до {total}" if total else "В коде нет строк"
    if not _CANONICAL_LINE.fullmatch(raw) or len(raw) > _LINE_MAX_DIGITS:
        return None, error
    number = int(raw)
    if not 1 <= number <= total:
        return None, error
    return number, None


def create_line_comment(
    db: Session, user: User, submission_id: int, line: str, text: str
) -> LineComment:
    ensure_role(user, ROLE_MENTOR)
    submission = db.get(Submission, submission_id) if fits_sqlite_int(submission_id) else None
    if submission is None:
        raise NotFound("Сдача не найдена")

    errors = {}
    number, line_error = _parse_line(line, line_count(submission))
    if line_error:
        errors["line"] = line_error
    text, text_error = clean_text(text, LINE_COMMENT_MAX, "Комментарий к строке")
    if text_error:
        errors["text"] = text_error
    if errors:
        raise ValidationError(errors)

    comment = LineComment(submission_id=submission.id, line=number, text=text, author_id=user.id)
    db.add(comment)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return comment
