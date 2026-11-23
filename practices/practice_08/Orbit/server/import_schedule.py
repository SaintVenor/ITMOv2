from datetime import date, datetime, timedelta

from .db import connect, initialize

ENGLISH = "Английский язык B1.1"
SPEAKING = "Техники публичных выступлений и презентаций"
MATH = "Дополнительные главы высшей математики"
AI = "Технологии ИИ в разработке ПО"
OOP = "Объектно-ориентированное проектирование"
HISTORY = "История России и мира в XX веке"
SPORT = "Большой зал (4405)"
PROBABILITY = "Теория вероятности"

# The source uses blue for lectures, yellow for practice, and purple for labs.
LESSONS = {
    16: [("11:30", "Волейбол", SPORT, None), ("13:30", "Базы данных", "2324", "lab")],
    17: [("08:10", ENGLISH, "3210", "practice"), ("09:50", ENGLISH, "3210", "practice"),
         ("13:30", PROBABILITY, "Orange Classroom (1229)", "lecture"), ("17:10", PROBABILITY, "2127", "practice")],
    18: [("08:10", SPEAKING, "2304", "practice"), ("09:50", SPEAKING, "2304", "practice"), ("11:30", MATH, "2127", "practice")],
    19: [("09:50", AI, "2342", "lab"), ("11:30", "Базы данных", "2342", "lecture")],
    20: [("09:50", AI, "2334", "lab"), ("13:30", "Волейбол", SPORT, None)],
    21: [("09:50", OOP, "2412", "lab"), ("11:30", OOP, "2412", "lab"), ("13:30", OOP, "2403", "lecture")],
    23: [("09:50", "Волейбол", SPORT, None), ("13:30", "Базы данных", "2324", "lab")],
    24: [("08:10", ENGLISH, "3210", "practice"), ("09:50", ENGLISH, "3210", "practice"),
         ("13:30", PROBABILITY, "Orange Classroom (1229)", "lecture"), ("17:10", PROBABILITY, "2127", "practice")],
    25: [("09:50", MATH, "2304", "lecture"), ("11:30", MATH, "2127", "practice")],
    26: [("11:30", "Базы данных", "2342", "lecture"), ("13:30", HISTORY, "2407 (архив)", "lecture"), ("15:30", HISTORY, "2337", "practice")],
    27: [("13:30", "Волейбол", SPORT, None)],
    28: [("13:30", OOP, "2403", "lecture")],
}


def import_schedule():
    initialize()
    with connect() as db:
        rows = []
        for number, entries in LESSONS.items():
            day = date(2026, 11, number)
            for clock, subject, room, lesson_type in entries:
                finish = (datetime.strptime(clock, "%H:%M") + timedelta(minutes=90)).strftime("%H:%M")
                identifier = f"itmo-{day:%Y%m%d}-{clock.replace(':', '')}"
                rows.append((identifier, day.isoweekday(), subject, room, clock, finish,
                             day.isoformat(), day.isoformat(), lesson_type))
        inserted = db.executemany(
            """INSERT OR IGNORE INTO lessons
               (id, weekday, subject, room, startTime, endTime, termStart, termEnd, lessonType)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows,
        ).rowcount
        typed = db.executemany(
            """UPDATE lessons SET lessonType = ?
               WHERE id = ? AND lessonType IS NULL""",
            [(row[-1], row[0]) for row in rows if row[-1] is not None],
        ).rowcount
    print(f"Filled in {typed} lesson types on existing records.")
    print(f"Imported {inserted} of {len(rows)} class sessions.")


if __name__ == "__main__":
    import_schedule()
