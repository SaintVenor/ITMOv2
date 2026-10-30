# Контракт UI: маршруты и разметка

Маршрут, поля формы, редирект и ошибки заданы общим контрактом ([LC-09, LC-10, LC-14](../../line-comments-contract.md));
здесь - то, что видит пользователь и что проверяют тесты UI.

## GET /submissions/{submission_id}[?assignment_id=K]

Существующий маршрут. Доступ как сейчас: ментор и автор; чужому ученику `404` (FR-009); без входа - редирект `/login`.
Числовых параметров выбора строки нет (LC-09); `assignment_id` - фильтр очереди (LC-13).

| Условие | Результат |
|---|---|
| ментор | `200`; под кодом форма `form#line-comment-form` (LC-18) |
| ученик-автор | `200`, формы и поля номера строки нет (LC-19) |

## POST /submissions/{submission_id}/line-comments

Поля формы (`application/x-www-form-urlencoded`): `line`, `text`, `assignment_id` (необязательно, фильтр очереди).

| Исход | Статус | Тело |
|---|---|---|
| успех | `303` | `Location: /submissions/{id}[?assignment_id=K]#L{n}` (FR-005; `K` только если фильтр валиден) |
| `text` пуст/длиннее предела | `400` | страница сдачи, `.field-error[data-field="text"]`, ввод сохранён (FR-012) |
| `line` неверен (LC-15) | `400` | страница сдачи, `.field-error[data-field="line"]`, ввод сохранён (FR-013) |
| оба поля неверны | `400` | оба `.field-error`, ввод сохранён |
| сдачи нет / id вне `INTEGER` | `404` | стандартная страница «Не найдено»; текст сообщения не проверяется (LC-17) |
| пользователь - ученик | `403` | стандартная страница «Доступ запрещён» (FR-010) |
| нет входа | `303` на `/login` | baseline US-1 AC3 |

## DOM-ориентиры (для тестов, FR-001…FR-019)

| Элемент | Селектор / атрибут | Условие |
|---|---|---|
| Строка кода | `div.code-row#L{n}`, номер в `span.line-no` | всегда, n с 1 |
| Блок комментариев | `div.line-comments` внутри строки n | есть комментарии |
| Комментарий | `article.line-comment#comment-<id>`: `.line-comment-author`, `time`/`.muted` дата, `.line-comment-text` | |
| Строка с комментарием | класс `code-row--commented` | FR-007 |
| Форма | `form#line-comment-form` (`action="/submissions/{id}/line-comments"`, `input[name=line]`, `textarea[name=text][maxlength=2000]`, скрытое `assignment_id` при фильтре, кнопка «Отправить») | `can_comment` |
| Ошибка поля | `.field-error[data-field="line"]`, `.field-error[data-field="text"]` из `_field_error.html` | есть ошибка |
| Пустое состояние | `p#no-line-comments` «Комментариев к строкам пока нет» | комментариев нет |
| Блок ревью | как в baseline | не меняется |

Весь вывод кода и текста - через автоэкранирование Jinja2, без `|safe` (FR-014).
