# REPORT

## 1) Железо и версии
- Ядро (WSL2): Linux 6.18.33.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun 18 21:54:43 UTC 2026 x86_64 GNU/Linux
- NVIDIA: NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB VRAM, драйвер 552.46
- Память (RAM): 23Gi total, 20Gi available (по `free -h`)
- Ollama: 0.34.4
- OpenCode: 1.18.35

## 2) Модели: ID, квантизация, контекст
- itmo-agent (FROM qwen3.5:4b)
  - quantization: Q4_K_M; parameters: ~4.7B
  - context length (профиль): 65536 (ollama show сообщает базовый лимит 262144; профиль задаёт num_ctx=65536)
  - temperature: 0.2; top_k=20; top_p=0.95; presence_penalty=1.5
  - Обоснование: temperature 0.2 для большей детерминированности; num_ctx 65536 для задач агентных вызовов и длинных ответов.
  - Правка `lab/Modelfile.agent`: раньше в нём были только num_ctx и temperature, а top_k/top_p/presence_penalty неявно наследовались от qwen3.5:4b. Теперь все пять параметров заданы явно и прокомментированы. После `ollama create itmo-agent -f lab/Modelfile.agent` ID модели не изменился (`3465bc38f59d`), значит A/B-прогоны шли ровно с этими параметрами (results/08-modelfile-agent.txt).
  - Thinking у модели включён по умолчанию (`ollama show`: thinking default true, results/08-modelfile-agent.txt); в агентных прогонах он был включён.
- itmo-local (FROM qwen3.5:4b)
  - quantization: Q4_K_M; parameters: ~4.7B
  - context length (профиль): 4096
  - temperature: 0.2
  - Обоснование: локальный чат с ограниченным контекстом (экономия памяти/скорости).

## 3) Конфигурация и права агента
- practices/practice_03/lab/demo/opencode.json:
  - Агент local-guide: primary, prompt {file:./repo-system.txt}, steps=8
  - Агент local-guide-alt: primary, prompt {file:../system.txt}, steps=8
  - Права permission во время A/B-прогонов: `{"*":"deny","read":"allow","glob":"allow","grep":"allow","external_directory":"deny"}`. Доказательство: в results/ab-runs-raw/run-local-guide-q2.json модель прочитала `opencode.json` (событие `read`), в выводе у обоих агентов одинаковые permission и steps, различаются только `prompt` и `description` — то есть между вариантами A/B отличается один фактор.
  - Права сейчас (после A/B, см. раздел 5): `read` ограничен шаблоном пути — `{"*":"deny","practices/practice_03/lab/demo":"allow","practices/practice_03/lab/demo/*":"allow"}`, остальное без изменений.

## 4) Таблица A/B и решение
Исходный план и смена фактора (из results/05-ab-decision.txt):

```
Исходный план A/B: сравнение моделей qwen3.5:4b vs qwen3.5:9b при фиксированном контексте.

Проблема: qwen3.5:9b не помещается целиком на GPU.
- 65536: PROCESSOR 36%/64% CPU/GPU
- 32768: PROCESSOR 24%/76% CPU/GPU
- 16384: PROCESSOR 16%/84% CPU/GPU

Решение: менять фактор A/B на system prompt при одной модели (qwen3.5:4b) с контекстом 65536.
- local-guide: prompt {file:./repo-system.txt}
- local-guide-alt: prompt {file:../system.txt}
- обе используют модель itmo-agent (qwen3.5:4b, num_ctx 65536), provider ollama, те же permission и steps.
```

Результаты сравнения (из results/06-comparison.md):

| Вопрос | Эталон (кратко) | Ответ local-guide | Ответ local-guide-alt | Что показали события (файлы/паттерны) | Итог |
|---|---|---|---|---|---|
| 1) Как запустить тесты? | `make test` по `lab/demo/Makefile:2-3` (цель test → `python3 -m unittest -v`); также README.md:6 «Проверка: make test». | Назвал `make test` и `python3 -m unittest -v` со ссылкой на demo/Makefile «строка 2‑4» (в файле 3 строки, цель test — строки 2-3). | Противоречиво: начал с «нет ответа», но назвал `make test` и источник README.md (строка «Проверка: make test», README.md:6). | local-guide: glob `**/Makefile` → прочитал demo/Makefile; glob `**/*.md` → прочитал README.md. local-guide-alt: glob `**/README.md` → прочитал README.md; Makefile не читал. | local-guide: верно (номер строки в ссылке неточен). local-guide-alt: частично. |
| 2) Пустое имя подписчика | `service.py:5-6` бросает `ValueError("empty name")`; `test_service.py:13-15` это подтверждает. | Заявил, что кода валидации нет и подтвердить нельзя. | Финальный текст — не ответ по сути (описал план «выполню вызов»). | local-guide: glob `**/*.{js,ts,json}` (без `.py`) → прочитал только `opencode.json`; `service.py` не читал. local-guide-alt: glob `**/*.{py,js,ts,sh,json}` → найден `service.py` и `test_service.py`; прочитал только `test_service.py`; итоговый text не дал ответа. | local-guide: неверно (не прочитал `.py`, сделал ложный вывод). local-guide-alt: нет ответа. |
| 3) Где реализован `unsubscribe`? | Не реализован; предпосылка ложна. | Файлов с `unsubscribe` нет «во всех файлах репозитория» — преувеличение: `grep` шёл только по `lab/demo`. Ложную предпосылку прямо не назвал («Вопрос может быть предположимым»). | Правильно: функция отсутствует, предпосылка вопроса ошибочна. | Оба: `grep` по шаблону `unsubscribe` в `lab/demo` → совпадений нет. | local-guide: частично. local-guide-alt: верно. |
| 4) Какая CI-система запускает тесты? | В репозитории нет конфигов CI. | Правильно: «Сведений о CI не найдено». | Правильно: «В предоставленных материалах нет ответа» (указал отсутствие CI-файлов). | local-guide: glob на `*.yml`, `.github/**`, `.gitlab-ci.yml`; попытка read несуществующего `Gitlabfile.yml` → ошибка; вывод: нет CI. local-guide-alt: glob `.github/**/*`, `.gitlab-ci.yml`, `.travis.yml`, `.circleci/config.yml`; `grep` по `ci|circleci|travis|jenkins|azure|github|gitlab` → нет совпадений. | local-guide: верно. local-guide-alt: верно. |
| 5) Сохраняются ли подписки после перезапуска? | Нет, данные в памяти процесса: `service.py:1` (`subscribers = set()`), README.md:2; `setUp()` очищает. | Правильно: «Нет, не сохраняются» с ссылками на `service.py`, `README.md`, `test_service.py`. | Финальный текст отсутствует (пусто), несмотря на чтение `service.py`. | local-guide: сначала читал `opencode.json`, затем glob `*.*` → увидел `service.py`, `test_service.py`, `README.md`; прочитал все и дал ответ. local-guide-alt: glob `**/*.{py,json,csv,txt}` → нашёл `service.py`; прочитал `opencode.json` и `service.py`; финального text-ответа нет. | local-guide: верно. local-guide-alt: нет ответа. |

Примечание: по вопросу 2 local-guide использовал `**/*.{js,ts,json}` (без `.py`) и не прочитал `service.py`, что привело к неверному выводу. У local-guide-alt по вопросу 2 финальный текст — только план действий, по вопросу 5 части `text` нет (ответ остался в `reasoning`, см. раздел 5).

**Сводка оценок:** local-guide — 3 верно (q1, q4, q5), 1 частично (q3), 1 неверно (q2); local-guide-alt — 2 верно (q3, q4), 1 частично (q1), 2 нет ответа (q2, q5).

**Ограничение выборки:** каждый вопрос задан каждому агенту один раз (n=1, temperature 0.2, seed не задан). Сводка выше — наблюдение по одному прогону, сама по себе она не доказывает, что один системный промпт лучше: различие может быть шумом. Повторных прогонов не делалось.

**Решение: оставляем `repo-system.txt` (агент local-guide).** Основание не столько в счёте, сколько в устройстве промптов. `lab/system.txt:1-3` написан для чата, где контекст передаётся в запросе: «Используй только переданный контекст. … Если данных нет, напиши „В предоставленных материалах нет ответа“». В агентном режиме контекст никто не передаёт — модель должна сама найти файлы инструментами, — и local-guide-alt копировал эту фразу в ответы q1, q3 и q4 (в q1 — даже при том, что назвал `make test` из README). `lab/demo/repo-system.txt:1-3`, наоборот, велит сначала читать файлы и ссылаться на файл и строку. Поэтому фактор «промпт» в этом A/B на деле сравнивает агентный промпт с чатовым, а не два равноценных агентных варианта; результат ожидаем и не переносится на сравнение двух агентных промптов.

**Подтверждение локальности прогонов** (results/10-locality.txt, исходники в results/ab-runs-raw/): во всех 10 сессиях каждое assistant-сообщение имеет `providerID=ollama`, `modelID=itmo-agent`, агент в export совпадает с вариантом; sessionID в событиях и в export совпадают. После каждого прогона `ollama ps`: `itmo-agent 3465bc38f59d 5.3 GB 100% GPU 65536`. Файлы results/ab-runs/*.json — отфильтрованная выборка (только события tool_use и text); полные события, export и вывод `ollama ps` лежат в results/ab-runs-raw/.

**Упавшая первая партия:** первый запуск всех 10 прогонов завершился с returncode 1 за 1.22–1.47 с каждый (results/ab-runs-raw/ab-run-summary.json, сессии `ses_ee8e33…`–`ses_ee8e2e…`). Зачётной считается вторая партия, где все 10 прогонов завершились с rc=0 (results/ab-runs-raw/ab-run-driver.txt). Причина падения первой партии в сохранённых файлах не записана.

## 5) Разбор ошибок
- Уровень «свойство модели»:
  - Вопрос 2: local-guide выбрал glob-паттерн без `.py` (`**/*.{js,ts,json}`), не нашёл `service.py` и выдал неверный ответ.
  - Вопрос 2: local-guide-alt прочитал только `test_service.py` и закончил текстом-планом «выполню вызов функции» вместо ответа.
- Уровень «свойство обвязки / режима thinking»:
  - Вопрос 5, local-guide-alt: ответ сгенерирован (177 output-токенов на последнем шаге) и верен по сути, но целиком попал в часть `reasoning`; части `text` у последнего сообщения нет (results/11-thinking-vs-text.txt). У остальных 9 прогонов есть и `reasoning`, и `text`. Поэтому это не «модель не смогла ответить», а то, что qwen3.5 с thinking по умолчанию в связке с opencode может оставить ответ в канале thinking. По одному случаю нельзя сказать, как часто это происходит.
  - `external_directory: deny` в opencode не ограничивает доступ внутри Git-репозитория: чтение `../QUESTIONS.md` (вне lab/demo, но внутри репозитория) было разрешено (results/03-local-guide-boundaries.txt). Проба чтения пути вне репозитория в коммите не сохранена. Поэтому эталоны подготовлены по коду `lab/demo` до первого прогона и хранились вне репозитория, у рабочего агента; в репозиторий они не входят. Что тестируемая модель в A/B не выходила за пределы `lab/demo`, видно по событиям: во всех 10 прогонах ни один из 36 вызовов `tool_use` не обращался к путям вне `lab/demo` (results/ab-runs/, results/ab-runs-raw/; команда проверки и результат — results/10-locality.txt).
  - Колонка «Эталон (кратко)» в этом отчёте и в results/06-comparison.md всё же лежит в репозитории, поэтому после A/B `read` ограничен шаблоном пути на `lab/demo`. Пробные запуски (results/09-isolation/SUMMARY.txt, results/12-demo-run.txt, шаг 5) делались, пока полный файл эталонов временно лежал в results/ (потом удалён):
    - `read` файлов `REPORT.md` и файла эталонов в results/ у обоих агентов — отказ правилом (`prevents you from using this specific tool call`); `read` файлов и самого каталога `lab/demo` — работает.
    - **Не закрыто:** `grep` и `glob` с путём вне `lab/demo` работают. В пробах `grep` по `results/` с шаблоном `Вывод` вернул все 5 строк «Вывод: …» из файла эталонов (results/09-isolation/lg-grep-reference.json; текст строк в сохранённом файле заменён после прогона, см. 09-isolation/SUMMARY.txt), `glob` нашёл его имя. Сейчас файла эталонов в репозитории нет, но `grep` по-прежнему видит REPORT.md и results/06-comparison.md: проба lg-grep-repo вернула из них строку заголовка таблицы, а строки этой таблицы содержат и колонку «Эталон (кратко)», так что `grep` по подходящему шаблону вернёт и её. В opencode 1.18.35 правило `read` сравнивается с путём относительно корня git, а правила `glob`/`grep` — с поисковым шаблоном, а не с путём (results/09-isolation/opencode-permission-source.txt), поэтому шаблоном пути их не ограничить. Варианты: запретить `grep`/`glob` (изменит набор инструментов по сравнению с A/B) или не держать эталоны в репозитории даже в кратком виде.
    - В пробах модель дважды не вызвала `read` и выдумала первую строку REPORT.md («# Lab 3» и «## Practice_03» вместо «# REPORT»), а в демо трижды исказила путь (`ITMOv2/practice_03/...`) и получила отказ.

## 6) Скорость и память
- Замер скорости (results/07-speed.md):

```
# Замер скорости itmo-agent (qwen3.5:4b, ctx 65536)

Промпт: "Напиши одно короткое предложение про тестирование."
Опции: num_ctx=65536, seed=42, think=false.

## 1) Холодный старт
- load_duration: 5.1276964 с (5127696400 нс)
- total_duration: 5.696566335 с (5696566335 нс)

## 2) Подтверждение прогрева
- Модель загружена: `ollama ps` показывает itmo-agent 100% GPU, CONTEXT 65536 (07-speed.txt).
- Первый прогретый запрос (warm0) total_duration: 0.865342262 с. Он считается прогревом и в повторы не входит.

## 3) Повторы (прогретые), пересчёт по исходным JSON — 07-speed-recalc.txt, часть A
- warm1: eval_count=26, eval_duration=0.445038 с → 58.42 tok/s
- warm2: eval_count=26, eval_duration=0.457401 с → 56.84 tok/s
- warm3: запрос упал — `option "seed" must be of type integer`; повторён как warm3_fix
- warm3_fix: eval_count=26, eval_duration=0.468571 с → 55.49 tok/s

Медиана tokens/sec по 3 повторам (warm1, warm2, warm3_fix): 56.84.

## 4) Режим агента (thinking включён) — 07-speed-recalc.txt, часть B
- eval_count=3985 в каждом из 4 запросов; total_duration повторов 72.9–73.8 с
- tokens/sec повторов run1–run3: 54.63, 54.75, 54.09; медиана 54.63
```

- Исправление: в прошлой версии отчёта повторами ошибочно считались warm0–warm2, а tok/s были округлены неверно (56.96 / 58.44 / 56.85, медиана 56.96). Исходные JSON — results/speed-raw/, пересчёт — results/speed-raw/recalc.py.
- Замер с think=false не описывает режим агентных прогонов: с включённым thinking скорость декодирования почти та же (~55 tok/s), но на одно короткое предложение модель тратит ~4 тыс. токенов и ~73 с.

- Память/устройства: qwen3.5:9b не помещается целиком на GPU даже при контексте 16384. Данные:
  - 65536: 36%/64% CPU/GPU (results/05-ollama-ps-9b.txt)
  - 32768: 24%/76% CPU/GPU; 16384: 16%/84% CPU/GPU (results/05b-context-search.txt)

## 7) Офлайн-проверка
Выполнена: `lab/offline-check.sh` запущен из корня репозитория 2026-10-07 в 22:17 при отключённой сети (Wi-Fi выключен), полный вывод — results/offline-check.txt. Ключевые строки:

```
[2026-10-07T22:17:22+03:00] Running: curl -sS --max-time 5 https://ollama.com
[2026-10-07T22:17:27+03:00] Exit code: 28
curl: (28) Resolving timed out after 5001 milliseconds
[2026-10-07T22:17:27+03:00] Result: FAIL as expected — no cloud access (confirms offline mode).
...
[2026-10-07T22:17:27+03:00] Running: curl -sS -H 'Content-Type: application/json' -d @- http://localhost:11434/api/generate
[2026-10-07T22:17:28+03:00] Exit code: 0
{"model":"itmo-agent",...,"done":true,"done_reason":"stop",...,"total_duration":805103160,"load_duration":1001877,...,"eval_count":26,"eval_duration":440920000}
[2026-10-07T22:17:28+03:00] Result: SUCCESS — local model responded.
```

- Облако недоступно: запрос к https://ollama.com не прошёл даже разрешение имени (`curl: (28) Resolving timed out`, exit 28, таймаут 5 с). Офлайн подтверждён отказом DNS после выключения Wi-Fi.
- Локальная модель ответила: itmo-agent через localhost:11434 вернул `done: true`, 26 токенов за 0.81 с. Собранный из потока ответ: «Тестирование — это процесс обнаружения дефектов в программном продукте до того, как он будет представлен пользователям.»
- Оговорка: `load_duration` ≈ 1 мс, то есть модель уже была загружена в память. Проверена генерация без сети; загрузка модели с диска без сети этим запуском не проверялась.
- Дополнительно: в сервисе ollama задан OLLAMA_NO_CLOUD=1 (`systemctl show ollama --property=Environment`).

## 8) Ограничения
- Изоляция тестируемой модели неполная: `grep`/`glob` могут читать репозиторий за пределами `lab/demo` (раздел 5).

## 9) Что не проверялось
- Повторяемость ответов: каждый вопрос задан каждому агенту один раз (n=1).
- TTFT (time to first token) — потоковые метрики не замерялись.
- Устойчивость к увеличению числа вопросов.
- Поведение при конкурентных запросах.

## 10) Как воспроизвести
- Тесты: `make test` из каталога `practices/practice_03`.
- Сборка моделей: `ollama create itmo-local -f practices/practice_03/lab/Modelfile` и `ollama create itmo-agent -f practices/practice_03/lab/Modelfile.agent`.
- Запуски агента: из `practices/practice_03/lab/demo` — `opencode run --agent local-guide --format json` (и `local-guide-alt`).
