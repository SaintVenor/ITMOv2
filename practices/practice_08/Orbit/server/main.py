import json
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import ValidationError

from .db import connect, initialize
from .lessons import router as lessons_router
from .plans import router as plans_router
from .recurrence import occurrences
from .entries import CreateEntry, EntryFields, calendar_date, invalid, normalize


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="Орбита", lifespan=lifespan)
app.include_router(plans_router)
app.include_router(lessons_router)


@app.get("/api/health")
def health():
    return {"ok": True}


ENTRY_SELECT = """SELECT e.*, s.frequency, s.active_from, s.active_until
                  FROM entries e LEFT JOIN entry_series s ON s.entry_id = e.id"""


def by_id(db, entry_id):
    item = db.execute(ENTRY_SELECT + " WHERE e.id = ?", (entry_id,)).fetchone()
    if item is None:
        raise HTTPException(404, "Запись не найдена.")
    return dict(item)


def entry_response(row):
    return {key: value for key, value in row.items() if key not in ("active_from", "active_until")}


def calendar_item(row, occurrence=None, end=None):
    result = {
        "id": row["id"],
        "kind": row["kind"],
        "title": row["title"],
        "area": row["area"],
        "startDate": occurrence or row["startDate"],
        "endDate": end or row["endDate"],
        "startTime": row["startTime"],
        "endTime": row["endTime"],
    }
    if occurrence:
        result.update(
            occurrenceDate=occurrence, frequency=row["frequency"] or "yearly",
            seriesStart=row["startDate"], seriesEnd=row["endDate"],
        )
    return result


@app.get("/api/calendar")
def calendar(start_raw: str = Query(alias="from"), end_raw: str = Query(alias="to")):
    start = calendar_date(start_raw, "from", "query")
    end = calendar_date(end_raw, "to", "query")
    if end < start:
        invalid("to", "Окончание раньше начала.", "query")

    with connect() as db:
        db.execute("BEGIN")
        entries = db.execute(
            ENTRY_SELECT + """ WHERE e.kind != 'birthday' AND s.frequency IS NULL
               AND e.startDate <= ? AND e.endDate >= ?""", (end_raw, start_raw),
        ).fetchall()
        repeating = db.execute(
            ENTRY_SELECT + " WHERE e.kind = 'birthday' OR (s.frequency IS NOT NULL AND e.startDate <= ?)",
            (end_raw,),
        ).fetchall()
        skipped = {
            (row["entry_id"], row["day"])
            for row in db.execute("SELECT entry_id, day FROM skipped_occurrences WHERE day <= ?", (end_raw,))
        }
        steps = db.execute(
            """SELECT s.id, s.title, p.area, s.scheduled_date, s.done,
                      p.id AS plan_id, p.title AS plan_title
               FROM steps s JOIN plans p ON p.id = s.plan_id
               WHERE s.scheduled_date BETWEEN ? AND ?""", (start_raw, end_raw),
        ).fetchall()

    items = [calendar_item(row) for row in entries]
    for row in repeating:
        for begin, finish in occurrences(row, start, end):
            day = begin.isoformat()
            if (row["id"], day) not in skipped:
                items.append(calendar_item(row, day, finish.isoformat()))

    items.extend({
        "id": row["id"], "kind": "step", "title": row["title"], "area": row["area"],
        "startDate": row["scheduled_date"], "endDate": row["scheduled_date"],
        "planId": row["plan_id"], "planTitle": row["plan_title"], "done": bool(row["done"]),
    } for row in steps)
    items.sort(key=lambda item: (item["startDate"], item["title"], item["kind"], item["id"]))
    return {"items": items}


@app.post("/api/entries", status_code=201)
def create_entry(fields: CreateEntry):
    data = normalize(fields)
    payload = json.dumps({key: value for key, value in data.items() if key != "frequency" or value}, sort_keys=True)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        operation = db.execute(
            "SELECT payload FROM entry_operations WHERE id = ?", (fields.id,),
        ).fetchone()
        if operation:
            if operation["payload"] != payload:
                raise HTTPException(409, "Этот идентификатор уже использован для другой записи.")
            return entry_response(by_id(db, fields.id))
        if db.execute("SELECT 1 FROM entries WHERE id = ?", (fields.id,)).fetchone():
            raise HTTPException(409, "Запись с таким идентификатором уже существует.")
        db.execute(
            """INSERT INTO entries
               (id, kind, title, area, startDate, endDate, startTime, endTime, birthMonth, birthDay)
               VALUES (:id, :kind, :title, :area, :startDate, :endDate, :startTime,
                       :endTime, :birthMonth, :birthDay)""", data,
        )
        if data["frequency"]:
            db.execute("INSERT INTO entry_series (entry_id, frequency) VALUES (?, ?)", (fields.id, data["frequency"]))
        db.execute("INSERT INTO entry_operations (id, payload) VALUES (?, ?)", (fields.id, payload))
        return entry_response(by_id(db, fields.id))


@app.patch("/api/entries/{entry_id}")
def update_entry(entry_id: str, changes: dict):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current = entry_response(by_id(db, entry_id))
        current.pop("id")
        try:
            fields = EntryFields.model_validate({**current, **changes})
        except ValidationError as error:
            details = [
                {"loc": ["body", *item["loc"]], "msg": item["msg"]}
                for item in error.errors()
            ]
            raise HTTPException(422, detail=details) from error
        data = normalize(fields)
        db.execute(
            """UPDATE entries SET kind=:kind, title=:title, area=:area, startDate=:startDate,
               endDate=:endDate, startTime=:startTime, endTime=:endTime,
               birthMonth=:birthMonth, birthDay=:birthDay WHERE id=:id""",
            {**data, "id": entry_id},
        )
        anchors = ("frequency", "kind", "startDate", "birthMonth", "birthDay")
        if any(current[key] != data[key] for key in anchors):
            db.execute("DELETE FROM entry_series WHERE entry_id = ?", (entry_id,))
            db.execute("DELETE FROM skipped_occurrences WHERE entry_id = ?", (entry_id,))
            if data["frequency"]:
                db.execute("INSERT INTO entry_series (entry_id, frequency) VALUES (?, ?)", (entry_id, data["frequency"]))
        return entry_response(by_id(db, entry_id))


@app.delete("/api/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str, scope: Literal["all", "one", "before", "after"] = "all", occurrence: str | None = None,
):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = by_id(db, entry_id)
        if scope == "all":
            db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        else:
            day = calendar_date(occurrence, "occurrence", "query")
            repeating = row["kind"] == "birthday" or row["frequency"]
            if not repeating or not any(begin == day for begin, _ in occurrences(row, day, day)):
                invalid("occurrence", "Дата не входит в серию.", "query")
            if scope == "one":
                db.execute("INSERT OR IGNORE INTO skipped_occurrences VALUES (?, ?)", (entry_id, occurrence))
            else:
                delta = 1 if scope == "before" else -1
                if not 1 <= day.toordinal() + delta <= date.max.toordinal():
                    db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
                else:
                    boundary = (day + timedelta(days=delta)).isoformat()
                    column = "active_from" if scope == "before" else "active_until"
                    db.execute(
                        f"""INSERT INTO entry_series (entry_id, frequency, {column}) VALUES (?, ?, ?)
                            ON CONFLICT(entry_id) DO UPDATE SET {column} = excluded.{column}""",
                        (entry_id, row["frequency"], boundary),
                    )
    return Response(status_code=204)
