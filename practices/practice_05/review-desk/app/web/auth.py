from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import auth
from app.web.deps import SESSION_USER_KEY
from app.web.templating import templates

router = APIRouter()

LOGIN_ERROR = "Неверный логин или пароль"


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"username": "", "error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = auth.authenticate(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request, "login.html", {"username": username, "error": LOGIN_ERROR}
        )
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    return RedirectResponse("/assignments", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
