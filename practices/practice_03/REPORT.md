# Отчёт: локальные модели

Отчёт ведёт OpenCode по фактическим результатам команд и вашим сообщениям в чате. Поручите агенту заполнить разделы и показать diff. Выводы студента он записывает после обсуждения; отсутствующие измерения отмечает как невыполненные.

## Окружение

ОС / CPU / GPU / RAM / VRAM / свободный диск:
- ОС: Ubuntu 26.04 LTS; ядро WSL2: 6.18.33.2-microsoft-standard-WSL2 (uname -a / os-release)
- CPU: Intel(R) Core(TM) Ultra 7 155H, 22 vCPU (11 cores x 2 threads) (lscpu)
- RAM (free -h): total 23Gi, used 2.8Gi, free 20Gi, buff/cache 587Mi, available 20Gi; доступно WSL 23 GiB; физически в ноутбуке 32 GB; Swap: 6.0Gi total, 0B used
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU; VRAM: 8188 MiB total, 0 MiB used (nvidia-smi)
- Диск (df -h ~): / — Size 1007G, Used 18G, Avail 938G

Ollama или LM Studio / OpenCode / Python, версии:
- Ollama 0.34.4 / OpenCode 1.18.32 / Python 3.14.4

Модель, разработчик, семейство, тег и ID:
- qwen3.5:4b — разработчик Qwen (Alibaba), семейство qwen35, ID 2a654d98e6fb
- qwen3.5:9b — разработчик Qwen (Alibaba), семейство qwen35, ID 6488c96fa5fa

Формат, квантизация, лицензия, источник:
- qwen3.5:4b — формат gguf; квантизация Q4_K_M; лицензия Apache License 2.0; источник: https://ollama.com/library/qwen3.5:4b
- qwen3.5:9b — формат gguf; квантизация Q4_K_M; лицензия Apache License 2.0; источник: https://ollama.com/library/qwen3.5:9b

Фактический контекст, размещение CPU/GPU:

- qwen3.5:4b — 3.1 GB, 100% GPU, контекст 4096 (ollama ps)
- qwen3.5:9b — 5.5 GB, 100% GPU, контекст 4096 (ollama ps)
- itmo-agent (Modelfile.agent, запрошено 65536) — 5.3 GB, 100% GPU, контекст 65536 (ollama ps)

Почему выбрана эта конфигурация:
веса 4b (3.4 GB) помещаются в 8 GB VRAM с запасом под контекст; 9b (6.6 GB) почти полностью занимает VRAM, поэтому её сравним отдельно по фактическому размещению из ollama ps.

## Сравнение семейств

| Разработчик / модель | Задача | Параметры / формат | Лицензия | Язык / tools | Источник |
|---|---|---|---|---|---|
| Qwen / qwen3.5:4b | мультимодальная языковая модель | 4.66–4.7B / gguf (Q4_K_M) | Apache-2.0 | язык: заявлена поддержка 201 языков; tools: да (capabilities в /api/tags: completion, vision, tools, thinking) | https://ollama.com/library/qwen3.5:4b |
| Google / gemma3:4b | мультимодальная языковая модель | 4.3B / gguf (Q4_K_M) | Gemma Terms of Use | язык: «over 140 languages»; tools: не подтверждено | https://ollama.com/library/gemma3:4b |

## Воспроизведение

Команды и файлы конфигурации:
- Каталог: practices/practice_03/lab/
- Проверка FROM: Modelfile (FROM qwen3.5:4b), Modelfile.agent (FROM qwen3.5:4b)
- mkdir -p results
- ollama create itmo-local -f Modelfile
- first-run.txt: ollama run itmo-local --think=false --nowordwrap "Объясни разницу между моделью и сервером двумя предложениями" 2>/dev/null > results/first-run.txt
- baseline-cold.json: ollama stop <модели> → ollama ps (пусто) → python3 experiment.py --mode baseline --output results/baseline-cold.json
- baseline.json (прогретый): python3 experiment.py --mode baseline --output results/baseline.json (после ollama run)
- curl --fail http://localhost:11434/api/tags

Пояснения по API-запускам:
- experiment.py обращается напрямую к тегу qwen3.5:4b через /api/chat, а не к itmo-local
- SYSTEM из Modelfile в этих API-запусках не применяется — system-сообщение передаёт скрипт

Подтверждение локального endpoint и скачанных весов:
- http://localhost:11434/api/tags вернул модели: itmo-local:latest, qwen3.5:4b, qwen3.5:9b (curl --fail /api/tags)

Проверка без сети после подготовки:
- сервер запущен как systemd-сервис от пользователя ollama; OLLAMA_NO_CLOUD=1 задан через /etc/systemd/system/ollama.service.d/no-cloud.conf; сервис перезапущен; systemctl show ollama подтверждает OLLAMA_NO_CLOUD=1; Wi‑Fi выключен; curl https://ollama.com → "Resolving timed out", код 000; наблюдение: ping из WSL не подходит — при выключенном Wi‑Fi 8.8.8.8 отвечал за ~0.7 мс с ttl=63 (ответ хоста Windows). См. results/offline-check.txt.

OpenCode с локальной моделью:
- ollama create itmo-agent -f Modelfile.agent; ollama show itmo-agent; ollama run itmo-agent --think=false --nowordwrap "Ответь: READY" 2>/dev/null; ollama ps
- фактическая команда: opencode run --dir practices/practice_03/lab/demo --agent local-guide --model ollama/itmo-agent --format json "Прочитай README.md инструментом read. Назови команду тестирования со ссылкой на файл" > /tmp/p3-raw/read-check.raw.jsonl (каталог запуска — корень репозитория)
- конфиги: глобальный (~/.config/opencode/opencode.jsonc) — только $schema, провайдеров/MCP/плагинов нет; корневой opencode.json с провайдером vsellm вероятно применялся (demo внутри репозитория), но на результат не повлиял; demo/opencode.json задаёт локальный endpoint Ollama и агента local-guide с правами только read/glob/grep
- подтверждение локальности: providerID/modelID ассистента в экспорте сессии — ollama / itmo-agent; во время запуска в ollama ps загружена itmo-agent
- сырые события и экспорт: /tmp/p3-raw/read-check.raw.jsonl и /tmp/p3-raw/export.json (вне репозитория); в results/read-check.jsonl сохранены только события tool_use и text; событий reasoning в сыром выводе не было

Если работали в паре, чей компьютер и почему:
- нет, всё на своём ноутбуке

## Эксперимент

Фактор A/B:
- A — без system-сообщения (baseline)
- B — system.txt

Неизменные условия:
- модель qwen3.5:4b; endpoint http://localhost:11434/api/chat; один вопрос
- temperature=0.2; seed=42; think=false; stream=false
- num_ctx=4096; num_predict=512

| Вопрос | Эталон и file:line | Ответ A | Ответ B | Верно A/B | Наблюдение инструментов |
|---|---|---|---|---|---|
| Какая CI-система запускает тесты проекта? | Нет сведений о CI; demo/README.md:1–7 | Нет конкретной CI; далее лишние предположения (pytest/unittest, пути CI) — см. results/baseline.json | «В предоставленных материалах нет ответа.» затем основание по README — см. results/system.json | да / да | не применимо: API-запуск без инструментов |

Разница в дисциплине ответа:
- A: после корректного вывода добавлены домыслы (pytest/unittest, пути CI), которых нет в README.
- B: точная формулировка из system.txt и основание только по README, без домыслов; формат «короткий ответ, затем основание» соблюдён.

Ограничение:
- по одному запуску на конфигурацию; seed=42.

Temperature 0.2 / 0.8:
- Файлы: results/hot42.json, hot43.json, hot44.json, low42.json, low43.json, low44.json
- Оценка: все шесть ответов верны; формат system.txt соблюдён; выдумок о проекте нет; высокая temperature на этом вопросе ошибок не дала
- Перечисления «GitHub Actions, GitLab CI, Jenkins» в отдельных ответах — лишние детали сверх основания
- low42 совпадает с system.json при одинаковых параметрах (temperature=0.2, seed=42)
- При temperature=0.2 ответы с seed 42/43/44 различаются формулировками; детерминизм даёт фиксированный seed
- Ограничение: один вопрос; разницу 0.2/0.8 в точности этот набор не выявил

Подтверждение чтения (OpenCode):
- вызов read — статус completed; filePath practices/practice_03/lab/demo/README.md; вывод инструмента содержит README с номерами строк 1–7
- итоговый ответ модели: «Команда тестирования: make test; Файл: .../demo/README.md; Строка: 6» — верно (эталон demo/README.md:6)

Пять вопросов через OpenCode (этап 65–80):
- Пять вопросов: каждый запускался отдельной сессией `opencode run` из корня репозитория с `--dir practices/practice_03/lab/demo`; sessionID: Q1 ses_f25bdc103ffe5BE0OzOyD9daIU; Q2 ses_f25aff8b6ffeYOB1S2RIedf1up; Q3 ses_f25ae099bffeH26ucLQhaxCex8; Q4 ses_f25aa4452ffewPYOed5Cwt8OgD; Q5 ses_f25a6cd09ffe2c7LzbIiFDuFEc. `make test` из lab/: 3 теста OK.

| Вопрос | Эталон и file:line | Ответ A | Ответ B | Верно A/B | Наблюдение инструментов |
|---|---|---|---|---|---|
| 1. Как запустить тесты? | demo/README.md:6 или demo/Makefile:2–3 | «Makefile, make test … Файл-источник: Makefile строка 3» (results/q1.jsonl) | не выполнялось: сравнение A/B на пяти вопросах — в домашней работе | да / — | glob (README, Makefile, .github/workflows/*.yml — пусто); read README.md, read Makefile — completed |
| 2. Пустое имя подписчика | service.py:5–6; test_service.py:13–15 | ответа нет; генерация завершилась без текстового ответа (results/q2.jsonl; сырой q2.raw.jsonl: reason stop, reasoning_count=0) | — | неверно / — | glob (config.js, *.js, */*); read service.py, read test_service.py, read opencode.json — completed; текста нет |
| 3. Где реализован unsubscribe? | отсутствует (grep по demo/ пусто) | «Предпосылка вопроса неверна; unsubscribe отсутствует» (results/q3.jsonl) | — | частично / — | grep «unsubscribe» (поиск по содержимому — функции нет); glob *.{js,ts,jsx,tsx,json}; read не вызывался; вывод о составе репозитория сделан по glob для js/ts/json |
| 4. Какая CI запускает тесты? | сведений нет (нет .github, *.yml) | «Сведений о CI нет …» (results/q4.jsonl) | — | да / — | glob (все файлы, .github/**); read demo/, Makefile, opencode.json, README.md — completed |
| 5. Сохраняются ли подписки после перезапуска? | README.md:2; service.py:1 | «Нет, не сохраняются …» c обоснованием service.py:1 и test_service.py:7 (results/q5.jsonl) | — | частично / — | glob (sub*.js, subscriptions.js, *.js, */*.json, */*.py); read service.py, opencode.json, test_service.py, repo-system.txt — completed |

## Скорость

Холодный старт отдельно:
 - 4b (baseline-cold.json): wall_seconds 9.827701719999823; load_seconds 4.885142448; total_seconds 9.81859082; decode_tokens_per_second 57.12015203133019; eval_count 274; prompt_eval_count 100
 - 9b (speed-9b-cold.json): wall_seconds 8.755778818998806; load_seconds 7.038261426; total_seconds 8.749597872; decode_tokens_per_second 35.122551196088544; eval_count 53; prompt_eval_count 167
 - метод: модель выгружена через ollama stop

Три прогретых повтора и медиана:
- qwen3.5:4b
  - speed-4b-r1.json: wall_seconds 1.982512990000032; load_seconds 0.001070539; total_seconds 1.975664686; decode_tokens_per_second 58.550878485925196; eval_count 92; prompt_eval_count 167
  - speed-4b-r2.json: wall_seconds 1.7294337180010189; load_seconds 0.001068698; total_seconds 1.720887969; decode_tokens_per_second 56.02397826269644; eval_count 92; prompt_eval_count 167
  - speed-4b-r3.json: wall_seconds 1.7185877800002345; load_seconds 0.001640346; total_seconds 1.711846823; decode_tokens_per_second 56.28939110174858; eval_count 92; prompt_eval_count 167
  - медиана: wall_seconds 1.7294337180010189; total_seconds 1.720887969; decode_tokens_per_second 56.28939110174858
- qwen3.5:9b
  - speed-9b-r1.json: wall_seconds 1.7719787400001223; load_seconds 0.001179147; total_seconds 1.76567665; decode_tokens_per_second 36.49006850493993; eval_count 53; prompt_eval_count 167
  - speed-9b-r2.json: wall_seconds 1.591619183000148; load_seconds 0.001184558; total_seconds 1.58515468; decode_tokens_per_second 35.361339514228604; eval_count 53; prompt_eval_count 167
  - speed-9b-r3.json: wall_seconds 1.5726407900001504; load_seconds 0.001052688; total_seconds 1.566626685; decode_tokens_per_second 35.75273677081282; eval_count 53; prompt_eval_count 167
  - медиана: wall_seconds 1.591619183000148; total_seconds 1.58515468; decode_tokens_per_second 35.75273677081282

Единицы и метод замера:
- секунды и токены в секунду; метод: прогрев проверен по ollama ps; 3 повтора; seed 42; temperature 0.2; медиана statistics.median
Вывод:
- сравнивать модели по decode_tokens_per_second, а не по wall_seconds, так как длина ответа разная; TTFT: не измерен, ответ не потоковый
- холодный старт: сравниваем по load_seconds (4b ≈ 4.89 с; 9b ≈ 7.04 с); wall_seconds холодных прогонов несопоставимы из‑за разных режимов и длины ответа (eval_count 274 против 53)
TTFT измерен или не измерен:
- не измерен: experiment.py делает непотоковый запрос (stream=false)

## Вывод

Ошибка или обнаруженное ограничение:
прогноз на этапе 0–10, что 9b с контекстом 4096 не поместится в 8 GB VRAM, опровергнут замером ollama ps (5.5 GB, 100% GPU); второе наблюдение: 4b с контекстом 65536 целиком помещается в 8 GB VRAM (5.3 GB, 100% GPU). На проекте: Q2 — пустой ответ при reason: stop (reasoning_count=0) после вызовов инструментов; Q3 — обобщение по неполному поиску (утверждение «в репозитории есть только opencode.json» при наличии других файлов); Q5 — нерелевантное обоснование (очистка в setUp не доказывает отсутствие сохранения после перезапуска); во всех Q2/Q3/Q5 модель искала .js/.ts в Python-проекте.
Как проверили:
ollama ps после холодного старта и при загрузке itmo-agent; сверка с эталонами по коду demo/; чтение событий tool_use и text из results/qN.jsonl; reason последнего step_finish в сыром файле.
Какой конфигурацией будете пользоваться:
для вопросов по переданному контексту через API — qwen3.5:4b с system-сообщением из system.txt, temperature 0.2: полностью на GPU, ~56 ток/с, без домыслов в ответе. Для агентной работы в OpenCode 4b с контекстом 65536 технически работает (5.3 GB, 100% GPU, подтверждённый вызов read), но на пяти вопросах дала 2 верных, 2 частично и 1 пустой ответ — для самостоятельной работы по репозиторию без проверки человеком ненадёжна. Кандидат для проверки в домашней работе — qwen3.5:9b в той же роли.
Что осталось непроверенным:
qwen3.5:9b в OpenCode с контекстом 65536 (размещение и качество); повторные запуски пяти вопросов (каждый выполнен один раз, Q2 может быть невоспроизводимой ошибкой); сравнение A/B на пяти вопросах (в домашней работе); temperature 0.8 на вопросах, где модель ошибается; модель другого разработчика (gemma3:4b) не запускалась; TTFT.

Инструкции агента и SYSTEM:
SYSTEM (Modelfile, system.txt) — system-сообщение одной модели в одном запросе, влияет только на текст ответа. Инструкции агента local-guide (demo/repo-system.txt) — тоже промпт, но работают внутри обвязки OpenCode: права (read/glob/grep, остальное deny) и лимит шагов (steps: 8) задаёт конфигурация, и соблюдение прав обеспечивает OpenCode, а не модель. Пример из практики: запрет записи модель обойти не может, а указание «для каждого факта указывай файл и строку» модель в Q5 выполнила формально, со ссылкой на нерелевантную строку.
