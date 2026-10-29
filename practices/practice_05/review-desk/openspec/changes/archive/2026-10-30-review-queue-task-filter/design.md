# Design

## Context

Мотивация описана в proposal.md (раздел Why), требования — в `specs/review-queue/spec.md` (RQF-1…RQF-12).

Текущий поток:
```
GET /review                 app/web/review.py  review_queue
  Depends(require_mentor)   -> Forbidden -> 403
  reviews.pending_queue(db, user)
  review/queue.html: "Открыть" -> /submissions/{id}
        |
GET /submissions/{id}       app/web/submissions.py  submission_detail
  Depends(current_user); submissions.get_submission_for
  render_submission(...) -> submissions/detail.html: "<- Очередь ревью" -> /review
        |
POST /submissions/{id}/review  app/web/review.py  create_review
  reviews.create_review: NotFound 404 | Conflict 409 | ValidationError -> render_submission(400)
  успех -> 303 /review
```
Ограничения: бизнес-правила живут только в `app/services/`, роуты только разбирают запрос (AGENTS.md, docs/architecture.md). Jinja2 с автоэкранированием, без `|safe` и без JS. Ошибки сервиса переводятся в ответы через `ERROR_STATUS` в `app/main.py` (`NotFound` -> 404). `RequestValidationError` -> 404 (`handle_bad_path`).

Что проверено на .venv (FastAPI 0.162, pydantic 2.14):
- `int | None` превращает `?x=` в 422 и пропускает `-1`, `0`, `05`, `" 5"`, `+5`, `5.0`, `1_000`, `99999999999999999999`;
- зависимости выполняются раньше, чем выбрасывается ошибка валидации параметров;
- при повторе параметра `str`-параметр получает последнее значение;
- огромный id при `db.get` падает с OverflowError (500).

## Goals / Non-Goals

**Goals:**
- Одно место, где разбирается и проверяется фильтр (сервис). Роуты передают сырую строку.
- Строгий режим на `/review` и мягкий на странице сдачи и в POST, на общем парсере.
- `Location` никогда не содержит пользовательский ввод.

**Non-Goals:**
- Починка 500 на огромных id в путях baseline (находка B, см. proposal).
- Общий механизм «запоминания» навигации (сессии, `next=`, Referer).
- Изменения модели данных и новые зависимости.

## Decisions

### D1. Параметр объявляется строкой, разбор делается вручную
Роуты объявляют `assignment_id: str | None = None` (Query на `GET /review` и `GET /submissions/{id}`, `Form(None)` в POST). Тогда 422 не возникает никогда: пустое значение приходит как `""`, и решение принимает сервис.
*Альтернатива* `int | None` отвергнута. Пустое значение превращалось бы в 404, хотя должно означать «без фильтра» (RQF-1). Неканоничные `05`, `+5`, `5.0`, `1_000` проходили бы, что противоречит RQF-4. Огромные числа доходили бы до SQLite и давали 500.

### D2. Строгий ASCII-парсер в сервисе
```python
# app/services/reviews.py
ASSIGNMENT_NOT_FOUND = "Задача не найдена"
SQLITE_INT_MAX = 2**63 - 1
_CANONICAL_ID = re.compile(r"[1-9][0-9]*", re.ASCII)

def parse_assignment_filter(raw: str | None) -> int | None:
    """None/"" -> None; каноничное целое <= 2^63-1 -> int; иначе NotFound."""
```
Строка проверяется `fullmatch`, без `strip()`. Используется явный класс `[0-9]`, а не `\d`: `\d` в Python совпадает и с `٥`. `re.ASCII` оставлен как страховка на случай, если позже класс заменят на `\d`. `isdigit()` и голый `int()` не используются: `"²".isdigit()` возвращает True, а `int("²")` падает, `int(" 5")` и `int("1_000")` проходят. Граница 2^63-1 проверяется после `int()` и до любого обращения к БД, поэтому OverflowError невозможен. Ошибка всегда `NotFound(ASSIGNMENT_NOT_FOUND)`, тот же текст, что у `assignments.get_assignment`. Снаружи невалидный и несуществующий id неотличимы (RQF-3, RQF-4).
*Альтернатива* `ValidationError` (400) отвергнута решением Q1: единый 404.

### D3. Сигнатуры сервисов
```python
def get_queue_filter(db: Session, raw: str | None) -> Assignment | None:
    """Строго: None/"" -> None; невалидно или нет задачи -> NotFound."""
    # parse_assignment_filter + assignments.get_assignment

def queue_filter_or_none(db: Session, raw: str | None) -> Assignment | None:
    """Мягко: то же, но NotFound превращается в None."""

def pending_queue(
    db: Session, mentor: User, assignment: Assignment | None = None
) -> list[Submission]:
    """Как раньше; при assignment добавляется WHERE assignment_id = assignment.id."""
```
`pending_queue` сохраняет обратную совместимость: существующий вызов без третьего аргумента ведёт себя как прежде. Порядок `created_at asc, id asc` не меняется. `ensure_role` остаётся первым шагом в `pending_queue`. Плюс в роуте стоит `Depends(require_mentor)`, поэтому 403 срабатывает раньше разбора фильтра (RQF-5). Порядок вызовов в роуте: сначала зависимость (403), потом `get_queue_filter` (404), потом `pending_queue`.

Список задач для `<select>` берётся из готового `assignments.list_assignments(db)`, новый запрос не нужен.

### D4. Сборка URL и почему это не open redirect
В `app/web/submissions.py`, рядом с `render_submission`, появляется хелпер. URL относится к HTTP, поэтому он в web-слое. Он лежит не в `review.py`, потому что `review.py` уже импортирует `render_submission` из `submissions.py`, и обратный импорт дал бы цикл. `review.py` импортирует хелпер оттуда же.
```python
def review_queue_url(assignment: Assignment | None) -> str:
    return "/review" if assignment is None else f"/review?assignment_id={assignment.id}"
```
Аргумент — объект `Assignment`, загруженный из БД через `queue_filter_or_none`, а не строка из запроса. `assignment.id` — это `int` из первичного ключа. Префикс `/review` захардкожен. Поэтому в `Location` может оказаться только `/review` или `/review?assignment_id=<целое>`. Протокол, хост, `//`, `..` и дополнительные параметры туда попасть не могут: значения вроде `//evil.example` не проходят парсер, и результатом становится `/review` (RQF-10). Параметра `next=` нет. Тот же хелпер даёт `href` ссылки «← Очередь ревью» в шаблоне сдачи, чтобы логика была в одном месте.

### D5. Мягкая обработка на странице сдачи и в POST
- `GET /submissions/{id}`: роут принимает `assignment_id: str | None = None`. Если пользователь ментор, роут вызывает `queue_filter_or_none`, иначе фильтр равен `None` (студенту параметр безразличен, RQF-8). Результат передаётся в `render_submission(..., queue_filter=...)`.
- `render_submission(request, user, submission, verdict="", comment="", errors=None, status_code=200, queue_filter: Assignment | None = None)`: новый именованный параметр в конце, существующие вызовы не меняются. В контекст шаблона идут `queue_filter` и `queue_url = review_queue_url(queue_filter)`.
- `detail.html`: ссылка `<a href="{{ queue_url }}">← Очередь ревью</a>`. Скрытое поле `<input type="hidden" name="assignment_id" value="{{ queue_filter.id }}">` выводится только при `queue_filter`.
- `POST /submissions/{id}/review`: `assignment_id: str | None = Form(None)`. Фильтр вычисляется через `queue_filter_or_none` до `create_review`, но не влияет на него. Невалидный фильтр не мешает сохранению ревью и ни при каком значении не вызывает ошибку. Успех даёт `RedirectResponse(review_queue_url(queue_filter), 303)`. `ValidationError` даёт `render_submission(..., status_code=400, queue_filter=queue_filter)` (RQF-11). `Conflict` и `NotFound` по-прежнему уходят в общий обработчик, фильтр там теряется.
- Несовпадение фильтра с `submission.assignment_id` не проверяется: фильтр сохраняется как есть.

*Альтернатива* строгая обработка (404 на странице сдачи и в POST) отвергнута. В POST она либо теряет текст ревью (проверка до сохранения), либо отвечает ошибкой на уже сохранённое ревью (проверка после). Для студента она изменила бы ответ US-5 из-за параметра, который его не касается.

### D6. Шаблон очереди
Роут передаёт в `review/queue.html` контекст `{queue, assignments, queue_filter}`.
- Заголовок: `Очередь ревью{% if queue_filter %} · {{ queue_filter.title }}{% endif %}`. Блок `title` получает тот же текст.
- Форма: `<form method="get" action="/review">`, `<select name="assignment_id">` с пунктом «Все задачи» `value=""` и пунктами `{{ a.id }}`/`{{ a.title }}`. Пункт активного фильтра получает `selected`, без фильтра выбран пункт «Все задачи». Кнопка `<button type="submit">Показать</button>`.
- При `queue_filter` выводится `<a href="/review">Сбросить фильтр</a>`.
- Ссылка «Открыть»: `/submissions/{{ s.id }}{% if queue_filter %}?assignment_id={{ queue_filter.id }}{% endif %}`. Без фильтра это ровно прежний `href`, и регулярка `test_us4_ac1` продолжает работать.
- Пустое состояние: при `queue_filter` выводится «Нет сдач, ждущих ревью, по задаче {{ queue_filter.title }}», иначе прежнее «Непроверенных сдач нет.».
- В разметке формы нет подстроки `/submissions/`, иначе сломаются `test_us4_ac1_empty_queue` и `test_us4_ac2`.

### D7. Тесты
Файл `tests/test_review_queue_task_filter.py`, тесты называются `test_rqfN_<сценарий>`, в docstring указывается `RQF-N / S<k>`. Используются существующие фикстуры из `tests/conftest.py` (`mentor_client`, `student_client`, `client`, `assignment`, `make_submission` и т.д.). Дополнительную задачу тест создаёт сам через `Assignment(...)`/`db_session`. Значения с `+`, пробелами и не-ASCII символами передаются через `params={...}` у TestClient, который их корректно кодирует (например, `+5` уходит как `%2B5`). Иначе `+` в query превратился бы в пробел.

## Risks / Trade-offs

- [Поведение `/review?assignment_id=abc` меняется с 200 на 404] -> записано в proposal как изменение поведения и в RQF-4. Внешних потребителей URL нет, тестов baseline это не задевает.
- [Строгий `/review` и мягкая страница сдачи ведут себя по-разному] -> разница записана явно в RQF-8 и RQF-10 и покрыта сценариями S14 и S17.
- [`list_assignments` выводит в `<select>` и задачи без pending-сдач, при большом числе задач список длинный] -> осознанный выбор (Q6): текущая задача всегда в списке, пустое состояние достижимо из UI. Счётчики и сужение списка вне рамок.
- [Фильтр теряется на 409/404 после POST] -> принято (Q5). Ментор возвращается в очередь по ссылке из меню.
- [Остаётся баг B (500 на огромных id в путях)] -> вне рамок, записан в proposal. Новый код его не повторяет благодаря границе 2^63-1 в парсере.

## Migration Plan

Миграций БД нет. Откат — revert кода и шаблонов. Старые URL `/review` и `/submissions/{id}` без параметра работают как раньше.
