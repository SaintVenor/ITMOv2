# Tasks

Порядок по AGENTS.md: сначала тест, показать его падение, затем минимальная реализация. Все тесты лежат в `tests/test_review_queue_task_filter.py`, называются `test_rqfN_...` и указывают `RQF-N / S<k>` в docstring. Тесты baseline (`tests/test_us4_review.py` и остальные) не меняются.

## 1. Исходная точка

- [x] 1.1 Запустить `sh scripts/check.sh` до любых изменений и убедиться, что выводится `CHECK: PASS`. Зафиксировать число тестов как базу.

## 2. Фильтрация очереди и ошибки фильтра (RQF-1, RQF-3, RQF-4, RQF-5)

- [x] 2.1 Написать тесты:
  - `test_rqf1_filter_shows_only_pending_of_task_oldest_first` (S1);
  - `test_rqf1_empty_value_means_no_filter` (S3);
  - `test_rqf1_repeated_param_last_wins` (S8);
  - `test_rqf3_unknown_task_is_404` и `test_rqf3_int64_max_is_404_not_500` (S6, S6b);
  - `test_rqf4_non_numeric_was_ignored_now_404` (S7a);
  - `test_rqf4_invalid_values_are_404[...]` с параметрами из S7b, значения передаются через `params=`;
  - `test_rqf5_student_gets_403_with_any_value[...]` (S9);
  - `test_rqf5_anonymous_redirected_to_login` (S10).

  Запустить `.venv/bin/pytest tests/test_review_queue_task_filter.py`, показать падение S1, S6, S7, S8. S3, S9 и S10 могут пройти уже сейчас: это проверка сохранённого поведения, отметить это.
- [x] 2.2 Реализовать в `app/services/reviews.py`:
  - `parse_assignment_filter`, `get_queue_filter`, `queue_filter_or_none` (design D2, D3);
  - необязательный параметр `assignment` в `pending_queue`.

  В `app/web/review.py` объявить `assignment_id: str | None = None` и вызывать `get_queue_filter` после `require_mentor`. Проверка: тесты из 2.1 зелёные, `tests/test_us4_review.py` зелёный.

## 3. Страница очереди: форма, заголовок, пустые состояния, ссылки (RQF-2, RQF-6, RQF-7, RQF-12)

- [x] 3.1 Написать тесты:
  - `test_rqf2_task_without_pending_shows_filtered_empty_state` (S4);
  - `test_rqf2_unfiltered_empty_keeps_general_message` (S5);
  - `test_rqf6_form_without_filter` (S11a) и `test_rqf6_form_marks_selected_task_and_reset_link` (S11b);
  - `test_rqf7_open_links_carry_filter_only_when_active` (S12);
  - `test_rqf12_task_title_escaped` (S20).

  Показать их падение.
- [x] 3.2 Обновить `app/templates/review/queue.html` и контекст роута `/review` (`assignments.list_assignments`, `queue_filter`) по design D6, без `|safe` и без подстроки `/submissions/` в форме. Проверка: тесты из 3.1 зелёные. `test_us4_ac1_queue_shows_only_pending_oldest_first` и `test_us4_ac1_empty_queue` по-прежнему зелёные.

## 4. Страница сдачи сохраняет фильтр (RQF-8)

- [x] 4.1 Написать тесты:
  - `test_rqf8_submission_page_keeps_filter` (S13);
  - `test_rqf8_filter_for_other_task_is_kept` (S13b);
  - `test_rqf8_submission_page_ignores_invalid_filter[...]` (S14);
  - `test_rqf8_no_hidden_field_without_filter` (S14b);
  - `test_rqf8_student_unaffected_by_param` (S14c).

  Показать падение S13 и S13b. S14, S14b и S14c могут пройти уже сейчас, отметить это.
- [x] 4.2 Добавить `review_queue_url` в `app/web/submissions.py` рядом с `render_submission` (design D4, там же объяснено, почему не в `review.py`). В `render_submission` добавить параметр `queue_filter` и `queue_url` в контекст. В `submission_detail` добавить `assignment_id: str | None = None` и вызов `queue_filter_or_none` только для ментора. Обновить `detail.html`: ссылка «← Очередь ревью» через `queue_url`, скрытое поле только при `queue_filter`. Проверка: тесты из 4.1 зелёные, `tests/test_us4_review.py` и `tests/test_us5_my_attempts.py` зелёные.
## 5. POST ревью: редирект, фолбэк, ошибки (RQF-9, RQF-10, RQF-11)

- [x] 5.1 Написать тесты:
  - `test_rqf9_review_redirects_to_filtered_queue` (S15);
  - `test_rqf9_review_without_filter_redirects_to_plain_queue` (S16, без поля и с пустым полем);
  - `test_rqf9_last_review_lands_on_filtered_empty_state` (S19);
  - `test_rqf10_bad_filter_falls_back_no_open_redirect[...]` (S17, проверить также, что ревью сохранено);
  - `test_rqf11_invalid_review_keeps_filter` (S18);
  - `test_rqf11_second_review_with_filter_is_409` (S18b).

  Показать падение S15, S19 и S18. S16, S17 и S18b могут пройти уже сейчас, отметить это.
- [x] 5.2 В `create_review` (`app/web/review.py`) добавить `assignment_id: str | None = Form(None)` и `queue_filter_or_none`. Успех даёт `RedirectResponse(review_queue_url(...), 303)`, `ValidationError` даёт `render_submission(..., queue_filter=...)` (design D5). Проверка: тесты из 5.1 зелёные. `test_us4_ac2_review_saves_verdict_comment_and_updates_status` (`Location == "/review"`) и `test_us4_ac2_invalid_review_rejected` зелёные.

## 6. Итоговая проверка

- [x] 6.1 Сверить, что каждый сценарий S1–S20 (включая S6b, S7a/b, S11a/b, S13b, S14b/c, S18b) имеет тест с `RQF-N / S<k>` в docstring. Исключение — S2: он покрыт `test_us4_ac1_queue_shows_only_pending_oldest_first`, сослаться на него в комментарии файла.
- [x] 6.2 Убедиться, что ни один файл в `tests/test_us*.py`, `docs/baseline.md` и `scripts/check.sh` не изменён, а `requirements.txt` не тронут (`git diff --stat`).
- [x] 6.3 Запустить `sh scripts/check.sh` и убедиться, что выводится `CHECK: PASS`.
