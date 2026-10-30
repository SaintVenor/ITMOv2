# Proposal

## Why

Известная проблема B из архива `2026-10-30-review-queue-task-filter`: сверхбольшие числовые id в пути (`> 2^63-1`) приводят к `500` (`OverflowError` в SQLite) вместо `404` «Не найдено». Для нечисловых id (`/assignments/abc`) приложение уже отдаёт `404` через `handle_bad_path`; переполняющие числовые id ведут себя иначе, потому что `OverflowError` возникает позже — при обращении к SQLite, — и этот обработчик его не перехватывает.

## What Changes

- Во всех маршрутах с числовым id пути (`assignment_id`, `submission_id`) значения, которые не укладываются в диапазон SQLite `INTEGER` (знаковое 64-битное целое, `-2^63 … 2^63-1`), трактуются как заведомо несуществующие и дают `404` «Не найдено» — без обращения к БД.
- Проверка границы выполняется в сервисном слое (`app/services/`), в тех же функциях, что уже делают `db.get(...)`, по аналогии с уже существующей проверкой `SQLITE_INT_MAX` в `app/services/reviews.py::parse_assignment_filter`.
- **BREAKING (наблюдаемое поведение):** `GET /assignments/{assignment_id}`, `POST /assignments/{assignment_id}/submissions`, `GET /submissions/{submission_id}`, `POST /submissions/{submission_id}/review` при `assignment_id`/`submission_id` вне диапазона SQLite `INTEGER` сейчас отдают `500`, а будут отдавать `404` «Не найдено» (тот же текст и шаблон, что и для несуществующего id). Тестов baseline это не затрагивает — они такие значения не используют.

## Capabilities

### New Capabilities
- `path-id-bounds`: обработка числовых id в путях, которые не укладываются в диапазон SQLite `INTEGER`, как несуществующих ресурсов (`404`), для всех маршрутов с параметром `assignment_id` или `submission_id`.

### Modified Capabilities
- нет

## Impact

- Код: `app/services/assignments.py` (`get_assignment`), `app/services/submissions.py` (`get_submission_for`), `app/services/reviews.py` (`create_review`, где сейчас сдача ищется через `db.get(Submission, submission_id)` в обход `get_submission_for`). Возможно выделение общей константы/проверки границы (сейчас `SQLITE_INT_MAX` объявлена только в `app/services/reviews.py`).
- Маршруты `app/web/*.py` не меняются: параметры пути уже типизированы как `int`, значение в обработчик приходит и так — просто сервис теперь отказывает ему раньше, чем дойдёт до `db.get`.
- Тесты: новый `tests/test_path_id_overflow_404.py`.
- `docs/baseline.md` и `scripts/check.sh` не меняются.
- Новых зависимостей и изменений модели данных нет.
