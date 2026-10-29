from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ROLE_MENTOR, Assignment, User
from app.services.auth import ensure_role
from app.services.errors import NotFound, ValidationError
from app.services.validation import clean_text

TITLE_MAX = 200
DESCRIPTION_MAX = 10_000


def list_assignments(db: Session) -> list[Assignment]:
    stmt = select(Assignment).order_by(Assignment.created_at.desc(), Assignment.id.desc())
    return list(db.scalars(stmt))


def get_assignment(db: Session, assignment_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if assignment is None:
        raise NotFound("Задача не найдена")
    return assignment


def ensure_can_create(user: User) -> None:
    ensure_role(user, ROLE_MENTOR)


def create_assignment(db: Session, author: User, title: str, description: str) -> Assignment:
    ensure_can_create(author)

    title, title_error = clean_text(title, TITLE_MAX, "Название")
    description, description_error = clean_text(description, DESCRIPTION_MAX, "Описание")
    errors = {}
    if title_error:
        errors["title"] = title_error
    if description_error:
        errors["description"] = description_error
    if errors:
        raise ValidationError(errors)

    assignment = Assignment(title=title, description=description, author_id=author.id)
    db.add(assignment)
    db.commit()
    return assignment
