# Отчёт проверки: построчные комментарии ментора (`git diff 4b1cf2e..HEAD`)

## 1. Вердикт: **принято** (критичных и существенных находок нет; 3 minor-наблюдения, не блокирующие)

Проверено: коммиты `a012d4c` (логика) и `ba4dca1` (UI). Файлов в проекте не создавалось: `git status --short` пуст; `.pytest_cache` существовал до проверки, прогоны шли с `-p no:cacheprovider` и `PYTHONDONTWRITEBYTECODE=1`.

## 2. Таблицы

### Блок 1. Объём и правила

| # | Ожидание | Факт | Доказательство | |
|---|---|---|---|---|
| 1.1 | Файлы только из LC-26/27, `tests/test_line_comments*.py`, `specs/`, `course/`, `docs/architecture.md` | 23 файла, все из списка. Логика (`a012d4c`): `main.py`, `models.py`, `services/line_comments.py`, `web/line_comments.py`, `web/review.py`, `web/submissions.py`. UI (`ba4dca1`): `style.css`, `_code.html`, `_line_comment*.html`, `detail.html`, `architecture.md`. UI-коммит не трогает ни одного `.py` в `app/` | `git diff --stat 4b1cf2e..HEAD`, `git show --stat a012d4c ba4dca1` | OK |
| 1.2 | `baseline.md`, `check.sh`, `AGENTS.md`, `requirements.txt`, `.gitignore` не изменены; в `tests/` только новые файлы | `UNCHANGED_OK`; `--name-status`: три `A` (`test_line_comments.py`, `_e2e.py`, `_ui.py`) | `git diff --quiet …` → rc 0 | OK |
| 1.3 | `CHECK: PASS` | `299 passed, 1 warning`, `CHECK: PASS`; из них 79 новых (47+3+29), 220 прежних | `sh scripts/check.sh \| tail -3`; `pytest --co` → 299 | OK |
| 1.4 | Бизнес-правила только в `services/` | `web/line_comments.py` разбирает форму, вызывает `queue_filter_or_none`/`create_line_comment`, ловит `ValidationError` и рендерит; проверок прав/статусов/номера нет. Права: `require_mentor` (deps) + `ensure_role` в сервисе (`app/services/line_comments.py:73`) | `grep ensure_role\|Forbidden\|status app/web/line_comments.py` → только `status_code=400/303` | OK |
| 1.5 | Нет `\|safe`/`<script`, автоэкранирование включено | grep пуст (rc 1); `autoescape` в `templating.py` не отключается | `grep -rn '\|safe\|<script\|autoescape' app/templates app/web/templating.py`; тесты `test_fr014_no_safe_filter_in_templates`, `test_fr015_page_has_no_javascript` | OK |
| 1.6 | Схема: только новая таблица | `app/models.py`: добавлен `LineComment` + импорт `CheckConstraint, Index`; существующие классы не тронуты | `git diff 4b1cf2e..HEAD -- app/models.py`; `test_existing_tables_schema_unchanged` | OK (см. m1) |
| 1.7 | Docstring у каждого теста: `[Л FR-`/`[UI FR-` и `LC-` | 79 тестов (47/3/29), `bad: 0`; сторона верная (в `_ui.py` нет `[Л`, в основном файле нет `[UI`) | скрипт на `ast` (вывод выше); мета-тест `test_every_test_has_traceable_docstring` | OK |

### Блок 2. Контракт LC-01…LC-29

| LC | Ожидание → факт (`путь:строка`) | Доказательство | |
|---|---|---|---|
| 01 | Таблица, колонки, FK, NOT NULL, `line>=1`, без UNIQUE → `models.py` класс `LineComment`; DDL: все поля NOT NULL, `CHECK(line>=1)`, 2 FK | `test_line_comments_table_columns_and_no_unique`, `…_two_on_same_line_and_line_check`; прогон 11 (DDL) | OK |
| 02 | `LineCommentView(id,line,text,author,created_at)`, author = `display_name` → `services/line_comments.py:21-27,55` | `test_view_fields_and_max_constant`, `test_list_view_author_is_display_name` | OK |
| 03 | Порядок line, created_at, id → `:52` | `test_list_order_line_created_id`, `test_fr006_two_comments_same_line_in_creation_order` | OK |
| 04 | `split_code_lines` по правилам → `:30-35` | `test_split_code_lines_rules`; прогон 7: `\r\n`/`\r`/финальный `\n`/`""`/`"\n"`/`\x0c\x85 ` | OK |
| 05 | `line_count` = len(split) единственное место → `:38`; в `render_submission` `len(code_lines)` берётся из того же списка (`web/submissions.py:57`) | `test_line_count_matches_split` | OK |
| 06 | `LINE_COMMENT_MAX=2000`, `clean_text`, `maxlength` из ключа → `:14,82`; `_line_comment_form.html` `maxlength="{{ line_comment_max }}"` | `test_create_text_length_boundary`, `test_create_rejects_bad_text`; прогон 3 (2000→303, 2001→400, пробелы→400, `"  "+2000+"  "`→303), прогон extra: `maxlength ['2000']` | OK |
| 07 | Пять функций сервиса, пустой список, только известные исключения → `:30-95` | `test_list_empty_is_empty_list`, `test_can_comment_mentor_only`, `test_create_raises_only_known_errors` | OK |
| 08 | Порядок: роль → сдача → поля вместе; запись не создаётся → `:73-86` | `test_create_student_forbidden_for_missing_submission`, `test_create_missing_submission_not_found_before_validation`, `test_create_both_fields_invalid_single_error`, `test_create_any_status_no_side_effects` | OK |
| 09 | Маршрут, `line: str`, `assignment_id: str\|None`, `require_mentor` → `web/line_comments.py:15-24`; GET не страница | `test_route_get_not_a_page`; прогон 10: GET ментор/ученик → `405`, аноним → `303` | OK |
| 10 | `303` на `/submissions/{id}[?assignment_id=K]#L{n}` → `web/line_comments.py:37-38` | `test_route_success_redirect`, `test_route_redirect_keeps_valid_filter`, `…_drops_garbage_filter`; прогон 1: `/submissions/1#L2`; прогон 6 | OK |
| 11 | Семь ключей контекста → `web/submissions.py:70-76` | `test_page_context_keys_mentor_and_student` | OK |
| 12 | `render_submission`: kw-only `*, db, …` в конце, все пути → `web/submissions.py:44-57`; `review.py:63` передаёт `db=db` | `test_review_400_keeps_comments_in_context`, `test_fr011_no_empty_state_after_failed_review_rerender`; прогон 8 | OK |
| 13 | Фильтр: скрытое поле, `queue_filter_or_none`, в редирект и в 400 → `web/line_comments.py:122,132,137` | `test_fr004_hidden_assignment_id_only_with_queue_filter`, `test_fr016_queue_link_keeps_filter_after_400`, `test_route_400_garbage_filter_dropped`; прогон 6 | OK |
| 14 | Таблица ошибок | `test_route_student_forbidden`, `…_for_missing_id`, `test_route_not_found_variants`, `test_route_400_page_with_errors_and_input`, `test_anonymous_redirected_to_login`; прогоны 2-5: 403/404/400/303 | OK |
| 15 | `fullmatch [1-9][0-9]*` ASCII, `len≤19`, `1≤n≤N` → `:17-18,60-67` | `test_create_rejects_bad_line` (таблица), `test_create_boundary_lines_ok`; прогон 2: все 14 значений (+ `-1`, `5.0`, `1e1`) → 400, строк не создано | OK |
| 16 | `_field_error.html` с `data-field`, ввод возвращается всегда → `_line_comment_form.html`, `web/line_comments.py:134-135` | `test_fr012_*`, `test_fr013_*`, `test_fr014_form_values_escaped_on_400`; прогон 2: `KEEPME` в ответе и `data-field="line"` для всех значений | OK |
| 17 | 404 + заголовок, текст не проверяется | `test_student_foreign_submission_404_same_as_missing`, `test_fr013_missing_submission_404_not_400`; прогон 4-5 | OK |
| 18 | Одна форма `#line-comment-form`, `id="L{n}"`, помеченные строки, без ссылок/query | `_code.html`, `_line_comment_form.html`; `test_fr001_code_rows_numbered_with_anchors`, `test_fr002_mentor_sees_single_form_without_comment_links`, `test_fr007_commented_row_is_marked`; прогон extra: форма ровно одна | OK |
| 19 | Ученик: номера и комментарии, без формы; чужая → 404; экранирование | `test_fr008_student_has_no_comment_form_controls`, `test_fr014_comment_text_is_escaped_…`, e2e; прогон 1 (`&lt;b&gt;` под `id="L2"`, сырого `<b>` нет), 4 (чужой → 404, комментария нет), extra (формы нет) | OK |
| 20 | Пустое состояние `#no-line-comments` | `test_fr011_empty_state_for_mentor_and_student`; прогон 8 (400 ревью: подсказки нет), 11 | OK |
| 21 | Комментарии нескольких менторов | `test_list_access_rules`, `test_two_mentors_see_each_other_via_route`, `test_fr018_…`; прогон extra: имя «Ментор2» видно | OK |
| 22 | Новая попытка: комментарии не переносятся | `test_fr019_new_attempt_has_own_empty_state`; прогон 9: у новой сдачи подсказка и нет текста, у старой текст есть, оба актора | OK |
| 23 | Любой статус, в т.ч. после ревью | `test_fr003_form_visible_in_any_status`, `test_create_any_status_no_side_effects`; прогон 9: комментарий после вердикта → 303 | OK |
| 24 | Ученик видит сразу в `pending` | `test_fr017_student_sees_comment_while_pending`, `test_student_sees_comment_immediately_in_pending`; прогон 1 | OK |
| 25 | Неверная строка → 400 со страницей сдачи | `test_route_400_page_with_errors_and_input`, `test_fr013_invalid_line_400_…`; прогон 2 | OK |
| 26 | Файлы логики | Диффы `a012d4c`: ровно файлы LC-26 | `git show --stat a012d4c` | OK |
| 27 | Файлы UI, без Python в `services/`/`web/` | Диффы `ba4dca1`: только шаблоны, CSS, тесты, docs | `git show --stat ba4dca1` | OK |
| 28 | Сначала логика, затем UI | порядок коммитов `a012d4c` → `ba4dca1` | `git log 4b1cf2e..HEAD` | OK |
| 29 | Docstring `LC-NN` + `[сторона FR-nnn]` | см. 1.7 | скрипт `ast`, `bad: 0` | OK |

### Блок 3. Собственные прогоны (`TestClient`, `StaticPool`, `init_db`, `dependency_overrides`, вход `POST /login`)

| # | Ожидание → факт | OK |
|---|---|---|
| 1 | Ментор `line=2`, `<b>x</b>` → `303`, `Location: /submissions/1#L2`; автор `GET` → `200`, `&lt;b&gt;x&lt;/b&gt;` в 700 символах после `id="L2"`, сырого `<b>x</b>` нет | OK |
| 2 | `N=3`: `4`, `0`, `05`, ` 5`, `+5`, `٣`, `²`, `1_000`, `9223372036854775808`, `"9"*5000`, `""`, `-1`, `5.0`, `1e1`, отсутствие поля → все `400`; `COUNT(line_comments)` не изменился; `KEEPME` и `data-field="line"` в ответе; `1` и `3` → `303` | OK |
| 3 | 2000 → `303`; 2001 → `400` (ошибка у `text`); `"   "` → `400`; `"  "+2000+"  "` → `303`; оба поля неверны → обе ошибки | OK |
| 4 | Ученик POST → `403` (в т.ч. id 99999 и `abc`); чужой ученик GET → `404`, комментария в теле нет; аноним POST → `303 /login`, аноним GET → `303 /login` | OK |
| 5 | Ментор, `line=1,text=x`: `abc`, `99999999999999999999`, `99999`, `-1`, `0` → `404` (не 500) | OK |
| 6 | `assignment_id=1` → `…?assignment_id=1#L2`; `abc`, `//evil.example`, `99999999999999999999`, `""`, `999`, `05` → без query. 400 с фильтром: ссылка `/review?assignment_id=1` и скрытое поле есть; 400 с мусорным: `evil` в ответе нет, ссылка `/review`. `GET …?assignment_id=abc` → `200` | OK |
| 7 | `a\r\nb\r\nc`, `a\rb\rc\r`, `a\r\nb\rc\n` → на странице `L1..L3`, POST `1..3` → 303, `4` → 400 («от 1 до 3»); `"\n"` → `L1`; `""` → нет `L*`, POST → 400 «В коде нет строк»; `x` → 1; `\x0c\x85 ` → одна строка. Номера страницы = принимаемые POST | OK |
| 8 | `POST /review` без вердикта на сдаче с комментарием → `400`, `VISIBLE_C` виден, подсказки нет, `id="L2"` есть | OK |
| 9 | (чистая база) старая сдача с комментарием → вердикт → новая попытка `303` (id 2, attempt 2): у новой подсказка и нет `OLD_C`, у старой `OLD_C` и нет подсказки; для ментора и ученика | OK |
| 10 | `GET /submissions/{id}/line-comments` (без автоследования редиректам): ментор `405`, ученик `405`, аноним `303` | OK |
| 11 | База без `line_comments`: до `init_db` таблицы нет; после — есть, `Submission.code` читается, страница сдачи `200` с подсказкой; DDL с `CHECK`, 2 FK, индекс | OK |

Примечание по методу: первые попытки сценариев 7, 9 и 10 дали ложные результаты из-за моего скрипта (коллизия `attempt` при сидировании, `409` из-за уже висящих `pending`-сдач ученика, автоследование редиректу `TestClient`). Скрипт исправлен, сценарии прогнаны заново на чистой базе; в таблице — результаты повторных прогонов.

### Блок 4. Сохранённое поведение

Команда: `pytest tests/test_us3_submissions.py tests/test_us4_review.py tests/test_us5_my_attempts.py tests/test_review_queue_task_filter.py tests/test_path_id_overflow_404.py` → `124 passed`.

| Что | Покрывающие зелёные тесты | Затронутое фичей место, подтверждённое прогоном | |
|---|---|---|---|
| US-3 (сдача, попытки, блокировка) | `test_us3_ac1…ac5_*` (16 тестов) | Фича не меняет `create_submission`; новая попытка после комментария и вердикта → `303` (прогон 9) | OK |
| US-4 (очередь, ревью, 409, 403) | `test_us4_ac1…ac4_*` (11) | Форма ревью на странице сдачи; ревью без вердикта → `400` с комментариями (прогон 8); ревью после комментария → `303` (прогон 9); `test_baseline_review_unchanged_with_comments` | OK |
| US-5 (мои попытки, чужая сдача 404, экранирование) | `test_us5_ac1…ac3_*` (11) | Код теперь рендерится из `code_lines`; экранирование кода и комментариев (прогон 1); чужой ученик → `404` (прогон 4) | OK |
| RQF-1…12 (очередь по задаче) | `test_rqf1…rqf12_*` (27) | RQF-8 (страница сдачи сохраняет фильтр), RQF-10 (нет open redirect), RQF-11 (400 сохраняет фильтр): форма комментария повторяет эти правила (прогон 6) | OK |
| path-id-bounds (4 требования) | `test_*_overflow_id_is_404_not_500`, `non_numeric`, `in_range_missing` (16) | Новый маршрут: `99999999999999999999` → `404` (прогон 5) | OK |

## 3. Находки

Critical: нет. Major: нет.

- **m1 (minor)** `app/models.py:79` — индекс `ix_line_comments_order (submission_id, line, created_at, id)` не упомянут в LC-01 (контракт перечисляет только поля и ограничения). Существующие таблицы не затронуты, `create_all` создаёт его на старой базе (прогон 11). Воспроизведение: прогон 11, вывод DDL.
- **m2 (minor)** `app/web/line_comments.py:126` — при `ValidationError` страница сдачи загружается дважды: `get_submission_for` в роуте и затем `list_line_comments` внутри `render_submission`. Поведение корректное (повторяет схему `app/web/review.py:54`), лишний запрос не влияет на результат.
- **m3 (minor)** `app/templates/_code.html:5` — на каждую строку кода делается `selectattr("line","equalto",loop.index)` по всему списку комментариев: O(строки × комментарии). При лимитах проекта на размер кода и текста заметной проблемы нет, воспроизведения с ошибкой нет.
