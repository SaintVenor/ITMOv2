import json
from contextlib import contextmanager
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError

from .db import connect
from .entries import calendar_date

router = APIRouter(prefix="/api")
Id = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]
Motif = Literal["route", "film", "grid"]


class Fields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PlanFields(Fields):
    title: str = Field(min_length=1, max_length=180)
    area: Literal["study", "personal"] = "personal"
    note: str = Field(default="", max_length=4000)
    motif: Motif | None = None
    cover: str | None = Field(None, max_length=560000, pattern=r"^(?:dawn|rings|reef|atlas|comet|field|data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2})$")


class StepFields(Fields):
    title: str = Field(min_length=1, max_length=180)
    scheduledDate: str | None = None
    done: bool = Field(default=False, strict=True)


class CreatePlan(PlanFields):
    id: Id


class CreateStep(StepFields):
    id: Id


class CreateResource(Fields):
    id: Id
    title: str = Field(min_length=1, max_length=180)
    url: AnyHttpUrl


@contextmanager
def transaction():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        yield db


PLAN_SELECT = "SELECT p.*, c.cover FROM plans p LEFT JOIN plan_covers c ON c.plan_id = p.id"


def save_cover(db, plan_id, cover):
    if cover:
        db.execute("""INSERT INTO plan_covers VALUES (?, ?)
                      ON CONFLICT(plan_id) DO UPDATE SET cover = excluded.cover""", (plan_id, cover))
    else:
        db.execute("DELETE FROM plan_covers WHERE plan_id = ?", (plan_id,))


def read_plan(db, plan_id):
    row = db.execute(PLAN_SELECT + " WHERE p.id = ?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "План не найден.")
    return dict(row)


def step_record(row):
    return {
        "id": row["id"], "planId": row["plan_id"], "position": row["position"],
        "title": row["title"], "scheduledDate": row["scheduled_date"], "done": bool(row["done"]),
    }


def read_step(db, step_id):
    row = db.execute("SELECT * FROM steps WHERE id = ?", (step_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Шаг не найден.")
    return step_record(row)


def read_resource(db, resource_id):
    row = db.execute(
        "SELECT id, title, url FROM resources WHERE id = ?", (resource_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Материал не найден.")
    return dict(row)


def detailed_plan(db, plan_id):
    plan = read_plan(db, plan_id)
    plan["steps"] = [
        step_record(row) for row in db.execute(
            "SELECT * FROM steps WHERE plan_id = ? ORDER BY position", (plan_id,),
        )
    ]
    plan["resources"] = [
        dict(row) for row in db.execute(
            "SELECT id, title, url FROM resources WHERE plan_id = ? ORDER BY rowid", (plan_id,),
        )
    ]
    return plan


def replay(db, kind, identifier, fields):
    payload = json.dumps(fields, sort_keys=True)
    operation = db.execute(
        "SELECT payload FROM plan_operations WHERE kind = ? AND id = ?", (kind, identifier),
    ).fetchone()
    if operation:
        if operation["payload"] != payload:
            raise HTTPException(409, "Этот идентификатор уже использован для другого запроса.")
        return True
    # Reserve the operation in the same transaction as its entity.
    db.execute(
        "INSERT INTO plan_operations (kind, id, payload) VALUES (?, ?, ?)",
        (kind, identifier, payload),
    )
    return False


def require_free_id(db, table, identifier):
    # The table name is always supplied by the route, never by the requester.
    if db.execute(f"SELECT 1 FROM {table} WHERE id = ?", (identifier,)).fetchone():
        raise HTTPException(409, "Этот идентификатор уже занят.")


def patched(model, current, changes):
    try:
        return model.model_validate({**current, **changes})
    except ValidationError as error:
        raise HTTPException(422, [
            {"loc": ["body", *item["loc"]], "msg": item["msg"]} for item in error.errors()
        ]) from error


def check_date(fields):
    if fields.scheduledDate is not None:
        calendar_date(fields.scheduledDate, "scheduledDate")


@router.get("/plans")
def list_plans():
    with connect() as db:
        db.execute("BEGIN")
        plans = {
            row["id"]: {**dict(row), "steps": []}
            for row in db.execute(PLAN_SELECT + " ORDER BY p.rowid")
        }
        for row in db.execute("SELECT plan_id, title, done FROM steps ORDER BY plan_id, position"):
            plans[row["plan_id"]]["steps"].append({"title": row["title"], "done": bool(row["done"])})
    return {"items": list(plans.values())}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    with connect() as db:
        db.execute("BEGIN")
        return detailed_plan(db, plan_id)


@router.post("/plans", status_code=201)
def create_plan(fields: CreatePlan):
    data = fields.model_dump()
    if data["cover"] is None:
        data.pop("cover")
    with transaction() as db:
        if not replay(db, "plan", fields.id, data):
            require_free_id(db, "plans", fields.id)
            position = db.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
            motif = fields.motif or ("film", "route", "grid")[position % 3]
            db.execute(
                "INSERT INTO plans (id, title, area, note, motif) VALUES (:id, :title, :area, :note, :motif)",
                {**data, "motif": motif},
            )
            save_cover(db, fields.id, fields.cover)
        return detailed_plan(db, fields.id)


@router.patch("/plans/{plan_id}")
def update_plan(plan_id: str, changes: dict):
    with transaction() as db:
        current = read_plan(db, plan_id)
        current.pop("id")
        fields = patched(PlanFields, current, changes)
        db.execute(
            "UPDATE plans SET title=:title, area=:area, note=:note, motif=:motif WHERE id=:id",
            {**fields.model_dump(), "motif": fields.motif or current["motif"], "id": plan_id},
        )
        save_cover(db, plan_id, fields.cover)
        return detailed_plan(db, plan_id)


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: str):
    with transaction() as db:
        read_plan(db, plan_id)
        db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    return Response(status_code=204)


class StepOrder(Fields):
    ids: list[Id]


@router.put("/plans/{plan_id}/steps/order")
def reorder_steps(plan_id: str, fields: StepOrder):
    with transaction() as db:
        plan = detailed_plan(db, plan_id)
        expected = {step["id"] for step in plan["steps"]}
        if len(fields.ids) != len(expected) or set(fields.ids) != expected:
            raise HTTPException(409, "Список шагов изменился. Откройте план заново.")
        db.execute("UPDATE steps SET position = -position WHERE plan_id = ?", (plan_id,))
        db.executemany(
            "UPDATE steps SET position = ? WHERE id = ? AND plan_id = ?",
            [(index, step_id, plan_id) for index, step_id in enumerate(fields.ids, 1)],
        )
        return detailed_plan(db, plan_id)


@router.get("/steps")
def list_steps(unscheduled: bool | None = None, done: bool | None = None):
    with connect() as db:
        rows = db.execute(
            """SELECT s.*, p.title AS plan_title, p.area
               FROM steps s JOIN plans p ON p.id = s.plan_id
               WHERE (? IS NULL OR (s.scheduled_date IS NULL) = ?)
                 AND (? IS NULL OR s.done = ?)
               ORDER BY p.rowid, s.position""",
            (unscheduled, unscheduled, done, done),
        ).fetchall()
    return {"items": [
        {**step_record(row), "planTitle": row["plan_title"], "area": row["area"]} for row in rows
    ]}


@router.post("/plans/{plan_id}/steps", status_code=201)
def create_step(plan_id: str, fields: CreateStep):
    check_date(fields)
    data = {**fields.model_dump(), "planId": plan_id}
    with transaction() as db:
        read_plan(db, plan_id)
        if not replay(db, "step", fields.id, data):
            require_free_id(db, "steps", fields.id)
            position = db.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM steps WHERE plan_id = ?", (plan_id,),
            ).fetchone()[0]
            db.execute(
                """INSERT INTO steps (id, plan_id, position, title, scheduled_date, done)
                   VALUES (:id, :planId, :position, :title, :scheduledDate, :done)""",
                {**data, "position": position},
            )
        return read_step(db, fields.id)


@router.patch("/steps/{step_id}")
def update_step(step_id: str, changes: dict):
    with transaction() as db:
        current = read_step(db, step_id)
        fields = patched(StepFields, {key: current[key] for key in StepFields.model_fields}, changes)
        check_date(fields)
        db.execute(
            "UPDATE steps SET title=:title, scheduled_date=:scheduledDate, done=:done WHERE id=:id",
            {**fields.model_dump(), "id": step_id},
        )
        return read_step(db, step_id)


@router.delete("/steps/{step_id}", status_code=204)
def delete_step(step_id: str):
    with transaction() as db:
        read_step(db, step_id)
        db.execute("DELETE FROM steps WHERE id = ?", (step_id,))
    return Response(status_code=204)


@router.post("/plans/{plan_id}/resources", status_code=201)
def create_resource(plan_id: str, fields: CreateResource):
    data = {**fields.model_dump(mode="json"), "planId": plan_id}
    with transaction() as db:
        read_plan(db, plan_id)
        if not replay(db, "resource", fields.id, data):
            require_free_id(db, "resources", fields.id)
            db.execute(
                "INSERT INTO resources (id, plan_id, title, url) VALUES (:id, :planId, :title, :url)",
                data,
            )
        return read_resource(db, fields.id)


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: str):
    with connect() as db:
        result = db.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Материал не найден.")
    return Response(status_code=204)
