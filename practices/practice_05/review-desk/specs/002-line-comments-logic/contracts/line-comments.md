# Контракт логики: построчные комментарии

Общий контракт [`specs/line-comments-contract.md`](../../line-comments-contract.md) главнее этого файла: сервис, маршрут,
ключи контекста и ошибки определены там (LC-NN). Здесь - только детали зоны логики, которые контракт не переопределяют.

## Что реализует логика

| Что | Пункт контракта |
|---|---|
| Таблица `line_comments`, модель `LineComment` в `app/models.py` | LC-01 |
| `LineCommentView(id, line, text, author: str, created_at)`, порядок `line`, `created_at`, `id` | LC-02, LC-03 |
| `split_code_lines(code)`, `line_count(submission)` | LC-04, LC-05 |
| `LINE_COMMENT_MAX = 2_000`, `clean_text(text, LINE_COMMENT_MAX, "Комментарий к строке")` | LC-06 |
| `can_comment`, `list_line_comments`, `create_line_comment` | LC-07 |
| Порядок проверок: роль → сдача → поля `line` и `text` вместе | LC-08 |
| `POST /submissions/{submission_id}/line-comments`, поля `line`, `text`, `assignment_id` | LC-09 |
| `303` на `/submissions/{id}[?assignment_id=K]#L{n}` | LC-10, LC-13 |
| Ключи контекста и `render_submission` (keyword-only, комментарии грузит сам) | LC-11, LC-12 |
| Ответы на ошибки и тест-таблица номера строки | LC-14, LC-15 |
| Ошибки у полей, ввод возвращается всегда; 404 — статус и заголовок | LC-16, LC-17 |

## Детали зоны логики

- `line` приходит строкой как из формы; разбор и проверка — в сервисе (LC-15), роут номер не парсит.
- `list_line_comments` использует правила `get_submission_for`: ментор — любая сдача, ученик — только своя, иначе `NotFound`.
- Роут при `ValidationError` вызывает `render_submission(..., status_code=400, line_comment_errors=exc.errors, line_comment_form={"line": ..., "text": ...}, db=db, queue_filter=...)`.
- Ученик (любой ввод, в том числе невалидный или несуществующая сдача) получает `403` раньше разбора формы (`Depends(require_mentor)`); аноним — `303` на `/login`.
- Мусорный `assignment_id` отбрасывается без ошибки (`queue_filter_or_none`).
- Исключения — из `app/services/errors.py`; новых категорий нет (FR-019).

## Что логика ожидает от UI

- Форма отправляет поля `line` и `text` (и скрытое `assignment_id` при фильтре очереди).
- Ошибки показываются у полей `line` и `text` из `line_comment_errors`, введённые значения берутся из `line_comment_form`.
- Текст выводится с автоэкранированием Jinja2, без `|safe`.
- Строки кода выводятся из `code_lines`, шаблон код не делит; `maxlength` поля текста — из `line_comment_max`.
