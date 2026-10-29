from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_STUDENT, User
from app.services import assignments as assignment_service
from app.services import submissions as submission_service
from app.services.errors import ValidationError
from app.web.deps import current_user, require_mentor
from app.web.templating import templates

router = APIRouter()


@router.get("/assignments")
def assignment_list(
    request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    context = {"user": user, "assignments": assignment_service.list_assignments(db)}
    if user.role == ROLE_STUDENT:
        context["statuses"] = submission_service.latest_statuses(db, user)
    return templates.TemplateResponse(request, "assignments/list.html", context)


def render_new_form(request, user, title="", description="", errors=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "assignments/new.html",
        {"user": user, "title": title, "description": description, "errors": errors or {}},
        status_code=status_code,
    )


@router.get("/assignments/new")
def new_assignment_form(request: Request, user: User = Depends(require_mentor)):
    return render_new_form(request, user)


@router.post("/assignments/new")
def create_assignment(
    request: Request,
    title: str = Form(""),
    description: str = Form(""),
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    try:
        assignment = assignment_service.create_assignment(db, user, title, description)
    except ValidationError as exc:
        return render_new_form(request, user, title, description, exc.errors, status_code=400)
    return RedirectResponse(f"/assignments/{assignment.id}", status_code=303)


@router.get("/assignments/{assignment_id}")
def assignment_detail(
    assignment_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    assignment = assignment_service.get_assignment(db, assignment_id)
    return render_detail(request, db, user, assignment)


def render_detail(
    request, db, user, assignment, code="", errors=None, message=None, status_code=200
):
    context = {"user": user, "assignment": assignment}
    if user.role == ROLE_STUDENT:
        context.update(
            attempts=submission_service.list_attempts(db, assignment, user),
            block_reason=submission_service.submit_block_reason(db, assignment, user),
            code=code,
            errors=errors or {},
            message=message,
        )
    return templates.TemplateResponse(
        request, "assignments/detail.html", context, status_code=status_code
    )
