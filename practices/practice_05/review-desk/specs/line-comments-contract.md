# Общий контракт: построчные комментарии ментора к коду сдачи

Контракт общий для `specs/001-line-comments-ui/` и `specs/002-line-comments-logic/`. По конституции
(`.specify/memory/constitution.md`, «Spec Kit Feature Organization») при расхождении контракт главнее спеки
любой из фич; спека может добавлять детали своей зоны, но не переопределяет то, что записано здесь.

В контракте только то, что решено в `course/homework-05/03-decisions.md`. Каждый пункт имеет идентификатор
`LC-NN` и ссылку «Решение N» (обоснования и отвергнутые варианты - в `course/homework-05/03-contract-diff.md`,
фаза 3, у решения с тем же номером). Пути в коде даны от корня репозитория.

## 1. Данные

**LC-01. Таблица `line_comments`** (Решение 2). Новая таблица, создаётся существующим
`Base.metadata.create_all` (`app/db.py:25`); существующие таблицы не меняются.

| Поле | Тип | Ограничения |
|---|---|---|
| `id` | integer | PK |
| `submission_id` | integer | FK → `submissions.id`, NOT NULL |
| `line` | integer | NOT NULL, ≥ 1; верхнюю границу проверяет сервис (LC-15) |
| `text` | text | NOT NULL, 1…`LINE_COMMENT_MAX` символов после `clean_text` (LC-06) |
| `author_id` | integer | FK → `users.id`, NOT NULL; роль `mentor` проверяет сервис |
| `created_at` | datetime (tz) | NOT NULL, default `utcnow` (`app/models.py`) |

Уникальных ограничений нет: на одну строку можно несколько комментариев. Модель `LineComment` - в
`app/models.py`, связи `submission` и `author` без `back_populates` в `Submission` (класс не меняется,
образец - `Review`, `app/models.py:62-73`).

**LC-02. `LineCommentView`** (Решение 2). Единственный тип, который сервис отдаёт наружу и который читает
шаблон:

```text
LineCommentView(id: int, line: int, text: str, author: str, created_at: datetime)
```

Поле номера называется `line` (не `line_number`); `author` - строка `display_name` (`app/models.py:27`),
не объект `User`; `username` и хэш пароля в вид не попадают. Шаблон выводит `c.author` и дату фильтром `dt`
(`app/web/templating.py:14-19`).

**LC-03. Порядок** (Решение 2). Список отдаётся по `line`, затем `created_at`, затем `id` (по возрастанию).
Группировку по строке для вывода делает шаблон.

**LC-04. `split_code_lines(code)`** (Решение 1). Единственная функция, определяющая «строку кода»;
живёт в `app/services/line_comments.py`. Правила, в таком порядке:

1. `\r\n` → `\n`, затем одиночный `\r` → `\n`;
2. `split("\n")`;
3. один финальный пустой элемент отбрасывается;
4. пустой код → `[]`.

`splitlines()` не использовать. Проверяется тестами функции: `"" → []`, `"a\n" → ["a"]`,
`"\n" → [""]`, `"a\r\nb\rc" → ["a", "b", "c"]`, `"a\x0cb c" → ["a\x0cb c"]`.

**LC-05. `line_count`** (Решение 1). `line_count(submission) = len(split_code_lines(submission.code))`;
допустимые номера - `1..line_count`. Число строк не считается нигде больше: ни в шаблоне, ни в роуте.

**LC-06. Текст и лимит** (Решение 7). Константа `LINE_COMMENT_MAX = 2_000` в `app/services/line_comments.py`
(имя `COMMENT_MAX` занято: `app/services/reviews.py:13`). Текст проходит
`clean_text(text, LINE_COMMENT_MAX, "Комментарий к строке")` (`app/services/validation.py:1-8`): `strip`,
`\r\n` → `\n`, длина 1…2 000. Атрибут `maxlength` у `textarea` берётся из ключа контекста
`line_comment_max`, не литералом.

## 2. Вызовы

**LC-07. Функции сервиса** (Решение 3). Модуль `app/services/line_comments.py`:

```text
split_code_lines(code: str) -> list[str]                                         # LC-04
line_count(submission) -> int                                                     # LC-05
can_comment(user, submission) -> bool                                             # True для mentor в любом статусе
list_line_comments(db, user, submission_id: int) -> list[LineCommentView]         # порядок LC-03
create_line_comment(db, user, submission_id: int, line: str, text: str) -> LineComment
```

- `can_comment` - по образцу `can_review` (`app/services/reviews.py:61-62`); статус сдачи и наличие ревью не
  влияют (LC-23).
- `list_line_comments` использует `get_submission_for` (`app/services/submissions.py:102`): ментору любая
  сдача, ученику только своя; иначе `NotFound`. Нет комментариев - пустой список, не ошибка.
- `create_line_comment` принимает `line` строкой как из формы и сам её разбирает (LC-15); возвращает
  созданный `LineComment`.
- Исключения - только из `app/services/errors.py`: `Forbidden`, `NotFound`, `ValidationError`; новых нет.

**LC-08. Порядок проверок при создании** (Решения 3, 8). Роль `mentor` (`ensure_role` → `Forbidden`) → сдача
(`NotFound`, в том числе id вне INTEGER через `fits_sqlite_int`, `app/services/validation.py:17-18`) →
поля `line` и `text` вместе (одно `ValidationError` с ключами `line` и/или `text`). При любой ошибке запись не
создаётся. Создание не меняет статус сдачи, ревью и очередь.

**LC-09. Маршрут и форма** (Решение 5). Файл `app/web/line_comments.py`:

```text
POST /submissions/{submission_id}/line-comments
  submission_id: int (путь)
  line: str = Form("")
  text: str = Form("")
  assignment_id: str | None = Form(None)
  user = Depends(require_mentor)
```

`line` объявлен строкой, не `int`: форма с дефолтом не даёт `RequestValidationError` (`app/main.py:73-77`),
поэтому ошибка номера - это `ValidationError` (400), а не 404. JSON-`GET` не делается; `GET` на этот путь не
отдаёт страницу (проверяется `status in (404, 405)`). Новых числовых query-параметров у страницы сдачи нет;
единственный параметр - `assignment_id` (LC-13).

**LC-10. Редирект после успеха** (Решение 5). `303`, `Location`:
`/submissions/{id}[?assignment_id=K]#L{n}`. `K` - id задачи, проверенной через `queue_filter_or_none`
(`app/services/reviews.py:42-47`), мусорный или пустой фильтр - без query; `n` - уже провалидированное целое
(`line` созданного комментария). Сырой ввод в `Location` не попадает (образец - RQF-10,
`openspec/specs/review-queue/spec.md:128`).

**LC-11. Ключи контекста страницы сдачи** (Решение 3). Шаблон `submissions/detail.html` получает:

| Ключ | Тип | Назначение |
|---|---|---|
| `line_comments` | `list[LineCommentView]` | комментарии сдачи в порядке LC-03 |
| `code_lines` | `list[str]` | `split_code_lines(submission.code)`; шаблон сам код не делит |
| `line_count` | `int` | `len(code_lines)` |
| `can_comment` | `bool` | показать форму комментария (ментор) |
| `line_comment_errors` | `dict[str, str]` | ошибки полей `line` и `text` |
| `line_comment_form` | `dict[str, str]` | введённые `line` и `text` при 400 |
| `line_comment_max` | `int` | `LINE_COMMENT_MAX` для `maxlength` |

Ключ `errors` - ошибки ревью (`app/templates/submissions/detail.html:31-36`), для комментариев не
используется. Ключи присутствуют на каждом пути рендера; без ошибок `line_comment_errors` и `line_comment_form`
- пустые `dict` (как `errors or {}` в `app/web/submissions.py:103`).

**LC-12. `render_submission`** (Решение 3). Функция `app/web/submissions.py:84` сама загружает
комментарии через сервис и сама заполняет ключи LC-11 на всех путях рендера: GET страницы сдачи,
400 формы комментария, 400 формы ревью (вызов `app/web/review.py:54-63`). Новые параметры -
**только keyword-only и в конце** сигнатуры:

```text
render_submission(request, user, submission, verdict="", comment="", errors=None,
                  status_code=200, queue_filter=None, *, db, line_comment_errors=None,
                  line_comment_form=None)
```

Существующий позиционный вызов из `review.py` не ломается (его меняют только добавлением `db=`).
Проверка: ревью без вердикта (400) на сдаче с комментариями показывает их и не показывает пустое состояние
(LC-20).

**LC-13. Фильтр очереди** (Решение 9). `assignment_id` сохраняется: скрытое поле формы комментария (по образцу
`app/templates/submissions/detail.html:23`), `queue_filter_or_none` в роуте, значение попадает и в редирект
(LC-10), и в 400-перерисовку как `queue_filter` (ссылка «← Очередь ревью» ведёт на `/review?assignment_id=K`).
Мусорные значения (`abc`, `//evil.example`, `99999999999999999999`) молча отбрасываются: ни ошибки, ни query.

## 3. Ошибки

**LC-14. Таблица ошибок** (Решение 8). Проверяются в порядке LC-08; «где видно» - место на странице.

| Случай | Исключение | HTTP | Где видно пользователю | Что сохраняется |
|---|---|---|---|---|
| Нет сессии | `LoginRequired` (`app/web/deps.py:11`) | `303` на `/login` | страница входа | ничего |
| Ученик (любой ввод, в том числе несуществующий id) | `Forbidden` (из `require_mentor`, `app/web/deps.py:24-26`) | `403` | страница ошибки «Доступ запрещён» | ничего |
| `submission_id` в пути не число | `RequestValidationError` → обработчик `app/main.py:73-77` | `404` | страница ошибки «Не найдено» | ничего |
| Сдачи нет или id вне INTEGER | `NotFound` | `404` | страница ошибки «Не найдено» | ничего |
| `line` неверный (LC-15) | `ValidationError({"line": …})` | `400` | страница сдачи, ошибка у поля `line` | комментарий не создан; введённые `line` и `text` возвращены в `line_comment_form` |
| `text` пуст после `strip` или длиннее лимита | `ValidationError({"text": …})` | `400` | страница сдачи, ошибка у поля `text` | комментарий не создан; введённые значения возвращены |
| Неверны оба поля | одно `ValidationError({"line": …, "text": …})` | `400` | ошибки у обоих полей | комментарий не создан; введённые значения возвращены |
| Всё верно | - | `303` (LC-10) | страница сдачи, комментарий под своей строкой | комментарий создан |

Сообщения: для `line` - «Номер строки: целое от 1 до {N}» (при `N = 0` - «В коде нет строк»); для `text` -
из `clean_text` (LC-06).

**LC-15. Разбор номера строки** (Решение 6). В сервисе: `re.fullmatch(r"[1-9][0-9]*", s, re.ASCII)`
(`fullmatch`, не `$`; образец - `app/services/reviews.py:18-19`), затем `len(s) ≤ 19` до вызова `int()`, затем
`1 ≤ n ≤ line_count`. Любое нарушение - `ValidationError({"line": …})`. `fits_sqlite_int` применяется только к
`submission_id`, к `line` не применяется. Тест-таблица (все значения → `400`, ключ `line`, комментарий не
создан):

| `line` | Почему отклонено |
|---|---|
| `""` | пусто |
| `0` | не ≥ 1 |
| `-1` | знак |
| `05` | ведущий ноль |
| `" 5"` | пробел |
| `+5` | знак |
| `5.0` | не целое |
| `1e1` | не десятичная запись |
| `1_000` | подчёркивание |
| `٣` | не ASCII-цифра |
| `²` | не ASCII-цифра |
| `N+1` | больше числа строк |
| `9223372036854775808` | длина 19, больше числа строк |
| `"9" * 5000` | длина > 19, до `int()` |

Допустимые `1` и `N` (последняя строка) → `303`.

**LC-16. Показ ошибок и сохранение ввода** (Решение 8). Ошибки выводятся через `_field_error.html`
(`app/templates/_field_error.html:1`) с `data-field="line"` и `data-field="text"`, класс `.field-error`
(`app/static/style.css:125`). Отдельный баннер ошибки номера не вводится. Введённые `line` и `text` возвращаются
в форму всегда, в том числе когда неверен номер. Роут: `ValidationError` →
`render_submission(..., status_code=400, line_comment_errors=exc.errors, line_comment_form={"line": …, "text": …}, db=db, queue_filter=…)`.

**LC-17. Правило для 404** (Решение 8). В контракт входят статус `404` и заголовок «Не найдено»
(`app/templates/error.html:6`). Текст `message` различается (пусто в `app/main.py:77`, «Сдача не найдена» в
`app/services/submissions.py:109`) и **не проверяется** тестами ни одной из сторон.

## 4. Состояния

**LC-18. Что видит ментор** (Решение 4). Под кодом одна форма `form#line-comment-form`: поле `line`
(`inputmode="numeric"`), `textarea name=text` (`maxlength` из `line_comment_max`), скрытое `assignment_id`,
кнопка отправки. Каждая строка кода - элемент с видимым номером и `id="L{n}"`; комментарии выводятся под своей
строкой; строки с комментариями визуально отличимы. Нет ссылки «Комментировать» у строки, нет числовых
query-параметров выбора строки. Действий не больше трёх: номер, текст, отправить.

**LC-19. Что видит ученик-автор** (Решение 3, права из брифа). Код с номерами строк и комментарии под строками
(автор, дата, текст). Формы комментария и поля `line` нет (`can_comment = False`). Чужая сдача для ученика -
`404`, как несуществующая (`docs/baseline.md`, US-5 AC2). Код и текст комментариев выводятся с
автоэкранированием, без `|safe`.

**LC-20. Пустое состояние** (Решение 3, проверка). Если у сдачи нет комментариев, и ментор, и ученик-автор видят
подсказку «Комментариев к строкам пока нет». Если комментарии есть (в том числе при перерисовке после
неудачного ревью), подсказки нет.

**LC-21. Комментарии других менторов** (Решение 11а). Ментор видит комментарии всех менторов к сдаче с именами
авторов; это покрыто тестом с двумя менторами.

**LC-22. Новая попытка** (Решение 10). Комментарии остаются на своей `Submission` и не переносятся: новая
попытка - новая строка `Submission` (`app/services/submissions.py:85-91`). Страница новой попытки показывает
пустое состояние (LC-20), страница прошлой попытки - свои комментарии; это сценарий и тест в UI-спеке.

**LC-23. Любой статус** (Решение 12, тема 1). Ментор комментирует сдачу в любом статусе (`pending`,
`accepted`, `changes_requested`), в том числе после ревью; форма видна всегда; отдельной ошибки по статусу
нет (`app/services/reviews.py:71-73` запрещает только повторное ревью).

**LC-24. Видимость ученику** (Решение 12, тема 2). Ученик-автор видит комментарии сразу после создания, в том
числе у сдачи в `pending`; скрытия до вердикта нет.

**LC-25. Неверный номер строки** (Решение 12, тема 3). Ответ `400` со страницей сдачи (LC-14), не `404`.

## 5. Разделение работ

**LC-26. Файлы логики** (Решение 3): `app/models.py` (класс `LineComment`), `app/services/line_comments.py`,
`app/web/line_comments.py` (единственный экземпляр; UI его не создаёт), `app/web/submissions.py`
(`render_submission`, LC-12), `app/web/review.py` (только передача `db=` в `render_submission`),
`app/main.py` (`include_router`), `tests/test_line_comments.py`.

**LC-27. Файлы UI** (Решение 3): `app/templates/_code.html`, новые `app/templates/_line_comment.html` и
`app/templates/_line_comment_form.html`, `app/templates/submissions/detail.html`, `app/static/style.css`,
`tests/test_line_comments_ui.py`. UI не пишет Python в `app/services/` и `app/web/`.

**LC-28. Порядок реализации** (Решение 3). Сначала логика (сервис, модель, роут, `render_submission`), затем
UI на настоящем сервисе. Файлы сторон не пересекаются; общий интерфейс - только LC-02, LC-07, LC-09…LC-11.

## 6. Трассировка

**LC-29. Docstring тестов** (Решение 11б). Каждый тест фичи ссылается в docstring на пункты этого контракта
`LC-NN` и на требование своей спеки с префиксом стороны: `[UI FR-nnn]` для `tests/test_line_comments_ui.py`,
`[Л FR-nnn]` для `tests/test_line_comments.py` (номера FR двух спек пересекаются). Пример:
`"""LC-15, LC-14. [Л FR-005] Номер «05» → 400, ключ line."""`. Тесты baseline остаются `test_usN_acM_...`
(`AGENTS.md`, «Проверка»).
