# DEMO: Быстрый показ

Все команды — из каталога `practices/practice_03/lab/demo`. Прогон этого сценария: `results/12-demo-run.txt`.

1) Проверить, что Ollama жив и видит модели

```bash
ollama list
```
Ожидаемый вывод (порядок строк и MODIFIED могут отличаться; SIZE здесь — размер весов на диске):
```
NAME                   ID              SIZE      MODIFIED
itmo-agent9b:latest    <id>            6.6 GB    ...
itmo-agent:latest      3465bc38f59d    3.4 GB    ...
itmo-local:latest      <id>            3.4 GB    ...
qwen3.5:9b             <id>            6.6 GB    ...
qwen3.5:4b             <id>            3.4 GB    ...
```

2) Убедиться, что модель грузится на GPU (прогрев + ps)

```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"itmo-agent","prompt":"ping","options":{"num_ctx":65536},"keep_alive":"5m"}' >/dev/null \
&& ollama ps
```
Ожидаемый вывод (SIZE здесь — занятая память вместе с KV-кэшем на 65536 токенов, поэтому больше, чем в `ollama list`).
С холодного старта шаг занимает ~30 с (31.1 с в `results/12-demo-run.txt`): загрузка модели плюс ответ на «ping» в режиме thinking, который у itmo-agent включён по умолчанию.
```
NAME                 ID              SIZE      PROCESSOR    CONTEXT    UNTIL
itmo-agent:latest    3465bc38f59d    5.3 GB    100% GPU     65536      ...
```

3) Запуск агента

```bash
opencode run --agent local-guide --format json --message "Как запустить тесты?" > /tmp/demo-q1.json
```
Ожидаемый вывод в `/tmp/demo-q1.json` (поток JSON-событий, по строке на событие). Набор и порядок вызовов
от прогона к прогону разный (модель недетерминирована), поэтому проверяется не точная последовательность, а:
- есть события `"type":"tool_use"` с `"tool":"glob"`, `"read"` или `"grep"`;
- все успешные `read` — файлы внутри `lab/demo` (README.md, Makefile, service.py, test_service.py);
- есть вызов `read` хотя бы одного файла из `lab/demo`;
- последнее событие `"type":"text"` упоминает `make test` и/или `python3 -m unittest -v`. Ссылка на файл в ответе возможна, но не гарантирована: в повторном прогоне модель ответила «Тесты запускаются командой `make test`.» без ссылки.

Быстрый просмотр:
```bash
grep -o '"tool":"[a-z]*"\|"filePath":"[^"]*"\|"text":"[^"]\{0,120\}' /tmp/demo-q1.json
```

4) Экспорт сессии для подтверждения локальности модели

```bash
SID=$(grep -o 'ses_[A-Za-z0-9]*' /tmp/demo-q1.json | head -1)
opencode export "$SID" 2>/dev/null | grep -A4 '"model"' | head -5
```
`opencode export` пишет строку `Exporting session: ses_...` в stderr. Если сохранять вывод в файл вместе с stderr (`2>&1`), эту первую строку нужно отрезать (`tail -n +2`), иначе файл не разбирается как JSON. Ожидаемый фрагмент:
```
    "model": {
      "id": "itmo-agent",
      "providerID": "ollama",
      "variant": "default"
    },
```

5) Проверка изоляции: файлы вне `lab/demo` не читаются

```bash
opencode run --agent local-guide --format json \
  --message "Прочитай файл инструментом read. filePath: $(realpath ../../REPORT.md) . Сначала обязательно вызови read, потом процитируй первую строку дословно." \
  | grep -o '"tool":"read","callID":"[^"]*","state":{"status":"[a-z]*"\|prevents you from using this specific tool call'
```
Ожидаемый вывод: событие `read` со статусом `error` и текстом `prevents you from using this specific tool call`.
Модель иногда отвечает без вызова инструмента (и выдумывает содержимое) — тогда повторить.
Ограничение: `glob`/`grep` по пути вне `lab/demo` не блокируются (см. REPORT.md, раздел 5).
