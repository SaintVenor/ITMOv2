from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ROLE_MENTOR, STATUS_PENDING, VERDICTS, Review, Submission, User
from app.services.auth import ensure_role
from app.services.errors import Conflict, NotFound, ValidationError
from app.services.validation import clean_text

COMMENT_MAX = 5_000

ALREADY_REVIEWED = "У этой сдачи уже есть ревью."


def pending_queue(db: Session, mentor: User) -> list[Submission]:
    ensure_role(mentor, ROLE_MENTOR)
    stmt = (
        select(Submission)
        .where(Submission.status == STATUS_PENDING)
        .order_by(Submission.created_at.asc(), Submission.id.asc())
    )
    return list(db.scalars(stmt))


def can_review(user: User, submission: Submission) -> bool:
    return user.role == ROLE_MENTOR and submission.review is None


def create_review(
    db: Session, mentor: User, submission_id: int, verdict: str, comment: str
) -> Review:
    ensure_role(mentor, ROLE_MENTOR)
    submission = db.get(Submission, submission_id)
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
