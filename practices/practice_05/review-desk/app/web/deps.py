from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_MENTOR, ROLE_STUDENT, User
from app.services import auth

SESSION_USER_KEY = "user_id"


class LoginRequired(Exception):
    """Сессии нет или она указывает на несуществующего пользователя."""


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get(SESSION_USER_KEY)
    user = auth.get_user(db, user_id) if isinstance(user_id, int) else None
    if user is None:
        request.session.clear()
        raise LoginRequired()
    return user


def require_mentor(user: User = Depends(current_user)) -> User:
    auth.ensure_role(user, ROLE_MENTOR)
    return user


def require_student(user: User = Depends(current_user)) -> User:
    auth.ensure_role(user, ROLE_STUDENT)
    return user
