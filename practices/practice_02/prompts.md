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
| R.C.T.F. | [`rctf/experiment.md`](rctf/experiment.md) |  |  |  |  |
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
