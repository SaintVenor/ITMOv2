CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('deadline', 'event', 'birthday')),
    title TEXT NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('study', 'personal')),
    startDate TEXT,
    endDate TEXT,
    startTime TEXT,
    endTime TEXT,
    birthMonth INTEGER,
    birthDay INTEGER
);

CREATE INDEX IF NOT EXISTS entry_dates ON entries (startDate, endDate);

CREATE TABLE IF NOT EXISTS entry_operations (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('study', 'personal')),
    note TEXT NOT NULL DEFAULT '',
    motif TEXT NOT NULL CHECK (motif IN ('route', 'film', 'grid'))
);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    scheduled_date TEXT,
    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    UNIQUE (plan_id, position)
);

CREATE INDEX IF NOT EXISTS step_dates ON steps (scheduled_date);

CREATE TABLE IF NOT EXISTS resources (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_operations (
    kind TEXT NOT NULL CHECK (kind IN ('plan', 'step', 'resource')),
    id TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (kind, id)
);

CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    subject TEXT NOT NULL,
    room TEXT NOT NULL,
    startTime TEXT NOT NULL,
    endTime TEXT NOT NULL CHECK (endTime > startTime),
    termStart TEXT NOT NULL,
    termEnd TEXT NOT NULL CHECK (termEnd >= termStart),
    weekInterval INTEGER NOT NULL DEFAULT 1 CHECK (weekInterval IN (1, 2)),
    firstDate TEXT,
    lessonType TEXT CHECK (lessonType IN ('lecture', 'practice', 'lab', 'consultation'))
);

CREATE INDEX IF NOT EXISTS lesson_term ON lessons (termStart, termEnd);

CREATE TABLE IF NOT EXISTS lesson_operations (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_series (
    entry_id TEXT PRIMARY KEY REFERENCES entries(id) ON DELETE CASCADE,
    frequency TEXT CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    active_from TEXT,
    active_until TEXT
);

CREATE TABLE IF NOT EXISTS skipped_occurrences (
    entry_id TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    PRIMARY KEY (entry_id, day)
);

CREATE TABLE IF NOT EXISTS plan_covers (
    plan_id TEXT PRIMARY KEY REFERENCES plans(id) ON DELETE CASCADE,
    cover TEXT NOT NULL
);
