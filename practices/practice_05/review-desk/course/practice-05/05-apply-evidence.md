# Журнал apply: review-queue-task-filter

Команда тестов фичи: `.venv/bin/python -m pytest tests/test_review_queue_task_filter.py -q`.
Окружение: Python 3.14 (.venv), FastAPI 0.162.0.

## Группа 1. Исходная точка (1.1)

`sh scripts/check.sh` до любых изменений:
```
88 passed, 1 warning in 1.78s
CHECK: PASS
```
База: 88 тестов. Предупреждение — `StarletteDeprecationWarning` про `httpx` в `fastapi.testclient`, оно было и до фичи.

## Группа 2. Фильтрация очереди и ошибки фильтра (2.1, 2.2: RQF-1, RQF-3, RQF-4, RQF-5)

Тесты в `tests/test_review_queue_task_filter.py`:
- `test_rqf1_filter_shows_only_pending_of_task_oldest_first` (S1);
- `test_rqf1_empty_value_means_no_filter` (S3);
- `test_rqf1_repeated_param_last_wins` (S8);
- `test_rqf3_unknown_task_is_404` (S6), `test_rqf3_int64_max_is_404_not_500` (S6b);
- `test_rqf4_non_numeric_was_ignored_now_404` (S7a);
- `test_rqf4_invalid_values_are_404[13 значений]` (S7b);
- `test_rqf5_student_gets_403_with_any_value[4 значения]` (S9);
- `test_rqf5_anonymous_redirected_to_login` (S10).

До реализации:
```
FAILED test_rqf1_filter_shows_only_pending_of_task_oldest_first
FAILED test_rqf1_repeated_param_last_wins
FAILED test_rqf3_unknown_task_is_404
FAILED test_rqf3_int64_max_is_404_not_500
FAILED test_rqf4_non_numeric_was_ignored_now_404
FAILED test_rqf4_invalid_values_are_404[0] [-1] [05] [ 5] [+5] [5.0] [1_000] [1e3] [٥] [²] [9223372036854775808] [99999999999999999999] [   ]
18 failed, 6 passed in 0.58s
```
Проходят до реализации (сохранённое поведение, как помечено в tasks.md 2.1): `test_rqf1_empty_value_means_no_filter` (S3), `test_rqf5_student_gets_403_with_any_value[existing|abc|9999|]` (S9), `test_rqf5_anonymous_redirected_to_login` (S10).

Изменённые файлы:
- `app/services/reviews.py`: `parse_assignment_filter`, `get_queue_filter`, `queue_filter_or_none`, необязательный параметр `assignment` в `pending_queue`;
- `app/web/review.py`: `GET /review` принимает `assignment_id: str | None = None` и вызывает `get_queue_filter`.

После (тесты фичи вместе с `tests/test_us4_review.py`):
```
43 passed in 1.03s
```

## Группа 3. Страница очереди: форма, заголовок, пустые состояния, ссылки (3.1, 3.2: RQF-2, RQF-6, RQF-7, RQF-12)

Тесты:
- `test_rqf2_task_without_pending_shows_filtered_empty_state` (S4);
- `test_rqf2_unfiltered_empty_keeps_general_message` (S5);
- `test_rqf6_form_without_filter` (S11a);
- `test_rqf6_form_marks_selected_task_and_reset_link` (S11b);
- `test_rqf7_open_links_carry_filter_only_when_active` (S12);
- `test_rqf12_task_title_escaped` (S20, часть про очередь).

До реализации (весь файл: 5 failed, 25 passed; ниже только тесты группы 3):
```
FAILED test_rqf2_task_without_pending_shows_filtered_empty_state
FAILED test_rqf6_form_without_filter
FAILED test_rqf6_form_marks_selected_task_and_reset_link
FAILED test_rqf7_open_links_carry_filter_only_when_active
FAILED test_rqf12_task_title_escaped
5 failed, 25 passed in 0.70s
```
Проходит до реализации: `test_rqf2_unfiltered_empty_keeps_general_message` (S5). Это сохранённое поведение baseline, хотя tasks.md 3.1 его так не пометил.

Изменённые файлы:
- `app/templates/review/queue.html`:
  - заголовок и `<title>` с названием задачи;
  - GET-форма с `<select name="assignment_id">`, пунктом «Все задачи» `value=""` и кнопкой «Показать»;
  - «Сбросить фильтр» при активном фильтре;
  - `?assignment_id=N` в «Открыть» только при фильтре;
  - отдельное пустое состояние для отфильтрованной очереди.

  `|safe` не используется, подстроки `/submissions/` в форме нет.
- `app/web/review.py`: в контекст шаблона добавлены `queue_filter` и `assignments` (`assignment_service.list_assignments`).

После (тесты фичи вместе с `tests/test_us4_review.py`):
```
49 passed
```

## Группа 4. Страница сдачи сохраняет фильтр (4.1, 4.2: RQF-8)

Тесты:
- `test_rqf8_submission_page_keeps_filter` (S13);
- `test_rqf8_filter_for_other_task_is_kept` (S13b);
- `test_rqf8_submission_page_ignores_invalid_filter[abc|0|9999|99999999999999999999]` (S14);
- `test_rqf8_no_hidden_field_without_filter` (S14b);
- `test_rqf8_student_unaffected_by_param` (S14c).

До реализации (весь файл):
```
FAILED test_rqf8_submission_page_keeps_filter
FAILED test_rqf8_filter_for_other_task_is_kept
2 failed, 36 passed in 0.92s
```
Проходят до реализации, как помечено в tasks.md 4.1: S14 (все 4 значения), S14b, S14c.

Изменённые файлы:
- `app/web/submissions.py`:
  - хелпер `review_queue_url` рядом с `render_submission`;
  - у `render_submission` новый именованный параметр `queue_filter`, в контекст добавлены `queue_filter` и `queue_url`;
  - `submission_detail` принимает `assignment_id: str | None = None` и вызывает `queue_filter_or_none` только для ментора.
- `app/templates/submissions/detail.html`: ссылка «← Очередь ревью» ведёт на `{{ queue_url }}`; скрытое поле `assignment_id` выводится только при `queue_filter`.

После (тесты фичи вместе с `tests/test_us4_review.py` и `tests/test_us5_my_attempts.py`):
```
68 passed in 1.71s
```

## Группа 5. POST ревью: редирект, фолбэк, ошибки (5.1, 5.2: RQF-9, RQF-10, RQF-11)

Тесты:
- `test_rqf9_review_redirects_to_filtered_queue` (S15);
- `test_rqf9_review_without_filter_redirects_to_plain_queue[без поля|пустое]` (S16);
- `test_rqf9_last_review_lands_on_filtered_empty_state` (S19);
- `test_rqf10_bad_filter_falls_back_no_open_redirect[abc|0|05|9999|99999999999999999999|//evil.example|https://evil.example/|/review?x=1|1/../../evil]` (S17);
- `test_rqf11_invalid_review_keeps_filter` (S18);
- `test_rqf11_second_review_with_filter_is_409` (S18b).

До реализации (весь файл):
```
FAILED test_rqf9_review_redirects_to_filtered_queue
FAILED test_rqf9_last_review_lands_on_filtered_empty_state
FAILED test_rqf11_invalid_review_keeps_filter
3 failed, 50 passed in 1.30s
```
Проходят до реализации, как помечено в tasks.md 5.1: S16 (оба варианта), S17 (все 9 значений), S18b.

Изменённые файлы:
- `app/web/review.py`: `create_review` принимает `assignment_id: str | None = Form(None)` и вызывает `queue_filter_or_none` до `create_review`. Успех даёт `RedirectResponse(review_queue_url(queue_filter), 303)`, `ValidationError` даёт `render_submission(..., status_code=400, queue_filter=queue_filter)`. Хелпер `review_queue_url` импортируется из `app/web/submissions.py`.

После (тесты фичи вместе с `tests/test_us4_review.py`):
```
72 passed in 1.89s
```

## Группа 6. Итоговая проверка (6.1, 6.2, 6.3)

6.1. У каждого сценария S1, S3–S20 (включая S6b, S7a/b, S11a/b, S13b, S14b/c, S18b) есть тест с `RQF-N / S<k>` в docstring, все 12 требований RQF-1…RQF-12 покрыты. S2 покрыт baseline-тестом `test_us4_ac1_queue_shows_only_pending_oldest_first`, ссылка на него стоит в docstring модуля. В файле 26 тест-функций, с параметризацией 53 теста.

6.2. `tests/test_us*.py`, `tests/conftest.py`, `docs/baseline.md`, `scripts/check.sh` и `requirements.txt` не изменены (`git diff --quiet` по ним проходит).

6.3. `sh scripts/check.sh` целиком:
```
........................................................................ [ 51%]
.....................................................................    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/testclient.py:1
  /home/ivan_korchagin/ITMOv2/practices/practice_05/review-desk/.venv/lib/python3.14/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
141 passed, 1 warning in 3.04s
CHECK: PASS
```
Итог: 141 тест (было 88, добавлено 53). Коммит не делался.

`git -C ~/ITMOv2 status --short`:
```
 M practices/practice_05/review-desk/app/services/reviews.py
 M practices/practice_05/review-desk/app/templates/review/queue.html
 M practices/practice_05/review-desk/app/templates/submissions/detail.html
 M practices/practice_05/review-desk/app/web/review.py
 M practices/practice_05/review-desk/app/web/submissions.py
?? practices/practice_05/review-desk/course/
?? practices/practice_05/review-desk/openspec/changes/review-queue-task-filter/
?? practices/practice_05/review-desk/tests/test_review_queue_task_filter.py
```

`git -C ~/ITMOv2 diff --stat`:
```
 .../review-desk/app/services/reviews.py            | 52 +++++++++++++++++++---
 .../review-desk/app/templates/review/queue.html    | 20 +++++++--
 .../app/templates/submissions/detail.html          |  3 +-
 .../practice_05/review-desk/app/web/review.py      | 37 ++++++++++++---
 .../practice_05/review-desk/app/web/submissions.py | 26 +++++++++--
 5 files changed, 118 insertions(+), 20 deletions(-)
```
