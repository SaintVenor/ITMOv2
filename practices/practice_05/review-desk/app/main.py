from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import STATIC_DIR, get_secret_key
from app.db import init_db
from app.services.errors import Conflict, Forbidden, NotFound, ServiceError, ValidationError
from app.web import assignments, auth, review, submissions
from app.web.deps import SESSION_USER_KEY, LoginRequired
from app.web.templating import templates

PUBLIC_PATHS = {"/login"}
PUBLIC_PREFIXES = ("/static/",)

ERROR_STATUS = {
    NotFound: (404, "Не найдено"),
    Forbidden: (403, "Доступ запрещён"),
    Conflict: (409, "Конфликт"),
    ValidationError: (400, "Некорректные данные"),
}


async def require_session(request: Request, call_next):
    """US-1 AC3: всё, кроме /login (и статики), требует сессии."""
    path = request.url.path
    is_public = path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)
    if not is_public and SESSION_USER_KEY not in request.session:
        return RedirectResponse("/login", status_code=303)
    return await call_next(request)


def render_error(request: Request, status: int, title: str, message: str = ""):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"title": title, "message": message, "status": status},
        status_code=status,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Review Desk", docs_url=None, redoc_url=None, openapi_url=None)

    # Порядок важен: последний добавленный middleware — внешний,
    # поэтому сессия уже разобрана, когда до неё доходит require_session.
    app.add_middleware(BaseHTTPMiddleware, dispatch=require_session)
    app.add_middleware(SessionMiddleware, secret_key=get_secret_key(), same_site="lax")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return RedirectResponse("/assignments", status_code=303)

    app.include_router(auth.router)
    app.include_router(assignments.router)
    app.include_router(submissions.router)
    app.include_router(review.router)

    @app.exception_handler(LoginRequired)
    async def handle_login_required(request: Request, exc: LoginRequired):
        return RedirectResponse("/login", status_code=303)

    @app.exception_handler(ServiceError)
    async def handle_service_error(request: Request, exc: ServiceError):
        status, title = ERROR_STATUS.get(type(exc), (400, "Ошибка"))
        return render_error(request, status, title, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_bad_path(request: Request, exc: RequestValidationError):
        # Формы читаются с дефолтами, так что сюда попадают только кривые
        # параметры пути вроде /assignments/abc — для пользователя это 404.
        return render_error(request, 404, "Не найдено")

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        title = {404: "Не найдено", 405: "Метод не поддерживается"}.get(exc.status_code, "Ошибка")
        return render_error(request, exc.status_code, title)

    return app


def _create_production_app() -> FastAPI:
    init_db()
    return create_app()


app = _create_production_app()
