# Data Model: построчные комментарии

## Таблица `line_comments` (новая)

| Поле | Тип | Ограничения | Откуда |
|---|---|---|---|
| `id` | integer | PK | FR-001 |
| `submission_id` | integer | FK → `submissions.id`, NOT NULL, ровно одна сдача | FR-001 |
| `line` | integer | NOT NULL, ≥ 1; верхняя граница проверяется сервисом по коду сдачи | FR-003, FR-005 |
| `text` | text | NOT NULL; 1…2 000 символов после strip и нормализации `\r\n` | FR-006, FR-013 |
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

- `line_count(submission)` = `len(submission.code.split("\n"))` (≥ 1, так как код не пуст); допустимые номера `1..line_count` (FR-003).

## Правила валидации

| Поле формы | Правило | Ошибка |
|---|---|---|
| `line` | `[1-9][0-9]*` ASCII, не длиннее 19 цифр, значение ≤ `line_count` | `ValidationError({"line": ...})` |
| `text` | `clean_text(text, 2000, "Комментарий")` | `ValidationError({"text": ...})` |

Оба поля проверяются вместе: ошибки возвращаются одним `ValidationError` по полям.

## Состояния

Нет переходов состояний: комментарий неизменяем (редактирование и удаление вне рамок). Статус сдачи на создание комментария не влияет и им не меняется (FR-015, FR-016).

## Совместимость

`Base.metadata.create_all` создаёт `line_comments` в уже существующей базе и не трогает остальные таблицы (FR-002, SC-005).
