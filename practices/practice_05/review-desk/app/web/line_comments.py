from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services import line_comments as line_comment_service
from app.services import reviews as review_service
from app.services import submissions as submission_service
from app.services.errors import ValidationError
from app.web.deps import require_mentor
from app.web.submissions import render_submission

router = APIRouter()


@router.post("/submissions/{submission_id}/line-comments")
def create_line_comment(
    submission_id: int,
    request: Request,
    line: str = Form(""),
    text: str = Form(""),
    assignment_id: str | None = Form(None),
    user: User = Depends(require_mentor),
    db: Session = Depends(get_db),
):
    queue_filter = review_service.queue_filter_or_none(db, assignment_id)
    try:
        comment = line_comment_service.create_line_comment(db, user, submission_id, line, text)
    except ValidationError as exc:
        submission = submission_service.get_submission_for(db, user, submission_id)
        return render_submission(
            request,
            user,
            submission,
            status_code=400,
            queue_filter=queue_filter,
            db=db,
            line_comment_errors=exc.errors,
            line_comment_form={"line": line, "text": text},
        )
    query = "" if queue_filter is None else f"?assignment_id={queue_filter.id}"
    return RedirectResponse(f"/submissions/{submission_id}{query}#L{comment.line}", status_code=303)
