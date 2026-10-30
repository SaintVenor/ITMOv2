# ДЗ 5 «Две команды - одна фича»: оглавление для защиты

Фича: построчные комментарии ментора к коду сдачи. Проект: `practices/practice_05/review-desk`,
ветка `homework-05`. Фреймворк: Spec Kit 1.2.5 (сравнение с OpenSpec из практики 5).
Пути ниже - от `review-desk/`.

## 1. Другой SDD-фреймворк и сравнение с OpenSpec (2)

| Что | Где |
|---|---|
| Установка, версии, проверки после init | `course/homework-05/00-setup.md` |
| Конституция Spec Kit и лог её создания | `.specify/memory/constitution.md`, `course/homework-05/00-constitution-session.md` |
| Сравнение Spec Kit и OpenSpec (по ходу и итог) | `course/homework-05/comparison-notes.md` |
| Опыт OpenSpec (практика 5) | `openspec/specs/`, `openspec/changes/archive/`, `course/practice-05/` |

## 2. Две спецификации, изоляция, контракт, решения (2)

| Что | Где |
|---|---|
| Бриф (одинаковый для обеих команд) | `course/homework-05/01-brief.md` |
| Изоляция: worktree, deny, автопамять, аудит логов, результаты | `course/homework-05/02-isolation.md` |
| Промпты всех сессий | `course/homework-05/prompts/` |
| Логи команд (specify, clarify + ответы) | `course/homework-05/team-ui/`, `course/homework-05/team-logic/` |
| Спеки **до** согласования | `course/homework-05/specs-before/ui/`, `course/homework-05/specs-before/logic/` |
| Сверка расхождений (данные / вызовы / ошибки / состояния) | `course/homework-05/03-contract-diff.md` |
| Решения Ивана | `course/homework-05/03-decisions.md` |
| Общий контракт LC-01...LC-29 | `specs/line-comments-contract.md` |
| Спеки **после** согласования | `specs/001-line-comments-ui/`, `specs/002-line-comments-logic/` |
| Дифф спек до → после | `course/homework-05/specs-diff.patch` |
| Логи согласования и обновления спек | `course/homework-05/04-contract-diff-session.md`, `course/homework-05/04-contract-update-session.md` |

## 3. Реализация: UI и логика, сквозной сценарий, ошибки и границы (5)

| Что | Где |
|---|---|
| Логика: модель, сервис, роут | `app/models.py` (`LineComment`), `app/services/line_comments.py`, `app/web/line_comments.py`, `app/web/submissions.py` (`render_submission`) |
| UI: шаблоны, стили | `app/templates/_code.html`, `app/templates/_line_comment.html`, `app/templates/_line_comment_form.html`, `app/templates/submissions/detail.html`, `app/static/style.css` |
| Задачи и analyze | `specs/00N-*/tasks.md`, `specs/00N-*/analyze-report.md` |
| Тесты логики (47), UI (29) | `tests/test_line_comments.py`, `tests/test_line_comments_ui.py` |
| Сквозной тест: комментарий → ученик видит; N+1 и int64 → 400; чужая сдача → 404 | `tests/test_line_comments_e2e.py` |
| Логи реализации | `course/homework-05/05-implement-logic-session.md`, `course/homework-05/05-implement-ui-session.md` |
| Коммиты | `a012d4c` (логика), `ba4dca1` (UI); база `4b1cf2e` |

## 4. Проверки

| Что | Где |
|---|---|
| Единая проверка | `sh scripts/check.sh` → `299 passed`, `CHECK: PASS` |
| Независимый проверяющий: ожидание → факт → доказательство, вердикт «принято», 3 minor | `course/homework-05/06-verify.md`, лог `course/homework-05/06-verify-session.md` |

## 5. Демо

`course/homework-05/demo.md`: сценарий на 2-3 минуты (ментор комментирует строку, ученик видит,
N+1 → 400 с сохранённым вводом, чужая сдача → 404).

## 6. Рефлексия (1)

`course/homework-05/reflection.md`: что согласовали, что дала изоляция и чего не дала (одна
модель), ошибки процесса, выводы.

## Известные ограничения (minor проверяющего, не исправлялись)

- m1: индекс `ix_line_comments_order` не описан в LC-01.
- m2: при 400 страница сдачи загружается дважды.
- m3: `selectattr` по всем комментариям на каждую строку кода, O(строки × комментарии).
