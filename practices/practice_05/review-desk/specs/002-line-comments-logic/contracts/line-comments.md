# Контракт: построчные комментарии (логика → слой отображения)

Вся бизнес-логика в `app/services/line_comments.py`; роуты `app/web/line_comments.py` только разбирают запрос и переводят исключения в ответ (FR-018, FR-019). Общий файл `specs/line-comments-contract.md` в worktree отсутствует; при его появлении он имеет приоритет (см. plan.md).

## Сервис

```text
create_line_comment(db, user, submission_id: int, line: str, text: str) -> LineComment
list_line_comments(db, user, submission_id: int) -> list[LineCommentView]
line_count(submission) -> int
```

- `line` приходит строкой как из формы; разбор и проверка — в сервисе.
- Порядок проверок при создании: роль `mentor` (`Forbidden`) → сдача (`NotFound`) → поля `line` и `text` (`ValidationError`).
- `list_line_comments` использует правила `get_submission_for`: ментор — любая сдача, ученик — только своя, иначе `NotFound`.
- `LineCommentView`: `id: int`, `line: int`, `text: str`, `author: str` (display_name), `created_at: datetime`.
- Исключения — из `app/services/errors.py`; новых категорий нет (FR-019).

## HTTP

### POST /submissions/{submission_id}/comments

Кто: только ментор. Форма (`application/x-www-form-urlencoded`): `line`, `text`.

| Ситуация | Ответ |
|---|---|
| Успех | `303` → `/submissions/{submission_id}`; комментарий сохранён |
| Нет сессии | `303` → `/login` |
| Ученик (любой ввод, в том числе невалидный или несуществующая сдача) | `403` «Доступ запрещён» |
| Сдачи нет, в том числе id вне диапазона `INTEGER` SQLite, или id не число | `404` «Не найдено» |
| `line` вне `1..N`, неканоничный (`05`, `+3`, `3.0`, ` 3`, `٣`, `1e1`), огромный, пустой | `400`, страница сдачи с `line_comment_errors["line"]` |
| `text` пустой, из пробелов или длиннее 2 000 символов | `400`, страница сдачи с `line_comment_errors["text"]` |

При `400` комментарий не создаётся, в контексте также `line_comment_form = {"line": ..., "text": ...}` с введёнными значениями.

### GET /submissions/{submission_id}/comments

Кто: ментор (любая сдача), ученик (только своя). Ответ `200`, `application/json`:

```json
{
  "line_count": 10,
  "comments": [
    {"id": 1, "line": 2, "text": "Переименуй переменную", "author": "Ментор", "created_at": "2026-10-30T12:00:00+00:00"}
  ]
}
```

- Порядок `comments`: по `line`, затем `created_at`, затем `id` (FR-008).
- Нет комментариев — `"comments": []` и `200`.
- Чужая для ученика сдача, несуществующая и вне диапазона id — `404`, одинаково (FR-009, FR-011).
- Нет сессии — `303` → `/login`.
- Текст отдаётся как есть, без экранирования и очистки (JSON сам по себе кодирует символы; HTML-экранирование при выводе — зона отображения, FR-013).

### Страница сдачи GET /submissions/{id} (существующая)

Контекст шаблона дополняется (шаблон правит UI): `line_comments` (список как в `comments` выше, с объектом `created_at`), `line_count` (int). Для ученика `line_comments` содержит комментарии его сдачи; кнопка и форма создания для ученика — решение UI (сервис всё равно ответит `403`).

## Что логика ожидает от UI

- Формы отправляют поля с именами `line` и `text`.
- Ошибки показываются у полей `line` и `text` из `line_comment_errors`.
- Текст выводится с автоэкранированием Jinja2, без `|safe`.
- Диапазон допустимых строк — `line_count`.
