# ДЗ 4: среда агента, skill и собственный MCP

Проект: сайт-портфолио (FastAPI). OpenCode 1.18.35, модель openai/gpt-5 через VseLLM.
Материалы практики рассчитаны на OpenCode 2.0.20, работа шла на 1.18.35, поэтому hook сделан совместимым с обеими версиями (`server()` для 1.x, `setup()` для 2.x), а skill лежит в `.opencode/skill/` — эту папку ищет 1.x.

Вся работа агента — одна сессия `ses_ee8032679ffeqKVfl7crb4EhsM`, полный экспорт: `evidence/session.json` (`opencode export`). Ниже «сообщение N» — N-й запрос в этой сессии.

## 1. Среда и её применение

| Подключение | Файл | Зачем | Какой шаг улучшило | Доказательство применения |
|---|---|---|---|---|
| Правила | `AGENTS.md` | агент знает источник требований, единую команду проверки и запреты, а не угадывает их | постановка задачи: контракт US-3 и критерии приёмки взяты из `docs/requirements.md`, проверка — только через `check.sh` | Сообщение 1: `read AGENTS.md`, `read docs/requirements.md`. Ответ агента: «Команда проверки: `sh scripts/check.sh`»; «Менять `scripts/check.sh`, `.opencode/`, `opencode.json` и `data/projects.json`» |
| Skill | `.opencode/skill/test-driven-development/` | заставляет сначала написать падающий тест, поэтому фича US-3 сразу закрыта проверками | реализация US-3: тесты появились раньше кода и упали по правильной причине | Сообщение 4: вызов `skill {"name": "test-driven-development"}`, затем `read .../writing-good-tests.md` — прочитан целиком (`End of file - total 198 lines`). Загрузку я попросил явно, правило есть и в `AGENTS.md` |
| MCP Context7 | `opencode.json` → `context7` | документация FastAPI/Pydantic вместо параметрической памяти модели | выбор способа валидации: `StringConstraints(strip_whitespace=True, min_length, max_length)` | Сообщение 3: `context7_resolve-library-id` и `context7_query-docs` для FastAPI и Pydantic. Найдено: «Default JSON validation error response», Source: fastapi.tiangolo.com/tutorial/handling-errors; «Validate and constrain strings with StringConstraints» |
| MCP portfolio | `opencode.json` → `portfolio` | факты о проектах берутся из данных сайта, а не выдумываются | см. раздел 3 | Сообщение 2, см. раздел 3 |
| Hook | `.opencode/plugin/check-after-edit.js` | после каждой правки запускает `scripts/check.sh` и дописывает вывод к результату инструмента: «готово» без зелёных тестов невозможно | цикл RED → GREEN: агент видел FAIL/PASS без отдельной команды | Вывод hook внутри результата `apply_patch` в `evidence/session.json`: `[hook check-after-edit] sh scripts/check.sh -> exit 1` с `E assert 404 == 201`; после реализации: `-> exit 0`, `14 passed`, `CHECK: PASS`. Журнал: `evidence/hook-log.jsonl` |

Runner: `scripts/check.sh` (pytest), до подключения hook проверен вручную. Итог: `evidence/check-final.txt` — «15 passed», «CHECK: PASS».

## 2. Skill `test-driven-development`

Источник: obra/superpowers, MIT, снимок `b9e75dd`. Готовый skill, разбираю устройство.

**Разбор устройства:**

Skill — это `SKILL.md` с YAML-шапкой: агент видит только `name` и `description` («Use when implementing any feature or bugfix, before writing implementation code») и по ним решает, загружать ли полный текст. Основное тело задаёт цикл RED → verify RED → GREEN → verify GREEN → REFACTOR. Обе проверки обязательные: тест должен упасть именно из-за отсутствия фичи, а не из-за опечатки. Большая часть текста — таблицы «отговорок» и red flags вроде «test passes immediately» и «I'll test after»: они заранее закрывают типичные способы, которыми модель срезает углы. Правила о качестве тестов (назвать поломку, которую ловит тест; не тестировать моки) вынесены в отдельный `writing-good-tests.md`. `SKILL.md` ссылается на него и не раздувает основной контекст.

**Запуск и проверенный результат:**
- Изменения: `evidence/feature-diff.txt` — `app/main.py | 37 insertions(+)`, `tests/test_contact.py | 157 insertions(+)`. Файл тестов новый и неотслеживаемый, поэтому его дифф снят через `git diff --no-index /dev/null tests/test_contact.py`.
- RED: после создания тестов hook вернул `exit 1`, причина — `assert 404 == 201` (эндпоинта ещё нет). Это та «правильная» причина падения, которую требует skill.
- GREEN: после реализации — `exit 0`, `14 passed`.
- Хронология hook (`evidence/hook-log.jsonl`): `exit_code 1` → `0` (реализация) → `0`, `0` (правки по ревью) → `0`, `0` (правки `REPORT.md`, к коду не относятся).
- Итог: `evidence/check-final.txt` — «15 passed», «CHECK: PASS».

**Ревью и вмешательство:**
Первая версия тестов проверяла граничные длины только внутри диапазона (1/100, 10/2000). По моему ревью добавлен тест `test_out_of_bounds_lengths_not_stored` (name 101, message 9 и 2001, message из пробелов) и удалён неиспользуемый импорт `Field`. Новые тесты прошли сразу, без стадии FAIL: ограничения уже были в коде. По правилам самого skill «test passes immediately» — это red flag, так что здесь TDD соблюдён лишь формально.

## 3. Собственный MCP `portfolio`

`mcp_server/server.py`, tool `get_project(slug)`: возвращает карточку проекта из `data/projects.json`.
Ошибочный вход обрабатывается явно через `ToolError`, сервер не падает:
- неверный формат slug — ошибка с примером правильного формата;
- несуществующий проект — ошибка со списком доступных slug, чтобы агент мог сразу исправиться.

Вызов агентом (сообщение 2, `evidence/session.json`):

| Вход | Статус | Результат |
|---|---|---|
| `walkey` | completed | `{"slug": "walkey", "name": "Walkey", "summary": "In-memory база данных по мотивам Redis/Valkey.", "tech": ["cpp", "databases", "networking"], "repo": "https://github.com/SaintVenor"}` |
| `react-app` | error | `Error executing tool get_project: project 'react-app' not found. Available: argparser, hamarc, circularbuffer, wayhome, ttaskscheduler, walkey, disassembler, myfloat` |

Проверка без агента: `evidence/mcp-smoke.txt` — один успешный и два ошибочных вызова: «get_project('no-such-project') isError=True», «get_project('Bad Slug!') isError=True … invalid slug 'Bad Slug!': expected lowercase letters, digits and '-'».

## 4. Рефлексия

См. `reflection.md`.

## Файлы доказательств

- `evidence/session.json` — полный экспорт сессии агента: все запросы, вызовы инструментов и их вывод, включая текст hook.
- `evidence/check-final.txt` — итоговый запуск runner: «15 passed», «CHECK: PASS».
- `evidence/feature-diff.txt` — дифф фичи US-3: `app/main.py` и новый `tests/test_contact.py`.
- `evidence/hook-log.jsonl` — журнал hook: 1 запись с `exit_code 1`, 5 с `exit_code 0`. Поле `file` равно `null`: правки шли через `apply_patch`, у которого нет аргумента `filePath`.
- `evidence/mcp-list.txt` — `opencode mcp list`: «context7 connected», «portfolio connected».
- `evidence/mcp-smoke.txt` — смоук-тест MCP portfolio без агента: 1 успех, 2 обработанные ошибки.
- `evidence/opencode-version.txt` — «1.18.35».
- `evidence/skill-list.txt` — `opencode debug skill`: есть `test-driven-development`; рядом 14 глобальных skills из `~/.claude/skills`.
