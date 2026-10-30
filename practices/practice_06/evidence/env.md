# Окружение домашнего задания 6

Дата проверки: 2026-10-30. Ветка `homework-06`.

## Версии

| Компонент | Версия |
|---|---|
| ОС | Linux 6.18.33.2-microsoft-standard-WSL2 (WSL2) |
| Python | 3.14.4 (требование лабы — 3.10+, только стандартная библиотека) |
| OpenCode | 1.19.2 (`opencode --version`) |

## Статус тестов (исходный, уязвимый сервис)

| Команда | Каталог | Результат |
|---|---|---|
| `make test` | `practices/practice_06` | OK, 16 тестов |
| `make step6` | корень | OK, 16 тестов |
| `make test` | корень | OK, exit 0: step1 (`Practice 1 artifacts: OK`), step2 (`Practice 2 artifacts: OK`), step3 (3 теста), step6 (16 тестов) |

Корневой `make test` на step1–step3 не падает, разбирать нечего.

## Конфигурация OpenCode

`practices/practice_06/opencode.json` содержит висячую запятую в блоке `read`
агента `threat-judge`. OpenCode читает конфиг как JSONC и запятую принимает:
`opencode debug config` из `practices/practice_06` показывает оба агента
(`threat-judge`, `shop-planner`) с промптами из файлов и исходными правами.
Файл не менялся.

Замечание: глобальный конфиг пользователя добавляет агенту `build` запрет
git-команд (`git commit*`, `git push*` и т. д.); на `threat-judge` и
`shop-planner` это не влияет — у них `"*": "deny"`.

## Выбранная модель

`opencode models` показывает у провайдера VseLLM только две модели:

- `vsellm/openai/gpt-5`
- `vsellm/anthropic/claude-sonnet-4`

Выбрана **`vsellm/openai/gpt-5`**: по публичным ценам она дешевле
(≈ $1.25 / $10 за 1M входных/выходных токенов против $3 / $15 у Sonnet 4) и при этом
не слабая. Эта модель используется во всех запусках домашки (`shop-planner` и `threat-judge`).
Фактический `cost` в событиях OpenCode равен 0 — провайдер не передаёт стоимость.

## Рабочие команды

Все флаги из условия есть в версии 1.19.2 (`--dir`, `--agent`, `--model`/`-m`,
`--format json`, `--file`/`-f`), но у `--file` важен порядок аргументов — см. ниже.

Пробный запуск (из корня форка), выполнен успешно, exit 0, ~13 с:

```bash
opencode run --dir practices/practice_06 --agent shop-planner \
  --model vsellm/openai/gpt-5 --format json "Верни tool=refuse"
```

Ответ модели (сырые события — `evidence/env-probe.jsonl`):

```json
{"tool":"refuse","arguments":{"reason":"Недостаточно данных для выдачи чека. ..."}}
```

`--format json` выдаёт поток JSONL-событий: `step_start`, `text` (ответ модели в
`part.text`), `step_finish` (токены, включая `reasoning`).

### Особенность `--file` в 1.19.2

`--file` объявлен как массив (`[array]`) и забирает все следующие позиционные
аргументы. Команда из условия в виде
`... --file THREAT_MODEL.md --file lab/service.py "Оцени модель угроз"`
падает с `Error: File not found: Оцени модель угроз` (проверено на `shop-planner`
с тем же порядком аргументов). Рабочий эквивалент — **сообщение ставится до `--file`**.

Пути в `--file` разрешаются относительно `--dir`: при запуске из корня форка
`--file planner-system.txt` нашёл файл `practices/practice_06/planner-system.txt`
(в корне такого файла нет), модель процитировала его первые слова.

Рабочая команда судьи (из корня форка):

```bash
opencode run --dir practices/practice_06 --agent threat-judge \
  --model vsellm/openai/gpt-5 --format json \
  "Оцени модель угроз" --file THREAT_MODEL.md --file lab/service.py
```

Рабочая команда планировщика с контекстом (для следующих сессий):

```bash
opencode run --dir practices/practice_06 --agent shop-planner \
  --model vsellm/openai/gpt-5 --format json \
  "<обычная задача клиента>" --file evidence/before/<контекст>.txt
```

### Зависание `opencode run` и обход

Дважды (первая попытка run-1 и первая попытка run-2 судьи) `opencode run` зависал
сразу после `message=init` в журнале: сессия не создавалась, запрос к модели не
уходил, вывод оставался пустым. Процессы останавливались вручную. Повторный запуск
с `< /dev/null` (stdin закрыт) и `timeout` отработал за 1–2 минуты. Точная причина
не установлена; рабочая гипотеза — `opencode run` ждёт данные из stdin, если он не
терминал. Поэтому все неинтерактивные запуски выполняются так:

```bash
timeout 600 opencode run --print-logs --log-level INFO --dir practices/practice_06 \
  --agent threat-judge --model vsellm/openai/gpt-5 --format json \
  "Оцени модель угроз" --file THREAT_MODEL.md --file lab/service.py \
  < /dev/null > run.raw.jsonl 2> run.stderr.txt
```

`--print-logs` пишет журнал OpenCode в stderr (видно, создана ли сессия и сколько файлов приложено).
Пути в `*.stderr.txt` обезличены: домашний каталог пользователя заменён на `~`, остальное содержимое журналов не менялось.

`jq` в системе не установлен; ответ извлекается коротким Python-скриптом
(`type == "text"` → `part.text`).

Сервис лабы: `python3 service.py --port 8066` из `practices/practice_06/lab`,
привязка только к `127.0.0.1`.
