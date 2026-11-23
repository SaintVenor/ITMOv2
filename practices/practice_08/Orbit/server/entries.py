from datetime import date
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field


class EntryFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["deadline", "event", "birthday"]
    title: str = Field(min_length=1, max_length=180)
    area: Literal["study", "personal"] = "personal"
    startDate: str | None = None
    endDate: str | None = None
    startTime: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    endTime: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    birthMonth: int | None = Field(None, ge=1, le=12, strict=True)
    birthDay: int | None = Field(None, ge=1, le=31, strict=True)
    frequency: Literal["daily", "weekly", "monthly", "yearly"] | None = None


class CreateEntry(EntryFields):
    id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]


def invalid(field, message, source="body"):
    raise HTTPException(422, detail=[{"loc": [source, field], "msg": message}])


def calendar_date(value, field, source="body"):
    try:
        result = date.fromisoformat(value)
    except (ValueError, TypeError):
        invalid(field, "Введите дату в формате ГГГГ-ММ-ДД.", source)
    if value != result.isoformat():
        invalid(field, "Введите дату в формате ГГГГ-ММ-ДД.", source)
    return result


def normalize(fields):
    values = fields.model_dump()
    if fields.kind == "birthday":
        if fields.birthMonth is None:
            invalid("birthMonth", "Укажите месяц.")
        try:
            date(2000, fields.birthMonth, fields.birthDay or 0)
        except ValueError:
            invalid("birthDay", "Укажите существующий день месяца.")
        return {
            **values, "startDate": None, "endDate": None, "frequency": None,
            "startTime": None, "endTime": None,
        }

    start = calendar_date(fields.startDate, "startDate")
    values.update(birthMonth=None, birthDay=None)
    if fields.kind == "deadline":
        return {**values, "endDate": start.isoformat(), "endTime": None}

    end = calendar_date(fields.endDate, "endDate")
    if end < start:
        invalid("endDate", "Окончание раньше начала.")
    if fields.startTime and not fields.endTime:
        invalid("endTime", "Укажите время окончания.")
    if fields.endTime and not fields.startTime:
        invalid("startTime", "Укажите время начала.")
    if start == end and fields.startTime and fields.endTime <= fields.startTime:
        invalid("endTime", "Время окончания должно быть позже начала.")
    return values
