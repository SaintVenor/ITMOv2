import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ROLE_MENTOR, STATUS_PENDING, VERDICTS, Assignment, Review, Submission, User
from app.services.assignments import get_assignment
from app.services.auth import ensure_role
from app.services.errors import Conflict, NotFound, ValidationError
from app.services.validation import SQLITE_INT_MAX, clean_text, fits_sqlite_int

COMMENT_MAX = 5_000

ALREADY_REVIEWED = "У этой сдачи уже есть ревью."
ASSIGNMENT_NOT_FOUND = "Задача не найдена"

# Явный [0-9], а не \d: \d в Python совпадает и с "٥".
_CANONICAL_ID = re.compile(r"[1-9][0-9]*", re.ASCII)


def parse_assignment_filter(raw: str | None) -> int | None:
    """None/"" -> None; каноничное целое <= 2^63-1 -> int; иначе NotFound."""
    if raw is None or raw == "":
        return None
    if not _CANONICAL_ID.fullmatch(raw):
        raise NotFound(ASSIGNMENT_NOT_FOUND)
    value = int(raw)
    if value > SQLITE_INT_MAX:
        raise NotFound(ASSIGNMENT_NOT_FOUND)
    return value


def get_queue_filter(db: Session, raw: str | None) -> Assignment | None:
    """Строго: None/"" -> None; невалидно или нет задачи -> NotFound."""
    assignment_id = parse_assignment_filter(raw)
    if assignment_id is None:
        return None
    return get_assignment(db, assignment_id)


def queue_filter_or_none(db: Session, raw: str | None) -> Assignment | None:
    """Мягко: как get_queue_filter, но невалидный фильтр просто отбрасывается."""
    try:
        return get_queue_filter(db, raw)
    except NotFound:
        return None


def pending_queue(
    db: Session, mentor: User, assignment: Assignment | None = None
) -> list[Submission]:
    ensure_role(mentor, ROLE_MENTOR)
    stmt = select(Submission).where(Submission.status == STATUS_PENDING)
    if assignment is not None:
        stmt = stmt.where(Submission.assignment_id == assignment.id)
    stmt = stmt.order_by(Submission.created_at.asc(), Submission.id.asc())
    return list(db.scalars(stmt))


def can_review(user: User, submission: Submission) -> bool:
    return user.role == ROLE_MENTOR and submission.review is None


def create_review(
    db: Session, mentor: User, submission_id: int, verdict: str, comment: str
) -> Review:
    ensure_role(mentor, ROLE_MENTOR)
    submission = db.get(Submission, submission_id) if fits_sqlite_int(submission_id) else None
    if submission is None:
        raise NotFound("Сдача не найдена")
    if submission.review is not None:
        raise Conflict(ALREADY_REVIEWED)

    errors = {}
    if verdict not in VERDICTS:
        errors["verdict"] = "Выберите вердикт: принять или вернуть на доработку"
    comment, comment_error = clean_text(comment, COMMENT_MAX, "Комментарий")
    if comment_error:
        errors["comment"] = comment_error
    if errors:
        raise ValidationError(errors)

    review = Review(mentor_id=mentor.id, verdict=verdict, comment=comment)
    submission.review = review
    submission.status = verdict
    try:
        db.commit()
    except IntegrityError:
        # Другой запрос успел оставить ревью первым.
        db.rollback()
        raise Conflict(ALREADY_REVIEWED) from None
    return review
