import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ROLES, User
from app.services.errors import Conflict, Forbidden, ValidationError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_user(
    db: Session, username: str, password: str, role: str, display_name: str | None = None
) -> User:
    username = username.strip()
    errors = {}
    if not username:
        errors["username"] = "Логин не может быть пустым"
    if role not in ROLES:
        errors["role"] = f"Роль должна быть одной из: {', '.join(ROLES)}"
    if not password:
        errors["password"] = "Пароль не может быть пустым"
    if errors:
        raise ValidationError(errors)
    if db.scalar(select(User).where(User.username == username)) is not None:
        raise Conflict(f"Пользователь {username} уже существует")

    user = User(
        username=username,
        display_name=(display_name or "").strip() or username,
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def ensure_role(user: User, role: str) -> None:
    if user.role != role:
        raise Forbidden("Недостаточно прав")


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Возвращает пользователя или None, не уточняя, что именно неверно."""
    user = db.scalar(select(User).where(User.username == username.strip()))
    if user is None or not password or not verify_password(password, user.password_hash):
        return None
    return user
