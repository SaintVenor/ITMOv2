from datetime import datetime, timezone

from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR

STATUS_LABELS = {
    "pending": "Ждёт ревью",
    "accepted": "Принято",
    "changes_requested": "На доработку",
}


def format_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.filters["dt"] = format_dt
templates.env.globals["STATUS_LABELS"] = STATUS_LABELS
