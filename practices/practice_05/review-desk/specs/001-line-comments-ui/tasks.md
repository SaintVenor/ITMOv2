# Tasks: Построчные комментарии ментора к коду сдачи: интерфейс

**Input**: `specs/001-line-comments-ui/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md) и общий контракт `specs/line-comments-contract.md` (LC-01…LC-29; главнее спеки).

**Prerequisites**: логика реализована и закоммичена (LC-28): `app/services/line_comments.py`, `app/web/line_comments.py`, `render_submission` (контекст LC-11), `tests/test_line_comments.py`.

**Tests**: обязательны (`AGENTS.md`, «Процесс»: сначала тест, показать падение, затем минимальная реализация). Тесты - в `tests/test_line_comments_ui.py`; docstring каждого теста начинается с `[UI FR-nnn]` и содержит `LC-nn` (LC-29).

**Зона UI (LC-27)**: `app/templates/_code.html`, новые `app/templates/_line_comment.html` и `app/templates/_line_comment_form.html`, `app/templates/submissions/detail.html`, `app/static/style.css`, `tests/test_line_comments_ui.py` (+ сквозной `tests/test_line_comments_e2e.py` по поручению). Python в `app/services/` и `app/web/` не меняется. Если для экрана не хватает данных в контексте - остановиться и спросить.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно параллельно (разные файлы, нет зависимости от незавершённых задач)
- **[Story]**: US1 - ментор комментирует; US2 - ученик видит; US3 - состояния и ошибки
- Пометка **«ожидается зелёный до реализации»**: тест проходит уже на текущей логике; его показывают зелёным и не подгоняют
- Пометка **«ожидается красный»**: тест должен упасть до реализации; вывод pytest показывают
- Пути сверены с диском: существуют `app/templates/_code.html`, `app/templates/_field_error.html`, `app/templates/submissions/detail.html`, `app/static/style.css`, `tests/conftest.py`; создаются по LC-27: `app/templates/_line_comment.html`, `app/templates/_line_comment_form.html`, `tests/test_line_comments_ui.py`, `tests/test_line_comments_e2e.py`

## Phase 1: Setup

- [X] T001 Создать `tests/test_line_comments_ui.py`: docstring модуля (зона UI, `[UI FR-nnn]` и `LC-NN`, LC-29), хелперы поверх фикстур `tests/conftest.py` (`mentor_client`, `student_client`, `make_client`, `make_submission`, `assignment`, `db_session`): `post_comment(client, submission_id, line, text, assignment_id=None)` с **полным** телом формы (`line`, `text`) и `follow_redirects=False`; `add_comment(db, submission, author, line, text)` (создание `LineComment` напрямую, как в `tests/test_line_comments.py`); `count_comments(db)`. Проверки HTML только по устойчивым признакам (`id="L3"`, `data-field="line"`, `name="text"`, `maxlength="2000"`), не по целым кускам разметки. [LC-29, LC-27]

## Phase 2: Foundational (блокирует все истории): строки кода с номерами и якорями

**Цель**: код выводится строками из `code_lines` (LC-04, LC-11) с видимым номером и `id="L{n}"`; шаблон код сам не делит.

- [X] T002 Тесты FR-001 в `tests/test_line_comments_ui.py` (ожидается красный): `test_fr001_code_rows_numbered_with_anchors` - ментор и ученик-автор видят у кода из 3 строк `id="L1"`, `id="L2"`, `id="L3"` и нет `id="L4"`; видимый номер в `span.line-no`; `test_fr001_numbering_follows_lc04` - код `"a\r\nb\rc\n"` даёт ровно `L1`..`L3` (нет `L4`), код из одной строки даёт только `L1`, пустая строка в середине (`"a\n\nb"`) имеет свой номер `L2`; docstring `[UI FR-001] LC-04, LC-05, LC-11, LC-18`
- [X] T003 Тест FR-014 в `tests/test_line_comments_ui.py` (**ожидается зелёный до реализации**, не подгонять): `test_fr014_no_safe_filter_in_templates` - в `app/templates/**/*.html` нет подстроки `|safe`; docstring `[UI FR-014] LC-19`
- [X] T004 Тест FR-015 в `tests/test_line_comments_ui.py` (**ожидается зелёный до реализации**): `test_fr015_page_has_no_javascript` - страница сдачи ментора и ученика не содержит `<script`; docstring `[UI FR-015]`
- [X] T005 Запустить `pytest tests/test_line_comments_ui.py` и показать падение T002 (T003, T004 зелёные)
- [X] T006 Переписать макрос в `app/templates/_code.html`: принимает `code_lines` и `line_comments`; для каждой строки `div.code-row#L{n}` (n из `loop.index`), внутри `span.line-no` (номер текстом) и `code.line-text`; код выводится автоэкранированием, без `|safe`, без `.split`; сигнатура допускает вызов из `detail.html` с контекстом LC-11. [UI FR-001, FR-014, LC-04, LC-11, LC-18]
- [X] T007 В `app/templates/submissions/detail.html` заменить `{{ code_block(submission.code) }}` на вызов нового макроса с `code_lines` и `line_comments`. [UI FR-001, LC-11]
- [X] T008 [P] В `app/static/style.css` заменить `pre.code`-счётчик на стили `.code`, `.code-row`, `.line-no`, `.line-text` (`white-space: pre`, `overflow-x: auto` у `.code`; тема светлая/тёмная через существующие переменные). [UI FR-001, FR-015; research R-2, R-3]
- [X] T009 Запустить `pytest`: T002 зелёный; существующие тесты (`test_us5_ac3_code_is_html_escaped` и остальные baseline) зелёные без правок. [UI FR-016, FR-014]

**Checkpoint**: у каждой строки номер и якорь; baseline не сломан.

## Phase 3: User Story 1 - Ментор комментирует строку (Priority: P1) MVP

**Независимый тест**: ментор открывает сдачу, отправляет форму «номер + текст», видит комментарий под строкой.

### Тесты US1 (сначала; в `tests/test_line_comments_ui.py`)

- [X] T010 [US1] `test_fr002_mentor_sees_single_form_without_comment_links` (ожидается красный): у ментора есть `id="line-comment-form"` с `action="/submissions/{id}/line-comments"`, `name="line"`, `inputmode="numeric"`, `name="text"`, `maxlength="2000"`, кнопка «Отправить»; форма ровно одна; нет текста «Комментировать»; адрес страницы без числовых параметров выбора строки. `[UI FR-002, FR-004] LC-06, LC-09, LC-18`
- [X] T011 [US1] `test_fr004_hidden_assignment_id_only_with_queue_filter` (ожидается красный): `GET /submissions/{id}?assignment_id=K` - скрытое поле `name="assignment_id"` со значением K; без фильтра и с мусорным `abc` - поля нет. `[UI FR-004] LC-13, LC-18`
- [X] T012 [US1] `test_fr003_form_visible_in_any_status` (ожидается красный): форма видна на сдаче `pending`, `accepted` и `changes_requested` (с ревью); форма ревью baseline на сдаче с ревью по-прежнему показывает ревью. `[UI FR-003] LC-23`
- [X] T013 [US1] `test_fr005_success_redirects_to_anchor` (**ожидается зелёный до реализации**): POST `line=2`, `text` валидный → `303`, `Location == /submissions/{id}#L2`; с `assignment_id=K` → `...?assignment_id=K#L2`; с мусором `//evil.example` → без query. `[UI FR-005, FR-016] LC-10, LC-13`
- [X] T014 [US1] `test_fr006_comment_under_own_line_with_author_and_date` (ожидается красный): после POST комментарий `article.line-comment#comment-<id>` находится после `id="L2"` и до `id="L3"`, виден `display_name` автора, дата в формате фильтра `dt` и текст. `[UI FR-006] LC-02, LC-18`
- [X] T015 [US1] `test_fr006_two_comments_same_line_in_creation_order` (ожидается красный): два комментария к строке 2 - первый выше второго. `[UI FR-006] LC-03`
- [X] T016 [US1] `test_fr007_commented_row_is_marked` (ожидается красный): строка с комментарием имеет класс `code-row--commented`, строка без - нет. `[UI FR-007] LC-18`
- [X] T017 [US1] `test_fr018_mentor_sees_comments_of_other_mentors` (ожидается красный): два ментора (второй создаётся в тесте через `auth.create_user(db_session, "mentor2", PASSWORD, "mentor", "Ментор Два")`; `PASSWORD` из `tests/conftest.py`), каждый видит комментарии обоих с именами. `[UI FR-018] LC-21`
- [X] T018 [US1] `test_fr016_queue_link_keeps_filter_after_400` (ожидается красный: ошибка у `text` ещё не выводится; ссылка очереди и `400` уже верны): POST с `assignment_id=K` и пустым `text` (поле `line=1` валидно) → `400`, ссылка «← Очередь ревью» ведёт на `/review?assignment_id=K`; проверка, что ошибка именно у `text`, а не 404. `[UI FR-016] LC-13`
- [X] T019 [US1] Запустить `pytest tests/test_line_comments_ui.py`, показать падение T010-T012, T014-T018 и зелёный T013

### Реализация US1

- [X] T020 [P] [US1] Создать `app/templates/_line_comment.html`: один `article.line-comment#comment-{{ c.id }}` с `.line-comment-author` (`c.author`), датой (`c.created_at | dt`, `time`/`.muted`) и `.line-comment-text` (автоэкранирование, без `|safe`). Читает только поля `LineCommentView` (LC-02). [UI FR-006, FR-014, LC-02]
- [X] T021 [US1] В `app/templates/_code.html` под каждой строкой вывести `div.line-comments` с комментариями этой строки (группировка по `c.line == loop.index` в шаблоне, порядок от сервиса, LC-03), include `_line_comment.html`; строке с комментариями добавить класс `code-row--commented`. [UI FR-006, FR-007, LC-03]
- [X] T022 [P] [US1] Создать `app/templates/_line_comment_form.html`: `form#line-comment-form` (`method="post"`, `action="/submissions/{{ submission.id }}/line-comments"`, класс `form`), скрытое `assignment_id` при `queue_filter`, `input name="line"` (`inputmode="numeric"`, значение из `line_comment_form.line`), `textarea name="text"` (`maxlength="{{ line_comment_max }}"`, значение из `line_comment_form.text`), кнопка «Отправить»; ошибки полей через `_field_error.html` c `errors = line_comment_errors` (`data-field="line"` / `"text"`); `aria-invalid` при ошибке. Ключ `errors` (ревью) не используется. [UI FR-002, FR-004, LC-06, LC-11, LC-13, LC-16, LC-18]
- [X] T023 [US1] В `app/templates/submissions/detail.html` под кодом показать форму: `{% if can_comment %}{% include "_line_comment_form.html" %}{% endif %}`, независимо от статуса и ревью; форма ревью не менять. [UI FR-002, FR-003, LC-23]
- [X] T024 [P] [US1] В `app/static/style.css` стили `.line-comments`, `.line-comment`, `.line-comment-author`, `.line-comment-text` (`white-space: pre-wrap; overflow-wrap: anywhere`), `.code-row--commented` (отличимая подсветка), форма комментария. [UI FR-007, FR-006; research R-3]
- [X] T025 [US1] Запустить `pytest`: T010-T018 зелёные, baseline зелёный без правок. [UI FR-002…FR-007, FR-016, FR-018]

**Checkpoint**: US1 работает независимо.

## Phase 4: User Story 2 - Ученик видит комментарии (Priority: P1)

**Независимый тест**: ученик-автор видит комментарий под нужной строкой без формы.

### Тесты US2 (сначала)

- [X] T026 [US2] `test_fr008_student_sees_comments_under_lines_3_and_7_without_form` (ожидается красный): комментарии к строкам 3 и 7 в позициях под своими строками, к остальным нет. `[UI FR-008, FR-006] LC-19`
- [X] T027 [US2] `test_fr017_student_sees_comment_while_pending` (ожидается красный): сдача `pending` без ревью, комментарий виден ученику сразу. `[UI FR-017] LC-24`
- [X] T028 [US2] `test_fr008_student_has_no_comment_form_controls` (**ожидается зелёный до реализации**, не подгонять; должен остаться зелёным после): страница ученика без формы комментария. `[UI FR-008] LC-19`
- [X] T029 [US2] `test_fr009_foreign_student_gets_404_without_comments` (**ожидается зелёный до реализации**): другой ученик открывает чужую сдачу с комментарием → `404`, заголовок «Не найдено» (не текст сообщения, LC-17), текст комментария в ответе отсутствует. `[UI FR-009] LC-14, LC-17`
- [X] T030 [US2] `test_fr010_student_post_is_403_even_for_missing_submission` (**ожидается зелёный до реализации**): ученик отправляет **полное валидное тело** на свою сдачу и на `999999` → оба `403`, заголовок «Доступ запрещён», комментарий не создан. `[UI FR-010] LC-14`
- [X] T031 [US2] `test_fr014_comment_text_is_escaped_for_student_and_mentor` (ожидается красный): комментарий `<b>x</b> & <script>alert(1)</script>` - в HTML есть `&lt;b&gt;`, нет сырого `<b>x</b>` и `<script>alert`; для ученика и ментора. `[UI FR-014] LC-19`
- [X] T032 [US2] `test_fr019_new_attempt_has_own_empty_state` (ожидается красный): две попытки одной задачи, комментарий только к первой: страница второй показывает «Комментариев к строкам пока нет» и не показывает текст комментария; страница первой показывает текст. `[UI FR-019] LC-22, LC-20`
- [X] T033 [US2] Запустить `pytest tests/test_line_comments_ui.py`, показать падение T026, T027, T031, T032 и зелёные T028-T030

### Реализация US2

- [X] T034 [US2] Проверить без правок кода, что `_code.html`/`detail.html` из US1 выводят комментарии для роли `student` (`can_comment = False` скрывает только форму) - тесты T026-T032 зелёные; при падении - минимальная правка шаблонов в зоне LC-27. [UI FR-008, FR-017, FR-019, LC-19, LC-24]
- [X] T035 [US2] Запустить `pytest`: T026-T032 зелёные, baseline зелёный (в том числе US-5 AC2/AC3). [UI FR-008…FR-010, FR-014, FR-017, FR-019]

**Checkpoint**: US1 и US2 работают независимо.

## Phase 5: User Story 3 - Состояния и ошибки (Priority: P2)

**Независимый тест**: пустой комментарий → ошибка у поля с сохранённым вводом; сдача без комментариев → подсказка.

### Тесты US3 (сначала)

- [X] T036 [US3] `test_fr011_empty_state_for_mentor_and_student` (ожидается красный): сдача без комментариев - `id="no-line-comments"` и текст «Комментариев к строкам пока нет» у ментора и ученика; при наличии комментария - нет. `[UI FR-011] LC-20`
- [X] T037 [US3] `test_fr011_no_empty_state_after_failed_review_rerender` (ожидается красный): сдача с комментарием, `POST /submissions/{id}/review` с валидным `comment` и **без** `verdict` → `400`, ошибка именно у `verdict` (`data-field="verdict"`), комментарий показан, подсказки нет. `[UI FR-011, FR-016] LC-12, LC-20`
- [X] T038 [US3] `test_fr012_empty_text_400_error_and_input_kept` (ожидается красный): `line=2`, `text="   "` → `400`, `data-field="text"` есть, `data-field="line"` нет, в форме сохранён `2`, комментарий не создан. `[UI FR-012] LC-14, LC-16`
- [X] T039 [US3] `test_fr012_too_long_text_400_input_kept` (ожидается красный): `text="x" * 2001` → `400`, `data-field="text"`, введённый текст в ответе, номер сохранён, комментарий не создан. `[UI FR-012] LC-06, LC-16`
- [X] T040 [US3] `test_fr013_invalid_line_400_error_at_line_text_kept` (ожидается красный): параметризовать `line` из `["99", "05", "abc", "0"]` (сверка с LC-15) с валидным `text="x"` → `400`, `data-field="line"`, нет `data-field="text"`, текст `x` в форме, значение `line` возвращено, комментарий не создан. `[UI FR-013] LC-15, LC-16, LC-25`
- [X] T041 [US3] `test_fr013_both_fields_invalid_show_both_errors` (ожидается красный): `line="99"`, `text=""` → оба `data-field`. `[UI FR-013] LC-14, LC-16`
- [X] T042 [US3] `test_fr013_missing_submission_404_not_400` (**ожидается зелёный до реализации**): ментор, **полное валидное тело**, id `999999` и `99999999999999999999` → `404`, заголовок «Не найдено» (текст сообщения не проверяется, LC-17), комментарий не создан. `[UI FR-013] LC-14, LC-17`
- [X] T043 [US3] `test_fr014_form_values_escaped_on_400` (ожидается красный): `text='"><script>alert(1)</script>'` + `line="99"` → в HTML нет сырого `<script>alert`, есть экранированный вид, значение возвращено в форму. `[UI FR-014] LC-16`
- [X] T044 [US3] `test_fr016_anonymous_post_redirects_to_login` (**ожидается зелёный до реализации**): без сессии POST с полным телом → `303` на `/login`. `[UI FR-016] LC-14`
- [X] T045 [US3] Запустить `pytest tests/test_line_comments_ui.py`, показать падение T036-T041, T043 и зелёные T042, T044

### Реализация US3

- [X] T046 [US3] В `app/templates/submissions/detail.html` добавить над кодом `p.muted#no-line-comments` «Комментариев к строкам пока нет» при `not line_comments`, для всех ролей; вёрстка кода и форма ревью не меняются. [UI FR-011, LC-20]
- [X] T047 [US3] Проверить, что `_line_comment_form.html` (T022) выводит ошибки `line`/`text` через `_field_error.html` и возвращает значения `line_comment_form`; при расхождении с T038-T043 - минимальная правка шаблона. [UI FR-012, FR-013, FR-014, LC-16]
- [X] T048 [P] [US3] В `app/static/style.css` стиль подсказки и ошибки поля формы комментария (повторное использование `.field-error`, `[aria-invalid="true"]`). [UI FR-011, FR-012]
- [X] T049 [US3] Запустить `pytest`: T036-T044 зелёные, baseline зелёный. [UI FR-011…FR-013]

**Checkpoint**: все три истории работают.

## Phase 6: Polish

- [X] T050 Прогнать `sh scripts/check.sh | tail -3` - `CHECK: PASS`; `grep -rn '|safe' app/templates` - пусто. [UI FR-014, FR-016]
- [X] T051 Сверить `quickstart.md` пункты 1-10 с тестами `tests/test_line_comments_ui.py`: каждый пункт покрыт тестом (таблица покрытия - в итоговом отчёте). [UI FR-001…FR-019]

## Phase 7: Сквозной тест (последняя задача)

- [X] T052 Создать `tests/test_line_comments_e2e.py` (`fastapi.testclient`, настоящие роуты и сервис, фикстуры `conftest.py`); docstring каждого теста `[UI FR-nnn] [Л FR-nnn] LC-nn` (LC-29); в каждом POST-тесте полное тело формы и проверка, что ошибка именно та. Три сценария:
  1. `test_e2e_mentor_comments_line_2_student_sees_escaped`: ментор POST `line=2`, `text="<b>важно</b>"` → `303`, `Location` оканчивается `#L2`; ученик-автор открывает сдачу: `&lt;b&gt;важно&lt;/b&gt;` в HTML после `id="L2"` и до `id="L3"`, сырого `<b>важно` нет, формы нет. `[UI FR-005, FR-006, FR-008, FR-014] [Л FR-004, FR-013, FR-017] LC-10, LC-19`
  2. `test_e2e_boundary_line_n_plus_1_and_int64_overflow`: для кода из N строк `line=str(N+1)` и `line="9223372036854775808"` (с валидным `text`) → оба `400`, `data-field="line"`, ввод (`line`, `text`) сохранён в форме, `LineComment` не создан (счётчик в БД не вырос); контроль: `line=str(N)` → `303`. `[UI FR-013] [Л FR-005, FR-014] LC-14, LC-15, LC-16, LC-25`
  3. `test_e2e_foreign_student_gets_404_without_comments`: другой ученик открывает чужую сдачу с комментарием → `404`, «Не найдено», текста комментария нет. `[UI FR-009] [Л FR-009] LC-14, LC-17, LC-19`
  Номера `[Л FR-nnn]` сверены с `specs/002-line-comments-logic/spec.md`. Тест пишется после реализации (последняя задача по поручению): сценарий 3 зелёный и до реализации (**ожидается зелёный до реализации**); сценарии 1 и 2 на базе `a012d4c` красные (нет вывода комментариев, ошибок полей и возврата ввода в форму) и зелёные после US1-US3. Запустить `sh scripts/check.sh | tail -3` - `CHECK: PASS`.

## Dependencies & Execution Order

- Phase 1 → Phase 2 (блокирует всё) → US1 → US2 → US3 → Polish → e2e (T052 последняя).
- Внутри каждой истории: тесты → запуск и показ падения → реализация → запуск и зелёный.
- US2 использует вывод комментариев из US1 (T021); US3 использует форму из T022.
- Файлы `detail.html`, `_code.html`, `style.css` правятся последовательно между историями (общие файлы, без `[P]` на пересекающихся задачах).

## Parallel Opportunities

- Тест-задачи одной истории пишутся в один файл `tests/test_line_comments_ui.py`, поэтому без `[P]`; записываются подряд.
- T020, T022, T024 - разные файлы (`_line_comment.html`, `_line_comment_form.html`, `style.css`).

## Implementation Strategy

MVP = Phase 1 + 2 + US1 (ментор оставляет и видит комментарий); затем US2 (ученик читает), US3 (состояния и ошибки), Polish и сквозной тест. `docs/architecture.md` (таблица страниц) не обновляется: файл вне зоны LC-27 и вне `specs/`, `AGENTS.md` запрещает менять структуру без согласования; вопрос - в итоговый отчёт.
