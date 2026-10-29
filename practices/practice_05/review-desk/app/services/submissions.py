from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ROLE_MENTOR,
    ROLE_STUDENT,
    STATUS_ACCEPTED,
    STATUS_PENDING,
    Assignment,
    Submission,
    User,
)
from app.services.assignments import get_assignment
from app.services.auth import ensure_role
from app.services.errors import Conflict, NotFound, ValidationError
from app.services.validation import clean_text

CODE_MAX = 100_000

BLOCKED_PENDING = "Предыдущая попытка ждёт ревью — новую можно сдать после проверки."
BLOCKED_ACCEPTED = "Задача уже принята — новые попытки по ней не нужны."


def list_attempts(db: Session, assignment: Assignment, student: User) -> list[Submission]:
    stmt = (
        select(Submission)
        .where(Submission.assignment_id == assignment.id, Submission.student_id == student.id)
        .order_by(Submission.attempt.desc())
    )
    return list(db.scalars(stmt))


def submit_block_reason(db: Session, assignment: Assignment, student: User) -> str | None:
    """Почему ученик сейчас не может сдать новую попытку (или None, если может)."""
    statuses = set(
        db.scalars(
            select(Submission.status).where(
                Submission.assignment_id == assignment.id,
                Submission.student_id == student.id,
                Submission.status.in_((STATUS_PENDING, STATUS_ACCEPTED)),
            )
        )
    )
    if STATUS_ACCEPTED in statuses:
        return BLOCKED_ACCEPTED
    if STATUS_PENDING in statuses:
        return BLOCKED_PENDING
    return None


def latest_statuses(db: Session, student: User) -> dict[int, str]:
    """Статус последней попытки ученика по каждой задаче: {assignment_id: status}."""
    latest = (
        select(Submission.assignment_id, func.max(Submission.attempt).label("attempt"))
        .where(Submission.student_id == student.id)
        .group_by(Submission.assignment_id)
        .subquery()
    )
    stmt = select(Submission.assignment_id, Submission.status).join(
        latest,
        (Submission.assignment_id == latest.c.assignment_id)
        & (Submission.attempt == latest.c.attempt),
    ).where(Submission.student_id == student.id)
    return {assignment_id: status for assignment_id, status in db.execute(stmt)}


def create_submission(db: Session, student: User, assignment_id: int, code: str) -> Submission:
    ensure_role(student, ROLE_STUDENT)
    assignment = get_assignment(db, assignment_id)

    reason = submit_block_reason(db, assignment, student)
    if reason:
        raise Conflict(reason)

    code, error = clean_text(code, CODE_MAX, "Код")
    if error:
        raise ValidationError({"code": error})

    last_attempt = db.scalar(
        select(func.max(Submission.attempt)).where(
            Submission.assignment_id == assignment.id, Submission.student_id == student.id
        )
    )
    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        attempt=(last_attempt or 0) + 1,
        code=code,
        status=STATUS_PENDING,
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        # Параллельная отправка заняла тот же номер попытки.
        db.rollback()
        raise Conflict(BLOCKED_PENDING) from None
    return submission


def get_submission_for(db: Session, user: User, submission_id: int) -> Submission:
    """Ментор видит любую сдачу, ученик — только свою.

    Чужая сдача для ученика неотличима от несуществующей (US-5 AC2).
    """
    submission = db.get(Submission, submission_id)
    if submission is None or (user.role != ROLE_MENTOR and submission.student_id != user.id):
        raise NotFound("Сдача не найдена")
    return submission
