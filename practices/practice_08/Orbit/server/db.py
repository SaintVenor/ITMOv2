import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@contextmanager
def connect():
    path = Path(os.environ.get("ORBIT_DB", ROOT.parent / ".data" / "orbit.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        db.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(lessons)")}
        if "weekInterval" not in columns:
            db.execute("ALTER TABLE lessons ADD COLUMN weekInterval INTEGER NOT NULL DEFAULT 1 CHECK (weekInterval IN (1, 2))")
        if "firstDate" not in columns:
            db.execute("ALTER TABLE lessons ADD COLUMN firstDate TEXT")
        if "lessonType" not in columns:
            db.execute("""ALTER TABLE lessons ADD COLUMN lessonType TEXT
                          CHECK (lessonType IN ('lecture', 'practice', 'lab', 'consultation'))""")
