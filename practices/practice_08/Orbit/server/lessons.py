import json
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .db import connect
from .entries import calendar_date, invalid

router = APIRouter(prefix="/api/lessons")

ClockTime = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]


class LessonFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    weekday: int = Field(ge=1, le=7, strict=True)
    subject: str = Field(min_length=1, max_length=120)
    room: str = Field(min_length=1, max_length=80)
    startTime: ClockTime
    endTime: ClockTime
    termStart: str
    termEnd: str
    weekInterval: Literal[1, 2] = 1
    firstDate: str | None = None
    lessonType: Literal["lecture", "practice", "lab", "consultation"] | None = None


class CreateLesson(LessonFields):
    id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]


def validate_lesson(fields):
    start = calendar_date(fields.termStart, "termStart")
    end = calendar_date(fields.termEnd, "termEnd")
    if end < start:
        invalid("termEnd", "Конец семестра раньше начала.")
    if (fields.weekday - start.isoweekday()) % 7 > (end - start).days:
        invalid("termEnd", "В этом периоде нет выбранного дня недели.")
    if fields.firstDate is not None:
        first = calendar_date(fields.firstDate, "firstDate")
        if not start <= first <= end or first.isoweekday() != fields.weekday:
            invalid("firstDate", "Первая пара должна быть в семестре и выпадать на выбранный день недели.")
    if fields.endTime <= fields.startTime:
        invalid("endTime", "Окончание пары должно быть позже начала.")


def read_lesson(db, lesson_id):
    row = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Пара не найдена.")
    return dict(row)


@router.get("")
def list_lessons(start_raw: str = Query(alias="from"), end_raw: str = Query(alias="to")):
    start = calendar_date(start_raw, "from", "query")
    end = calendar_date(end_raw, "to", "query")
    if end < start:
        invalid("to", "Окончание раньше начала.", "query")
    with connect() as db:
        rows = db.execute(
            """SELECT * FROM lessons WHERE termStart <= ? AND termEnd >= ?
               AND (id NOT GLOB 'demo-lesson-*'
                    OR NOT EXISTS (SELECT 1 FROM lessons WHERE id GLOB 'itmo-202611*'))
               ORDER BY startTime, endTime, subject, id""",
            (end_raw, start_raw),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@router.post("", status_code=201)
def create_lesson(fields: CreateLesson):
    validate_lesson(fields)
    data = fields.model_dump()
    replay_data = {key: value for key, value in data.items() if (key, value) not in (("weekInterval", 1), ("firstDate", None), ("lessonType", None))}
    payload = json.dumps(replay_data, sort_keys=True)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        operation = db.execute(
            "SELECT payload FROM lesson_operations WHERE id = ?", (fields.id,),
        ).fetchone()
        if operation:
            if operation["payload"] != payload:
                raise HTTPException(409, "Этот идентификатор уже использован для другой пары.")
            return read_lesson(db, fields.id)
        if db.execute("SELECT 1 FROM lessons WHERE id = ?", (fields.id,)).fetchone():
            raise HTTPException(409, "Этот идентификатор уже занят.")

        db.execute(
            """INSERT INTO lessons (id, weekday, subject, room, startTime, endTime, termStart, termEnd, weekInterval, firstDate, lessonType)
               VALUES (:id, :weekday, :subject, :room, :startTime, :endTime, :termStart, :termEnd, :weekInterval, :firstDate, :lessonType)""",
            data,
        )
        db.execute("INSERT INTO lesson_operations (id, payload) VALUES (?, ?)", (fields.id, payload))
        return read_lesson(db, fields.id)


@router.put("/{lesson_id}")
def update_lesson(lesson_id: str, fields: LessonFields):
    validate_lesson(fields)
    with connect() as db:
        result = db.execute(
            """UPDATE lessons SET weekday=:weekday, subject=:subject, room=:room,
               startTime=:startTime, endTime=:endTime, termStart=:termStart, termEnd=:termEnd,
               weekInterval=:weekInterval, firstDate=:firstDate, lessonType=:lessonType
               WHERE id=:id""",
            {**fields.model_dump(), "id": lesson_id},
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Пара не найдена.")
        return read_lesson(db, lesson_id)


@router.delete("/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: str):
    with connect() as db:
        result = db.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Пара не найдена.")
    return Response(status_code=204)
