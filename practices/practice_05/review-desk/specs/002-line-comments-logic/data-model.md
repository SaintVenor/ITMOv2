# Data Model: построчные комментарии

## Таблица `line_comments` (новая)

| Поле | Тип | Ограничения | Откуда |
|---|---|---|---|
| `id` | integer | PK | FR-001 |
| `submission_id` | integer | FK → `submissions.id`, NOT NULL, ровно одна сдача | FR-001 |
| `line` | integer | NOT NULL, ≥ 1; верхняя граница проверяется сервисом по коду сдачи | FR-003, FR-005 |
| `text` | text | NOT NULL; 1…`LINE_COMMENT_MAX` (2 000) символов после strip и нормализации `\r\n` | FR-006, FR-013 |
| `author_id` | integer | FK → `users.id`, NOT NULL; роль `mentor` проверяет сервис | FR-001, FR-004 |
| `created_at` | datetime (tz) | NOT NULL, default `utcnow` | FR-001 |

Индекс: `(submission_id, line, created_at, id)` — под выдачу списка в порядке FR-008.

Уникальных ограничений нет: несколько комментариев на одну строку допустимы (FR-007).

SQLAlchemy-модель `LineComment` в `app/models.py` со связями `submission` и `author` (оба `relationship()`, без `back_populates` в `Submission`, чтобы не менять существующий класс).

## Связи

- `Submission` 1 — N `LineComment` (комментарии принадлежат конкретной попытке и не переносятся, FR-001, Edge Cases).
- `User` (mentor) 1 — N `LineComment` (автор).
- С `Review` связи нет: ревью — общий вердикт, комментарии независимы и не меняют его (FR-015).

## Вычисляемые значения

- `split_code_lines(code)` — единственное правило разбиения (LC-04, FR-003): `\r\n` и `\r` → `\n`, `split("\n")`, финальный пустой элемент отбрасывается, пустой код → `[]`.
- `line_count(submission)` = `len(split_code_lines(submission.code))` (≥ 0; 0 только для пустого кода, недостижимого через HTTP); допустимые номера `1..line_count` (FR-003, LC-05).
- `LineCommentView(id, line, text, author: str, created_at)` — вид для слоя отображения (LC-02, FR-008); порядок `line`, `created_at`, `id` (LC-03).

## Правила валидации

| Поле формы | Правило | Ошибка |
|---|---|---|
| `line` | `re.fullmatch(r"[1-9][0-9]*", s, re.ASCII)`, не длиннее 19 символов (до `int()`), `1 ≤ n ≤ line_count` (LC-15) | `ValidationError({"line": ...})`: «Номер строки: целое от 1 до {N}» (при N = 0 — «В коде нет строк») |
| `text` | `clean_text(text, LINE_COMMENT_MAX, "Комментарий к строке")` | `ValidationError({"text": ...})` |

Оба поля проверяются вместе: ошибки возвращаются одним `ValidationError` по полям.

## Состояния

Нет переходов состояний: комментарий неизменяем (редактирование и удаление вне рамок). Статус сдачи на создание комментария не влияет и им не меняется (FR-015, FR-016).

## Совместимость

`Base.metadata.create_all` создаёт `line_comments` в уже существующей базе и не трогает остальные таблицы (FR-002, SC-005).
