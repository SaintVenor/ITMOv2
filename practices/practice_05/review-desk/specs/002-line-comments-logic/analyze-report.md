# Specification Analysis Report: 002-line-comments-logic

Артефакты: `spec.md`, `plan.md`, `tasks.md` (+ `data-model.md`, `research.md`, `contracts/line-comments.md`, общий контракт `specs/line-comments-contract.md`, конституция). Анализ только читал файлы; правки внесены в `tasks.md` после отчёта (см. «Исправлено»). CRITICAL: 0, HIGH: 0.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation / Статус |
|----|----------|----------|-------------|---------|-------------------------|
| C1 | Underspecification | MEDIUM | tasks.md T007; contract LC-01, data-model.md | LC-01 перечисляет «NOT NULL, ≥ 1» для `line`, а T007 не говорил, выражено ли «≥ 1» ограничением БД. | **Исправлено в tasks.md**: T007 — `CheckConstraint("line >= 1")`, T003 — проверка `IntegrityError` для `line = 0`. |
| I1 | Inconsistency (порядок) | MEDIUM | tasks.md T017 → T018 | После T017 `db` в `render_submission` обязателен, а вызов в `review.py` обновляется только в T018: между задачами существующий тест ревью упал бы с `TypeError`. | **Исправлено в tasks.md**: T018 помечена как выполняемая сразу после T017 без промежуточного запуска. |
| G1 | Coverage | LOW | spec.md Edge Cases («Одновременная отправка»); tasks.md | Для edge case не было задачи. | **Исправлено в tasks.md**: T020 — серия комментариев к одной строке без потерь (параллельность не эмулируется). |
| G2 | Traceability | LOW | tasks.md T036 | Сценарий «новая попытка» (LC-22) ссылался только на FR-015; Edge Case «Новая попытка» связан с FR-001. | **Исправлено в tasks.md**: T036 ссылается на FR-001 и FR-015. |
| A1 | Inconsistency | LOW | plan.md (Performance Goals: «один запрос»), research R6/R7 | `list_line_comments` делает `get_submission_for` (запрос сдачи) и запрос комментариев — два запроса, не один. | Не tasks-only; на поведение не влияет. Оставлено, в итоге. |
| A2 | Ambiguity | LOW | spec.md «Status: Draft» | Спека в статусе Draft, хотя по ней идёт реализация (Clarifications приняты, чеклист отмечен). | Не tasks-only; в итоге. |
| A3 | Underspecification | LOW | spec.md US2 AC4, FR-013 | «Данные не изменяются»: нормализация `\r\n` и `strip` (clean_text) — изменение содержимого, но FR-013 это оговаривает. Противоречия нет. | Без правок. |
| T1 | Technical risk | LOW | tasks.md T013, T026 | Проверка контекста через `response.context` зависит от версии Starlette/TestClient; при недоступности — fallback на spy `render_submission`. | Выяснится на красном запуске; в итоге. |

## Coverage Summary

| Requirement | Has Task? | Task IDs |
|---|---|---|
| FR-001 | да | T003, T007, T020, T036 |
| FR-002 | да | T003, T007 |
| FR-003 | да | T004, T008, T020, T021 |
| FR-004 | да | T012, T016, T023, T027, T029 |
| FR-005 | да | T021, T026, T029 |
| FR-006 | да | T005, T022, T026, T029 |
| FR-007 | да | T003, T020, T033 |
| FR-008 | да | T005, T010, T016, T020 |
| FR-009 | да | T011, T014, T035 |
| FR-010 | да | T011, T020, T033 |
| FR-011 | да | T011, T023, T027 |
| FR-012 | да | T023, T027, T034 |
| FR-013 | да | T010, T020 |
| FR-014 | да | T024, T029 |
| FR-015 | да | T024, T036 |
| FR-016 | да | T011, T012, T024 |
| FR-017 | да | T011, T035 |
| FR-018 | да | T012, T013, T017, T025–T027, T030, T031 |
| FR-019 | да | T023, T029 |

SC-001…SC-006 покрыты тестами T020–T037; SC-005 — T036 и T039.

## Constitution Alignment

Нарушений нет. I: baseline, `scripts/check.sh` и `AGENTS.md` не затрагиваются. II: бизнес-правила в `app/services/line_comments.py` (T029), роут только разбирает форму (T030). III: все тесты в `tests/test_line_comments.py` с `[Л FR-nnn]` и `LC-NN` (T037 проверяет автоматически). IV: реализуются только FR-001…FR-019. V: на этапе tasks неоднозначностей, требующих остановки, нет.

## Unmapped Tasks

Нет: T001, T002, T038, T039 — служебные, ссылаются на LC-26/LC-28 и правила процесса.

## Metrics

- Requirements (FR): 19; Tasks: 39; Coverage: 100 %
- Ambiguity: 2 (A2, A3 — LOW); Duplication: 0; Critical: 0; High: 0

## Next Actions

CRITICAL/HIGH отсутствуют, можно переходить к `/speckit-implement`. Находки A1, A2, T1 касаются spec.md/plan.md/окружения и намеренно не правились.
