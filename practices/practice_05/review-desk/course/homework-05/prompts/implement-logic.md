# Промпт: реализация логики (`/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`)

## До промпта (Иван)

```bash
cd ~/ITMOv2/practices/practice_05/review-desk && git status --short   # должно быть пусто
git log --oneline -1                                                   # база реализации
claude --model sonnet
```

Обычный режим, accept edits (не auto). После итога: `/export course/homework-05/05-implement-logic-session.md`
(сначала проверить cwd), затем `/exit`. Не коммитить до проверки результата.

## Промпт

````text
Проект Review Desk, фреймворк Spec Kit (не OpenSpec: скиллы openspec-* не вызывай). Ты - команда
логики фичи «построчные комментарии ментора к коду сдачи». Спека: `specs/002-line-comments-logic/`,
общий контракт: `specs/line-comments-contract.md` (LC-01...LC-29; по конституции он главнее спеки).
Реализуй только зону логики (LC-26). Файлы UI (LC-27: шаблоны, CSS, `tests/test_line_comments_ui.py`)
не трогай: их сделает следующая сессия поверх твоего результата. Не коммить.

## Шаг 0. Подготовка (покажи вывод)

- `git status --short` - пусто; `git log --oneline -1` - запомни хэш базы.
- `printf '{\n  "feature_directory": "specs/002-line-comments-logic"\n}\n' > .specify/feature.json`
  (файл в `.gitignore`, нужен скиллам, чтобы найти фичу).
- `sh scripts/check.sh | tail -1` - `CHECK: PASS` до начала работы.
- Прочитай целиком: контракт, все файлы `specs/002-line-comments-logic/`, `AGENTS.md`,
  `.specify/memory/constitution.md`, `docs/architecture.md`, `docs/baseline.md`.

## Шаг 1. `/speckit-tasks`

Выполни скилл speckit-tasks для `specs/002-line-comments-logic/`. Тесты обязательны (AGENTS.md:
тест первым), поэтому задачи на тесты генерируй. Требования к `tasks.md`:
- каждый тест-таск перед своей реализацией; тесты - в `tests/test_line_comments.py`;
- у каждой задачи ссылка на `[Л FR-nnn]` и/или `LC-nn`;
- пути только существующие или явно создаваемые по LC-26; каждый путь сверь с диском
  (`ls`), выдуманных путей не должно быть;
- тесты, которые пройдут ещё до реализации (например, проверка неизменного поведения baseline),
  пометь в tasks заранее: «ожидается зелёный до реализации».

## Шаг 2. `/speckit-analyze`

Выполни скилл speckit-analyze (он только читает файлы). По его отчёту:
- CRITICAL или HIGH - остановись, покажи находки и спроси Ивана. Не реализуй.
- MEDIUM/LOW, касающиеся только `tasks.md` (покрытие, порядок, пути) - исправь `tasks.md` и
  перечисли правки. spec.md, plan.md и контракт не меняй.
- Остальные MEDIUM/LOW - перечисли в итоге, продолжай.
Отчёт analyze сохрани в `specs/002-line-comments-logic/analyze-report.md`.

## Шаг 3. `/speckit-implement`

Выполни скилл speckit-implement по `tasks.md`. Уточнения к скиллу:
- Чеклисты: если `checklists/requirements.md` не полностью отмечен, остановись и спроси, как
  требует скилл.
- Шаг скилла про ignore-файлы: только проверить. `.gitignore` и другие ignore-файлы не меняй,
  `.dockerignore`/`.eslintignore` не создавай.
- Цикл на каждую группу задач: тест → запуск → показать падение (вывод pytest) → минимальная
  реализация → запуск → зелёный. Для тестов, помеченных «зелёный до реализации», - показать, что
  они зелёные, и не подгонять.
- Отмечай выполненные задачи в `tasks.md` (`[X]`).

Правила (AGENTS.md и контракт):
- Бизнес-правила - только в `app/services/line_comments.py`; роут в `app/web/line_comments.py`
  только разбирает форму, вызывает сервис и рендерит/редиректит.
- Схема - только новая таблица (`create_all`), существующие таблицы не меняются.
- `render_submission`: `db` и новые аргументы - keyword-only в конце (LC-12); все существующие
  вызовы обновить (`app/web/review.py`, `app/web/submissions.py`). Существующие тесты не менять и
  не ослаблять.
- Новые зависимости не добавлять. `docs/baseline.md`, `scripts/check.sh`, `AGENTS.md` не менять.
- Тесты в `tests/test_line_comments.py`; docstring каждого теста начинается с `[Л FR-nnn]` и
  содержит `LC-nn` (LC-29).

Ловушки проекта, учесть в тестах:
- POST-тест без валидного тела формы даёт ложный 404/400: в каждом POST-тесте полное тело
  (`line`, `text`, при необходимости `assignment_id`) и проверка, что ошибка именно та.
- Если считаешь запросы через spy на `Session.get`, фильтруй по модели: `auth.get_user` тоже
  вызывает `Session.get`.
- Тексты 404 у `handle_bad_path` и `handle_service_error` разные; по LC проверяются статус и
  заголовок, не текст.
- Числа вне int64 в SQLite дают 500 мимо обработчиков: таблица разбора номера строки из
  контракта (включая `9223372036854775808` и `"9"*5000`) - обязательные тесты.
- Отображение комментариев в HTML - зона UI. Логика проверяет статусы, `Location`, состояние БД,
  данные сервиса и наличие ключей контекста. Проверять разметку UI здесь не нужно.

## Шаг 4. Проверка и итог

- `sh scripts/check.sh | tail -3` - `CHECK: PASS`.
- `git status --short` - изменены и созданы только файлы LC-26, `specs/002-line-comments-logic/`
  (`tasks.md`, `analyze-report.md`); `.specify/feature.json` в статусе не виден.
- `git diff --stat <хэш базы>` - покажи.
- Итог: таблица «задача → тест (имя) → LC/FR → статус», какие тесты были зелёными до
  реализации, находки analyze и что с ними сделано, отклонения от tasks.md. Затем остановись.
````
