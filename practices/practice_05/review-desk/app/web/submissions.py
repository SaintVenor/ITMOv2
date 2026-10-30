from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_MENTOR, Assignment, User
from app.services import assignments as assignment_service
from app.services import line_comments as line_comment_service
from app.services import reviews as review_service
from app.services import submissions as submission_service
from app.services.errors import Conflict, ValidationError
from app.web.assignments import render_detail
from app.web.deps import current_user, require_student
from app.web.templating import templates

router = APIRouter()


@router.post("/assignments/{assignment_id}/submissions")
def create_submission(
    assignment_id: int,
    request: Request,
    code: str = Form(""),
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    try:
        submission_service.create_submission(db, user, assignment_id, code)
    except ValidationError as exc:
        assignment = assignment_service.get_assignment(db, assignment_id)
        return render_detail(request, db, user, assignment, code, exc.errors, status_code=400)
    except Conflict as exc:
        assignment = assignment_service.get_assignment(db, assignment_id)
        return render_detail(request, db, user, assignment, message=exc.message, status_code=409)
    return RedirectResponse(f"/assignments/{assignment_id}", status_code=303)


def review_queue_url(assignment: Assignment | None) -> str:
    """URL очереди только из id проверенной задачи: сырой ввод сюда не попадает."""
    return "/review" if assignment is None else f"/review?assignment_id={assignment.id}"


def render_submission(
    request,
    user,
    submission,
    verdict="",
    comment="",
    errors=None,
    status_code=200,
    queue_filter: Assignment | None = None,
    *,
    db,
    line_comment_errors=None,
    line_comment_form=None,
):
    code_lines = line_comment_service.split_code_lines(submission.code)
    return templates.TemplateResponse(
        request,
        "submissions/detail.html",
        {
            "user": user,
            "submission": submission,
            "can_review": review_service.can_review(user, submission),
            "verdict": verdict,
            "comment": comment,
            "errors": errors or {},
            "queue_filter": queue_filter,
            "queue_url": review_queue_url(queue_filter),
            "line_comments": line_comment_service.list_line_comments(db, user, submission.id),
            "code_lines": code_lines,
            "line_count": len(code_lines),
            "can_comment": line_comment_service.can_comment(user, submission),
            "line_comment_errors": line_comment_errors or {},
            "line_comment_form": line_comment_form or {},
            "line_comment_max": line_comment_service.LINE_COMMENT_MAX,
        },
        status_code=status_code,
    )


@router.get("/submissions/{submission_id}")
def submission_detail(
    submission_id: int,
    request: Request,
    assignment_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    submission = submission_service.get_submission_for(db, user, submission_id)
    queue_filter = None
    if user.role == ROLE_MENTOR:
        queue_filter = review_service.queue_filter_or_none(db, assignment_id)
    return render_submission(request, user, submission, queue_filter=queue_filter, db=db)
