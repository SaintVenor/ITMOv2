from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services import reviews as review_service
from app.services import submissions as submission_service
from app.services.errors import ValidationError
from app.web.deps import require_mentor
from app.web.submissions import render_submission
from app.web.templating import templates

router = APIRouter()


@router.get("/review")
def review_queue(request: Request, user: User = Depends(require_mentor), db: Session = Depends(get_db)):
    queue = review_service.pending_queue(db, user)
    return templates.TemplateResponse(request, "review/queue.html", {"user": user, "queue": queue})


@router.post("/submissions/{submission_id}/review")
def create_review(
    submission_id: int,
    request: Request,
    verdict: str = Form(""),
    comment: str = Form(""),
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    try:
        review_service.create_review(db, user, submission_id, verdict, comment)
    except ValidationError as exc:
        submission = submission_service.get_submission_for(db, user, submission_id)
        return render_submission(
            request, user, submission, verdict, comment, exc.errors, status_code=400
        )
    return RedirectResponse("/review", status_code=303)
