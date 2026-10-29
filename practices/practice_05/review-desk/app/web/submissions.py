from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services import assignments as assignment_service
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


def render_submission(request, user, submission, verdict="", comment="", errors=None, status_code=200):
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
        },
        status_code=status_code,
    )


@router.get("/submissions/{submission_id}")
def submission_detail(
    submission_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    submission = submission_service.get_submission_for(db, user, submission_id)
    return render_submission(request, user, submission)
