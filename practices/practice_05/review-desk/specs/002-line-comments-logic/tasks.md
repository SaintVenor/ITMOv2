---

description: "Задачи: построчные комментарии ментора — данные и правила (зона логики, LC-26)"
---

# Tasks: Построчные комментарии ментора к коду сдачи — данные и правила

**Input**: `specs/002-line-comments-logic/` (plan.md, spec.md, data-model.md, research.md, contracts/line-comments.md, quickstart.md); общий контракт `specs/line-comments-contract.md` (LC-01…LC-29) главнее спеки.

**Tests**: обязательны (`AGENTS.md`, «Процесс»: сначала тест, показать падение, затем минимальная реализация). Все тесты фичи — в `tests/test_line_comments.py`; docstring каждого теста начинается с `[Л FR-nnn]` и содержит `LC-NN` (LC-29). Импорты нового кода (`app.services.line_comments`, `LineComment`) внутри тестов — локальные, чтобы файл собирался до реализации и каждый тест падал или проходил по отдельности.

**Зона**: только файлы LC-26: `app/models.py`, `app/services/line_comments.py` (новый), `app/web/line_comments.py` (новый), `app/web/submissions.py`, `app/web/review.py` (только `db=`), `app/main.py` (только `include_router`), `tests/test_line_comments.py` (новый). Файлы UI (LC-27: шаблоны, CSS, `tests/test_line_comments_ui.py`) не трогаются. `docs/baseline.md`, `scripts/check.sh`, `AGENTS.md`, `requirements.txt`, `.gitignore` не меняются; зависимости не добавляются.

**Проверка путей** (сверено с диском до генерации): существуют — `app/models.py`, `app/main.py`, `app/db.py`, `app/services/{auth,errors,reviews,submissions,validation}.py`, `app/web/{deps,review,submissions,templating}.py`, `tests/conftest.py`, `scripts/check.sh`, `.specify/feature.json`; создаются по LC-26 — `app/services/line_comments.py`, `app/web/line_comments.py`, `tests/test_line_comments.py`.

**Порядок историй**: US2 (чтение) идёт перед US1 (создание): `render_submission` и `list_line_comments` нужны 400-ответам формы создания, а тесты чтения создают комментарии прямо через `db_session` и от создания не зависят. Обе истории P1.

## Format: `[ID] [P?] [Story] Description`

- Все тесты лежат в одном файле, поэтому тест-задачи не помечаются `[P]`.
- Пометка **«ожидается зелёный до реализации»** — тест пройдёт до написания кода фичи (поведение baseline или уже действующий обработчик); его показывают зелёным и не подгоняют.

---

## Phase 1: Setup

**Purpose**: каркас файла тестов и фиксация базы.

- [X] T001 Зафиксировать базу: `sh scripts/check.sh | tail -1` → `CHECK: PASS`, `git log --oneline -1`, `.specify/feature.json` указывает на `specs/002-line-comments-logic` (файл не трекается). Код не меняется. [LC-28]
- [X] T002 Создать `tests/test_line_comments.py`: модульный docstring, локальные хелперы без префикса `test_` (`add_comment(db, submission, author, line, text)` прямой вставкой `LineComment`; `post_comment(client, submission_id, line, text, assignment_id=None)` — всегда с полным телом формы `line`, `text` и при необходимости `assignment_id`; `numbered_code(n)` — код из n строк). Фикстуры берутся из `tests/conftest.py` (`mentor`, `student`, `other_student`, `make_client`, `assignment`, `make_submission`, `db_session`). Тестов пока нет. [LC-29]

**Checkpoint**: `pytest tests/test_line_comments.py` собирается (0 тестов), `CHECK: PASS`.

---

## Phase 2: Foundational (блокирует все истории)

**Purpose**: таблица, единая функция строки, константы, вид `LineCommentView`.

### Tests (написать первыми, показать падение)

- [X] T003 Тесты схемы в `tests/test_line_comments.py`: (а) таблица `line_comments` с колонками `id`, `submission_id` (FK → `submissions.id`, NOT NULL), `line` (integer, NOT NULL), `text` (NOT NULL), `author_id` (FK → `users.id`, NOT NULL), `created_at` (datetime tz, NOT NULL, default `utcnow`), без уникальных ограничений — две вставки на одну строку проходят, а вставка с `line = 0` отклоняется БД (`IntegrityError`, ограничение «≥ 1» из LC-01) [Л FR-001, FR-007] [LC-01]; (б) `init_db` на уже существующей базе без `line_comments` (создать только прежние таблицы через `Base.metadata.create_all(tables=...)`, вставить данные, вызвать `init_db(engine)`) добавляет таблицу и не теряет данные [Л FR-002] [LC-01]; (в) **ожидается зелёный до реализации**: набор колонок `users`, `assignments`, `submissions`, `reviews` равен зафиксированному в тесте списку из `docs/architecture.md` (схема существующих таблиц не меняется) [Л FR-002] [LC-01].
- [X] T004 Тесты `split_code_lines` и `line_count` в `tests/test_line_comments.py` (параметризованно, LC-04): `"" → []`, `"a\n" → ["a"]`, `"\n" → [""]`, `"a\r\nb\rc" → ["a","b","c"]`, `"a\x0cb c" → ["a\x0cb c"]`, пустые строки внутри считаются; `line_count(submission)` равен `len(split_code_lines(code))`, для пустого кода 0 [Л FR-003] [LC-04, LC-05].
- [X] T005 Тест вида и констант: `LINE_COMMENT_MAX == 2_000`; `LineCommentView` имеет поля `id`, `line`, `text`, `author`, `created_at` и только их (нет `username`, `password_hash`, `author_id`) [Л FR-006, FR-008] [LC-02, LC-06].
- [X] T006 Запустить `python -m pytest tests/test_line_comments.py -q` и **показать падение** (T003 а–б, T004, T005 красные; T003 в зелёный).

### Implementation

- [X] T007 Добавить класс `LineComment` в `app/models.py` по `data-model.md` и LC-01: таблица `line_comments`; `id` PK; `submission_id` FK → `submissions.id` NOT NULL; `line` integer NOT NULL с `CheckConstraint("line >= 1")` (верхнюю границу проверяет сервис); `text` Text NOT NULL; `author_id` FK → `users.id` NOT NULL; `created_at` `DateTime(timezone=True)` NOT NULL, default `utcnow`; связи `submission` и `author` без `back_populates`; индекс `(submission_id, line, created_at, id)`. Классы `User`, `Assignment`, `Submission`, `Review` не менять. [FR-001, FR-002] [LC-01]
- [X] T008 Создать `app/services/line_comments.py`: `LINE_COMMENT_MAX = 2_000`; `@dataclass(frozen=True) LineCommentView(id, line, text, author, created_at)`; `split_code_lines(code)` по LC-04 (`\r\n` → `\n`, затем `\r` → `\n`, `split("\n")`, один финальный пустой элемент отбрасывается, пустой код → `[]`; без `splitlines()`); `line_count(submission)`. [FR-003, FR-006, FR-008] [LC-02, LC-04, LC-05, LC-06]
- [X] T009 Запустить `pytest tests/test_line_comments.py -q` → T003–T005 зелёные; `sh scripts/check.sh | tail -1` → PASS.

**Checkpoint**: модель и чистые функции готовы.

---

## Phase 3: User Story 2 — Ученик читает комментарии к своей сдаче (P1)

**Goal**: сервис отдаёт список `LineCommentView`, страница сдачи получает ключи контекста на каждом пути рендера.

**Independent Test**: комментарии вставлены в БД напрямую; автор получает свои, чужая сдача неотличима от несуществующей.

### Tests (первыми, показать падение)

- [X] T010 [US2] Тесты `list_line_comments` в `tests/test_line_comments.py`: сортировка `line`, затем `created_at`, затем `id` (комментарии вставлены в обратном порядке, с равными `created_at`) [Л FR-008] [LC-03]; у элементов `author` — строка `display_name`, а не `User` [Л FR-008] [LC-02]; сдача без комментариев → `[]` [Л FR-008] [LC-07]; HTML-разметка в тексте возвращается неизменной [Л FR-013] [US2 AC4, LC-07].
- [X] T011 [US2] Тесты прав чтения: автор-ученик получает только комментарии своей сдачи [Л FR-009]; чужой ученик получает `NotFound` с тем же исключением, что и несуществующая сдача [Л FR-009] [LC-07, LC-19]; любой ментор получает комментарии любой сдачи, включая чужих менторов (второй ментор создаётся в тесте) [Л FR-010] [LC-21]; id `2**63` и `-1`, `0` → `NotFound` без обращения к БД и без `OverflowError` [Л FR-011] [LC-08]; статус сдачи (`pending`, `accepted`, `changes_requested`) и наличие ревью на выдачу не влияют, комментарии видны ученику сразу [Л FR-016, FR-017] [LC-23, LC-24].
- [X] T012 [US2] Тест `can_comment`: `True` для ментора в любом статусе и при наличии ревью, `False` для ученика (в том числе автора) [Л FR-004, FR-016, FR-018] [LC-07, LC-23].
- [X] T013 [US2] Тесты контекста страницы сдачи (`client.get(...).context`): на `GET /submissions/{id}` у ментора и у ученика-автора присутствуют ключи `line_comments`, `code_lines`, `line_count`, `can_comment`, `line_comment_errors`, `line_comment_form`, `line_comment_max`; типы и значения по LC-11 (`code_lines == split_code_lines(code)`, `line_count == len(code_lines)`, `line_comment_max == 2000`, ошибки и форма — пустые `dict`, `can_comment` у ментора `True`, у ученика `False`); `line_comments` — вид в порядке LC-03 [Л FR-018] [LC-11, LC-12]. Тот же набор ключей на 400 ревью без вердикта (`POST /submissions/{id}/review` с `verdict=""`, `comment="x"`; статус именно `400`, а не 404) на сдаче с комментариями: комментарии в `line_comments` присутствуют [Л FR-018] [LC-12, LC-20]. Проверка разметки не нужна (зона UI).
- [X] T014 [US2] Тест чужой сдачи и страницы: ученик `GET /submissions/{чужой id}` → `404` с заголовком «Не найдено», как для `/submissions/999999` (сравнивать статус и заголовок, не текст) — **ожидается зелёный до реализации** (baseline US-5 AC2) [Л FR-009] [LC-17, LC-19].
- [X] T015 [US2] Запустить `pytest tests/test_line_comments.py -q` и **показать падение** (T010–T013 красные; T014 зелёный).

### Implementation

- [X] T016 [US2] В `app/services/line_comments.py` добавить `can_comment(user, submission)` (по образцу `can_review`, `app/services/reviews.py:61-62`: роль `mentor`, статус и ревью не влияют) и `list_line_comments(db, user, submission_id)`: `get_submission_for` (`app/services/submissions.py`) → один запрос `LineComment` по `submission_id` с `joinedload(LineComment.author)` и `ORDER BY line, created_at, id` → `list[LineCommentView]`; `author = author.display_name`. [FR-008, FR-009, FR-010, FR-011, FR-016, FR-017] [LC-03, LC-07]
- [X] T017 [US2] В `app/web/submissions.py` изменить `render_submission`: добавить в конец сигнатуры keyword-only `*, db, line_comment_errors=None, line_comment_form=None` (LC-12); внутри вызывать `list_line_comments` и заполнять ключи `line_comments`, `code_lines`, `line_count`, `can_comment`, `line_comment_errors or {}`, `line_comment_form or {}`, `line_comment_max`; существующие ключи не менять. Обновить вызов в `submission_detail` (`app/web/submissions.py`) — добавить `db=db`. [FR-018] [LC-11, LC-12]
- [X] T018 [US2] В `app/web/review.py` в вызове `render_submission` (ветка `ValidationError`) добавить только `db=db`; остальные аргументы и позиционный порядок не менять. T017 и T018 выполняются подряд без промежуточного запуска: между ними вызов из `review.py` падает с `TypeError` (`db` обязателен). [FR-018] [LC-12, LC-26]
- [X] T019 [US2] Запустить `pytest tests/test_line_comments.py -q` и существующие тесты → зелёные; `sh scripts/check.sh | tail -1` → PASS.

**Checkpoint**: US2 работает независимо (комментарии, созданные вставкой в БД, читаются и попадают в контекст).

---

## Phase 4: User Story 1 — Ментор комментирует строку кода (P1) 🎯 MVP

**Goal**: ментор создаёт комментарий через сервис и маршрут; правила, ошибки и редирект по LC-08…LC-16.

**Independent Test**: ментор отправляет `line` и `text` для чужой сдачи → `303`; список сдачи содержит комментарий.

### Tests сервиса (первыми)

- [X] T020 [US1] Тесты `create_line_comment` — успех: сдача из 10 строк, комментарий к строке 3 → возвращён `LineComment` с `submission_id`, `line == 3`, `text`, `author_id` ментора, `created_at`; затем `list_line_comments` возвращает его [Л FR-001, FR-008] [LC-07]; два комментария к строке 3 сохранены в порядке создания [Л FR-007] [LC-03]; два ментора на одну строку [Л FR-007, FR-010] [LC-21]; серия из 5 подряд созданных комментариев к одной строке сохраняется без потерь (Edge Case «одновременная отправка»; параллельность не эмулируется) [Л FR-007] [LC-01]; допустимые `"1"` и `str(N)` (последняя строка) проходят; на пустой строке кода комментировать можно [Л FR-003] [LC-15]; текст сохраняется без санитизации (только `strip` и `\r\n` → `\n`) [Л FR-013] [LC-06].
- [X] T021 [US1] Таблица разбора номера строки (LC-15, параметризованно; для каждого значения: `ValidationError` с ключом `line` в `errors`, комментарий в БД не создан): `""`, `"0"`, `"-1"`, `"05"`, `" 5"`, `"+5"`, `"5.0"`, `"1e1"`, `"1_000"`, `"٣"`, `"²"`, `str(N+1)`, `"9223372036854775808"`, `"9"*5000`, плюс завершающий `"5\n"` (защита `fullmatch`); сообщение «Номер строки: целое от 1 до {N}»; для кода без строк (`line_count == 0`, сдача создаётся прямой вставкой пустого `code`) — «В коде нет строк» [Л FR-005] [LC-14, LC-15, LC-25]. Ни один вариант не даёт `OverflowError`/`ValueError` [Л FR-005, SC-002].
- [X] T022 [US1] Тесты текста: пустой, из пробелов, `"x"*2001` → `ValidationError` с ключом `text`, сообщение с меткой «Комментарий к строке»; `"x"*2000` проходит; `"x"*2000 + "   "` проходит (длина после `strip`); оба поля неверны → одно `ValidationError` с ключами `line` и `text` [Л FR-006, FR-005] [LC-06, LC-08, LC-14].
- [X] T023 [US1] Тесты прав и порядка проверок: ученик (автор сдачи и чужой, с валидным и невалидным вводом, с несуществующим id) → `Forbidden`, записей нет [Л FR-004, FR-012] [LC-08, LC-14]; несуществующий id и `2**63` → `NotFound` (раньше валидации: невалидный `line` не превращает 404 в 400) [Л FR-011, FR-012] [LC-08]; сервис исключений вне `Forbidden`/`NotFound`/`ValidationError` не бросает [Л FR-019] [LC-07].
- [X] T024 [US1] Тесты атомарности и неизменности: при любой ошибке `count(LineComment) == 0`; при успехе статус сдачи, `review`, очередь `/review`-выборка и нумерация попыток не изменились; комментарий создаётся в `pending`, `accepted` и `changes_requested`, в том числе после ревью, без ошибки по статусу [Л FR-014, FR-015, FR-016] [LC-08, LC-23].

### Tests маршрута (первыми)

- [X] T025 [US1] Тесты `POST /submissions/{id}/line-comments` — успех: полное тело (`line`, `text`) → `303`, `Location == /submissions/{id}#L{n}`; с `assignment_id=K` существующей задачи → `Location == /submissions/{id}?assignment_id=K#L{n}`; комментарий в БД; мусорный фильтр (`abc`, `//evil.example`, `99999999999999999999`, пустой, несуществующий id задачи) → `Location` без query, ни ошибки, ни сырого ввода в `Location`; `n` — созданного комментария [Л FR-018] [LC-09, LC-10, LC-13].
- [X] T026 [US1] Тесты 400 от формы: `line="0"` и неверный/пустой `text` → статус `400` (проверять, что ответ — страница сдачи, `context` содержит `submission`, а не 404-страницу); `context["line_comment_errors"]` содержит ровно ключи неверных полей (`line`, `text` или оба); `context["line_comment_form"] == {"line": …, "text": …}` с введёнными значениями даже при неверном `line`; `context["queue_filter"]` — задача из валидного `assignment_id`, а при мусорном — `None`; все ключи LC-11 присутствуют; комментарий не создан [Л FR-005, FR-006, FR-018] [LC-13, LC-14, LC-16, LC-25].
- [X] T027 [US1] Тесты прав и путей маршрута (всегда полное тело формы): ученик → `403` с заголовком «Доступ запрещён» при валидном, невалидном вводе и несуществующем id, записей нет [Л FR-004, FR-012] [LC-14]; сдача не существует и `9223372036854775808` в пути → `404` с заголовком «Не найдено» (проверять статус и заголовок, не текст) — **ожидается зелёный до реализации** (маршрута ещё нет → 404 роутера; после реализации то же через `NotFound`) [Л FR-011] [LC-14, LC-17]; нечисловой `submission_id` (`/submissions/abc/line-comments`) → `404` — **ожидается зелёный до реализации** [Л FR-011] [LC-14, LC-17]; `GET /submissions/{id}/line-comments` → статус `404` или `405` — **ожидается зелёный до реализации** [Л FR-018] [LC-09].
- [X] T028 [US1] Запустить `pytest tests/test_line_comments.py -q` и **показать падение** (T020–T026 и «ученик → 403» из T027 красные; помеченные в T027 зелёные).

### Implementation

- [X] T029 [US1] В `app/services/line_comments.py` добавить `create_line_comment(db, user, submission_id, line, text)`: `ensure_role(user, ROLE_MENTOR)` → сдача (`db.get(Submission, …)` под `fits_sqlite_int`, иначе `NotFound("Сдача не найдена")`) → поля вместе: номер по LC-15 (`re.fullmatch(r"[1-9][0-9]*", s, re.ASCII)`, `len(s) ≤ 19` до `int()`, `1 ≤ n ≤ line_count`; `fits_sqlite_int` не применять) с сообщением «Номер строки: целое от 1 до {N}» («В коде нет строк» при N = 0), `clean_text(text, LINE_COMMENT_MAX, "Комментарий к строке")`; ошибки полей одним `ValidationError`; затем один `db.add` + `commit`, при исключении `rollback`; статус сдачи и ревью не трогать; вернуть `LineComment`. [FR-001, FR-004, FR-005, FR-006, FR-007, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-019] [LC-06, LC-07, LC-08, LC-14, LC-15]
- [X] T030 [US1] Создать `app/web/line_comments.py`: `router`; `POST /submissions/{submission_id}/line-comments` с `submission_id: int`, `line: str = Form("")`, `text: str = Form("")`, `assignment_id: str | None = Form(None)`, `user = Depends(require_mentor)`, `db = Depends(get_db)`. Роут: `queue_filter = queue_filter_or_none(db, assignment_id)` → `create_line_comment`; `ValidationError` → `render_submission(request, user, submission, status_code=400, queue_filter=queue_filter, db=db, line_comment_errors=exc.errors, line_comment_form={"line": line, "text": text})` (сдача — через `get_submission_for`); успех → `RedirectResponse(url, 303)`, где `url = /submissions/{id}[?assignment_id=K]#L{n}`, `K = queue_filter.id`, `n = comment.line`. Бизнес-правил в роуте нет. [FR-012, FR-018] [LC-09, LC-10, LC-13, LC-16]
- [X] T031 [US1] В `app/main.py` добавить импорт `line_comments` в `from app.web import …` и `app.include_router(line_comments.router)`; больше ничего не менять. [FR-018] [LC-26]
- [X] T032 [US1] Запустить `pytest tests/test_line_comments.py -q` → T020–T027 зелёные; `sh scripts/check.sh | tail -1` → PASS.

**Checkpoint**: US1 и US2 работают вместе; MVP готов.

---

## Phase 5: User Story 3 — Ментор видит комментарии при проверке (P2)

**Goal**: все менторы видят комментарии друг друга; аноним уходит на вход. Нового кода нет: поведение даёт `get_submission_for` (T016) и middleware; фаза закрывает требования тестами.

- [X] T033 [US3] Сквозной тест с двумя менторами через `POST` маршрута: ментор A создаёт комментарий, ментор B — свой к той же строке; `GET /submissions/{id}` у обоих → `context["line_comments"]` содержит оба с `author` = display_name авторов, порядок по LC-03 [Л FR-007, FR-010] [LC-21, US3 AC1].
- [X] T034 [US3] Тест анонима: `POST /submissions/{id}/line-comments` с полным телом формы и `GET /submissions/{id}` без сессии → `303`, `Location: /login`, комментарий не создан — **ожидается зелёный до реализации** (middleware `require_session`, baseline US-1 AC3) [Л FR-012] [LC-14, US3 AC2].
- [X] T035 [US3] Тест видимости ученику через маршрут: ментор создаёт комментарий к сдаче в `pending` → ученик-автор сразу видит его в `context["line_comments"]`; другой ученик получает `404` [Л FR-009, FR-017] [LC-19, LC-24].

**Checkpoint**: тесты T033, T035 зелёные после Phase 4 без нового кода; T034 зелёный и до реализации.

---

## Phase 6: Polish & cross-cutting

- [X] T036 Регрессия baseline (FR-015): ревью по сдаче с комментариями создаётся как раньше (`303` на `/review`, статус и вердикт меняются, комментарии остаются); повторное ревью → `409`; очередь `/review` и `/review?assignment_id=K` с комментариями неизменны; новая попытка ученика — новая `Submission` без комментариев (`list_line_comments` → `[]`, у прошлой попытки — свои) [Л FR-001, FR-015] [LC-22, LC-23].
- [X] T037 Тест трассировки (SC-006, LC-29): разобрать `tests/test_line_comments.py` через `ast`; у каждой функции `test_*` docstring начинается с `[Л FR-` и содержит `LC-`; множество упомянутых `FR-001`…`FR-019` равно полному (каждое требование покрыто). Тест красный, пока не покрыты все требования; финальный запуск — зелёный [Л FR-001…FR-019] [LC-29].
- [X] T038 Шаг скилла про ignore-файлы: только проверить (`git rev-parse --is-inside-work-tree`, наличие `.gitignore`); `.gitignore` и другие ignore-файлы не менять, новые не создавать.
- [X] T039 Финальная проверка: `sh scripts/check.sh | tail -3` → `CHECK: PASS`; `git status --short` — только файлы LC-26 и `specs/002-line-comments-logic/` (`tasks.md`, `analyze-report.md`); `.specify/feature.json` не виден; сверка с `quickstart.md` (шаги 2–9 покрыты тестами). Не коммитить.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 (блокирует всё) → Phase 3 (US2) → Phase 4 (US1) → Phase 5 (US3) → Phase 6.
- Внутри фаз: тесты → запуск с показом падения → реализация → запуск зелёным. T007 → T008 (T008 импортирует `LineComment`); T016 после T008; T017 после T016; T018 после T017; T029 после T016; T030 после T017 и T029; T031 после T030.
- Реализационные задачи в разных файлах (`app/models.py`, `app/services/line_comments.py`, `app/web/…`) формально независимы, но каждая группа выполняется строго после своего красного запуска.

## Parallel Opportunities

Тесты в одном файле — последовательно. После T029 задачи T030 (`app/web/line_comments.py`) и правки `app/web/review.py` (T018) касаются разных файлов, но T018 уже сделана раньше; параллелизм минимален и не используется.

## Тесты «ожидается зелёный до реализации»

| Задача | Почему зелёный сразу |
|---|---|
| T003 (в) | схема существующих таблиц не меняется |
| T014 | baseline US-5 AC2: чужая сдача → 404 |
| T027 (404 для несуществующей сдачи и `9223372036854775808`, нечисловой id, `GET` → 404/405) | маршрута нет, роутер отвечает 404/405; после реализации тот же результат даёт `NotFound`/обработчик пути |
| T034 | middleware `require_session`, baseline US-1 AC3 |

## Покрытие требований

| FR | Тесты |
|---|---|
| FR-001 | T003, T020 |
| FR-002 | T003 |
| FR-003 | T004, T021 |
| FR-004 | T012, T023, T027 |
| FR-005 | T021, T026 |
| FR-006 | T005, T022, T026 |
| FR-007 | T003, T020, T033 |
| FR-008 | T005, T010, T020 |
| FR-009 | T011, T014, T035 |
| FR-010 | T011, T020, T033 |
| FR-011 | T011, T023, T027 |
| FR-012 | T023, T027, T034 |
| FR-013 | T010, T020 |
| FR-014 | T024 |
| FR-015 | T024, T036 |
| FR-016 | T011, T012, T024 |
| FR-017 | T011, T035 |
| FR-018 | T012, T013, T025, T026, T027 |
| FR-019 | T023 |

## Implementation Strategy

MVP = Phase 1–4 (чтение + создание). Шаги: красный запуск → минимальный код → зелёный запуск на каждую группу; US3 и Polish добавляют только тесты и регрессию. Расхождение с контрактом или архитектурой — остановиться и спросить (`AGENTS.md`).
