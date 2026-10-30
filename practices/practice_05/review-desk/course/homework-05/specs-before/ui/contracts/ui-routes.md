# Контракт UI: маршруты и разметка

## GET /submissions/{submission_id}[?line=N][&assignment_id=K]

Существующий маршрут, расширяется. Доступ как сейчас: ментор и автор; чужому ученику `404` (FR-009); без входа - редирект `/login`.

| Условие | Результат |
|---|---|
| ментор, `line` - целое в `1..line_count` | `200`; под строкой N открыта форма (`#line-comment-form`), строка с классом `code-row--active` |
| ментор, `line` отсутствует/невалиден | `200`, форма не открыта (A-2) |
| ученик-автор, любой `line` | `200`, форм и действий нет (A-3) |

## POST /submissions/{submission_id}/line-comments

Поля формы (`application/x-www-form-urlencoded`): `line` (строка, число), `text`, `assignment_id` (необязательно, фильтр очереди).

| Исход | Статус | Тело |
|---|---|---|
| успех | `303` | `Location: /submissions/{id}[?assignment_id=K]#line-N` (FR-005; `K` только если фильтр валиден) |
| `text` пуст/длиннее предела | `400` | страница сдачи, форма открыта у строки `line`, `.field-error[data-field="text"]`, ввод сохранён (FR-012) |
| `line` не число / вне диапазона | `400` | страница сдачи, баннер `.form-error[data-field="line"]`, комментарий не создан (FR-013) |
| сдачи нет / id вне `INTEGER` | `404` | стандартная страница «Не найдено» (FR-013, path-id-bounds) |
| пользователь - ученик | `403` | стандартная страница «Доступ запрещён» (FR-010) |
| нет входа | `303` на `/login` | baseline US-1 AC3 |

## DOM-ориентиры (для тестов, FR-001…FR-014)

| Элемент | Селектор / атрибут | Условие |
|---|---|---|
| Строка кода | `div.code-row#line-N`, номер в `span.line-no` | всегда, N с 1 |
| Действие | `a.line-comment-action[href*="?line=N"]` текст «Комментировать» | только ментор, `can_comment` |
| Блок комментариев | `div.line-comments` внутри строки N | есть комментарии |
| Комментарий | `article.line-comment#comment-<id>`: `.line-comment-author`, `time`/`.muted` дата, `.line-comment-text` | |
| Строка с комментарием | класс `code-row--commented` | FR-007 |
| Форма | `form#line-comment-form` (`action="/submissions/{id}/line-comments"`, скрытые `line`, `assignment_id`, `textarea[name=text][maxlength=5000]`, кнопка «Отправить») | ментор, `open_line == N` |
| Пустое состояние | `p#no-line-comments` «Комментариев к строкам пока нет» | комментариев нет |
| Блок ревью | как в baseline | не меняется |

Весь вывод кода и текста - через автоэкранирование Jinja2, без `|safe` (FR-014).
