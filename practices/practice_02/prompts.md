# Журнал экспериментов Практики 2

- Выбранный слабый артефакт Практики 1:
- practices/practice_01/tests_load.md — таблица «Нагрузочные проверки»
- Что в нём нужно улучшить:
- Сделать цели нагрузки измеримыми и проверяемыми по доступным источникам (CASE.md, TRAINING_PR.diff), добавить воспроизводимость.
- Как поймём, что изменение полезно:
- Строка сценария содержит: ссылку на код эндпоинта, измеримые цели (p99, 100% 200), источник evidence в рамках OBS-1, команду запуска. Ревьюер может повторить проверку.

| Техника | Файл эксперимента | Изменённый файл Практики 1 | Конкретное изменение | Проверка | Что отклонили |
|---|---|---|---|---|---|
| Few-shot | [`few_shot/experiment.md`](few_shot/experiment.md) | Раздел «Нагрузочные проверки» в `../practice_01/tests_load.md` → исправленная версия: [`few_shot/tests_load.md`](few_shot/tests_load.md) | Уточнили эндпоинт и метод; заменили среднее на p99; цели: 100% 200; evidence привязан к OBS-1; добавили команду запуска | Проверка через CASE.md (OBS-1), TRAINING_PR.diff (`@app.post("/api/reviews")`), и наличие команды запуска в few_shot/tests_load.md | Отклонены Grafana/APM и допущения о трафике без пометки |
| R.C.T.F. | [`rctf/experiment.md`](rctf/experiment.md) | Раздел «Нагрузочные проверки» в `../practice_01/tests_load.md` → исправленная версия: [`rctf/tests_load.md`](rctf/tests_load.md) | Добавили обязательные сценарии под API-1 (413 для >20 000 символов) и REL-1 (таймаут 10 с); уточнили POST /api/reviews; заменили среднее на p99; evidence согласовали с OBS-1; числа без источника пометили «допущение» | Проверка ссылками: TRAINING_PR.diff:35-38 (эндпоинт), app/review_service.py:19-22 (LLM вызов); CASE.md: API-1, REL-1, OBS-1, OUT-1, QA-1 | Отклонены не подтверждённые источниками метрики (трейсинг содержимого), любые числа без пометки «допущение» |
| Chain of Verification | [`chain_of_verification/experiment.md`](chain_of_verification/experiment.md) |  |  |  |  |
| Tree of Thoughts | [`tree_of_thoughts/experiment.md`](tree_of_thoughts/experiment.md) |  |  |  |  |
| RAG | [`rag/experiment.md`](rag/experiment.md) |  |  |  |  |
| ReAct | [`react/experiment.md`](react/experiment.md) |  |  |  |  |

## Независимое ревью

| Замечание другой команды | Где исправили | Evidence |
|---|---|---|
| Двусмысленность |  |  |
| Непроверяемое требование |  |  |
| Пропущенный риск или источник |  |  |
