# Как прогнать ДЗ 4 (≈ 40 минут)

Всё готово, кроме самой работы агента. Её и нужно показать: агент читает правила,
грузит skill, вызывает MCP, а hook возвращает ему результат проверки.
Доказательства складываем в `evidence/`.

## 0. Подготовка (5 мин)

Работаем в своём форке курса, как в ДЗ 3: отдельная ветка и PR внутри форка.

```bash
cd ~/ITMOv2
git status --short                    # должно быть пусто; иначе сначала закоммитить или убрать
git switch main
git pull --ff-only origin main
git switch -c homework-04

# архив скачан в Загрузки Windows; распаковываем в папку практики
unzip /mnt/c/Users/<имя_в_Windows>/Downloads/portfolio-hw4.zip -d practices/practice_04/
cd practices/practice_04/portfolio
git add . && git commit -m "hw4: portfolio skeleton with agent environment"

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

mkdir -p evidence
sh scripts/check.sh                                   # ожидаем CHECK: PASS
PYTHONPATH=. python3 scripts/mcp_smoke.py 2>/dev/null | tee evidence/mcp-smoke.txt
```

`mcp_smoke.py` проверяет свой MCP без агента: один успешный вызов и два ошибочных.

## 1. Проверка подключений (5 мин)

venv должен быть активирован в том же терминале: через него MCP-сервер и hook находят Python и пакеты.

```bash
export VSELLM_API_KEY=...            # если ещё не задан
opencode --version | tee evidence/opencode-version.txt
opencode mcp list | tee evidence/mcp-list.txt
opencode api skill.list --param "location[directory]=$PWD" | tee evidence/skill-list.txt
```

- В `mcp list` должны быть `context7` и `portfolio` со статусом `connected`. Если context7 просит авторизацию, в OpenCode выполнить `/mcps` и войти.
- В списке skills должен быть `test-driven-development`. Если список пустой, подождать пару секунд и повторить.

## 2. Одна сессия в OpenCode (20 мин)

Запустить `opencode` из папки `practices/practice_04/portfolio` (не из корня форка: оттуда не подхватятся skill, hook и MCP этого проекта), выбрать модель VseLLM, режим Build. Сообщения отправлять по одному.

**Сообщение 1 - правила (`AGENTS.md`)**

```text
Прочитай AGENTS.md и docs/requirements.md. Назови команду проверки,
что нельзя менять без поручения и контракт US-3. Пока ничего не меняй.
```

Проверить: агент назвал `sh scripts/check.sh` и запреты из файла, а не общие слова.

**Сообщение 2 - свой MCP, успех и ошибка**

```text
Через MCP-сервер portfolio вызови get_project для slug "walkey",
затем для slug "react-app". Покажи оба ответа инструмента как есть.
```

Проверить: в ленте видны два вызова `portfolio_get_project`, второй вернул ошибку со списком доступных проектов.

**Сообщение 3 - Context7**

```text
use context7. Найди в документации FastAPI и Pydantic, как в модели запроса
ограничить длину строки и как FastAPI отвечает 422 при ошибке валидации.
Ответь кратко, со ссылкой на найденный фрагмент. Ничего не меняй.
```

Проверить: виден вызов инструментов `context7_*`, а не ответ по памяти.

**Сообщение 4 - фича US-3 через skill, hook срабатывает сам**

```text
Загрузи skill test-driven-development и прочитай его writing-good-tests.md.
Реализуй US-3 из docs/requirements.md по этой процедуре:
1) сначала тесты в tests/test_contact.py, покажи их падение;
2) затем минимальная реализация в app/main.py.
После каждой правки читай вывод hook. В конце покажи git diff
и итоговый вывод sh scripts/check.sh. Не делай commit.
```

Проверить:
- виден вызов skill и чтение `writing-good-tests.md`;
- после записи тестов hook дописал к результату правки `CHECK: FAIL`, после реализации - `CHECK: PASS`;
- в `.opencode/hook-log.jsonl` есть строки с `exit_code` 1 и 0.

Если агент проигнорировал skill или нарушил правило, это не провал, а материал для рефлексии: поправить его следующим сообщением и записать, что пришлось вмешаться.

## 3. Сохранить доказательства (5 мин)

```bash
# ID сессии: в TUI или через `opencode session list` (если команды нет - из `/export` в TUI)
opencode export <sessionID> > evidence/session.json
cp .opencode/hook-log.jsonl evidence/hook-log.jsonl
sh scripts/check.sh | tee evidence/check-final.txt
git diff --stat
```

Лучше сделать ещё скриншоты ленты на четырёх ключевых местах (правила, MCP-ошибка, вызов skill, FAIL → PASS от hook).

Самому проверить diff: покрыты ли граничные длины, проверяется ли, что отклонённое сообщение не сохранилось, не изменены ли старые тесты.

## 4. Отчёт и сдача (10 мин)

1. Заполнить `REPORT.md`: вставить короткие фрагменты из `evidence/`, дописать разбор skill своими словами.
2. Написать `reflection.md` своими наблюдениями из этого прогона.
3. Закоммитить и открыть PR **внутри своего форка**, не в репозиторий курса:

```bash
git add . && git commit -m "hw4: contact form (US-3), evidence, report"
git push -u origin homework-04
```

PR `homework-04 → main` в `SaintVenor/ITMOv2`, в описание - ссылку на `REPORT.md`.
