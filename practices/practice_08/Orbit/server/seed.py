import argparse
from datetime import date, timedelta

from .db import connect, initialize


def seed(anchor, flight_plan=False):
    initialize()
    prefix = f"demo-{anchor:%Y-%m}"
    # Keep the demo trip crossing the month boundary for every seed month.
    next_month = (anchor.replace(day=28) + timedelta(days=4)).replace(day=1)
    trip_start = next_month - timedelta(days=4)
    trip_end = next_month + timedelta(days=1)
    term_month = ((anchor.month - 1) // 4) * 4 + 1
    term_start = date(anchor.year, term_month, 1)
    if term_month == 9:
        term_end = date(anchor.year, 12, 31)
    else:
        term_end = date(anchor.year, term_month + 4, 1) - timedelta(days=1)
    with connect() as db:
        db.executemany(
            """INSERT OR IGNORE INTO entries
               (id, kind, title, area, startDate, endDate, startTime, birthMonth, birthDay)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (f"{prefix}-lab", "deadline", "Лабораторная по алгоритмам", "study",
                 anchor.isoformat(), anchor.isoformat(), "18:00", None, None),
                (f"{prefix}-travel", "event", "Поездка в Карелию", "personal",
                 trip_start.isoformat(), trip_end.isoformat(), None, None, None),
                ("demo-birthday", "birthday", "День рождения Саши", "personal",
                 None, None, None, anchor.month, 24),
            ],
        )
        db.executemany(
            """INSERT OR IGNORE INTO lessons
               (id, weekday, subject, room, startTime, endTime, termStart, termEnd)
               VALUES (?, 5, ?, ?, ?, ?, ?, ?)""",
            [
                (f"demo-lesson-{term_start:%Y-%m}-{suffix}", subject, room, start, end,
                 term_start.isoformat(), term_end.isoformat())
                for suffix, subject, room, start, end in (
                    ("math", "Дискретная математика", "2403", "09:00", "10:30"),
                    ("design", "Проектирование интерфейсов", "2312", "10:50", "12:20"),
                    ("english", "Английский язык", "3104", "13:00", "14:30"),
                )
            ],
        )
        if flight_plan:
            db.execute(
                """INSERT OR IGNORE INTO entries
                   (id, kind, title, area, startDate, endDate, startTime, endTime)
                   VALUES (?, 'event', 'Консультация по проекту', 'study', ?, ?, '10:00', '10:45')""",
                (f"{prefix}-consultation", anchor.isoformat(), anchor.isoformat()),
            )
            db.executemany(
                "UPDATE lessons SET lessonType = ? WHERE id = ? AND lessonType IS NULL",
                [(kind, f"demo-lesson-{term_start:%Y-%m}-{suffix}") for suffix, kind in
                 (("math", "lecture"), ("design", "practice"), ("english", "lab"))],
            )
        db.executemany(
            """INSERT OR IGNORE INTO plans (id, title, area, note, motif)
               VALUES (?, ?, ?, ?, ?)""",
            [
                ("demo-film", "Снять первый короткий ролик", "personal",
                 "Собрать ролик из коротких кадров и попробовать монтаж.", "film"),
                ("demo-books", "Собрать список книг", "personal", "", "grid"),
            ],
        )
        route = db.execute(
            """INSERT OR IGNORE INTO plans (id, title, area, note, motif)
               VALUES ('demo-route', 'Пройти маршрут вдоль залива', 'personal', '', 'route')"""
        )
        if flight_plan and route.rowcount:
            db.execute(
                """INSERT INTO steps (id, plan_id, position, title, done)
                   VALUES ('demo-route-walk', 'demo-route', 1, 'Пройти от набережной до маяка', 1)"""
            )
        db.executemany(
            """INSERT OR IGNORE INTO steps (id, plan_id, position, title, done)
               VALUES (?, 'demo-film', ?, ?, ?)""",
            [
                ("demo-watch", 1, "Посмотреть урок", 1),
                ("demo-draft", 2, "Собрать черновик", 0),
                ("demo-review", 3, "Посмотреть ролик целиком", 0),
            ],
        )
        db.execute(
            """INSERT OR IGNORE INTO resources (id, plan_id, title, url)
               VALUES ('demo-tutorial', 'demo-film', 'Урок по монтажу',
                       'https://www.blender.org/support/tutorials/')""",
        )
    print(f"Demo seed: {anchor.isoformat()}, trip {trip_start} .. {trip_end}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--flight-plan", action="store_true")
    args = parser.parse_args()
    seed(args.date, args.flight_plan)
