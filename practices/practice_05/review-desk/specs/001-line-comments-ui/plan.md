# Implementation Plan: Построчные комментарии ментора к коду сдачи: интерфейс

**Branch**: `001-line-comments-ui` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-line-comments-ui/spec.md`

## Summary

Страница сдачи `GET /submissions/{id}` показывает код с явными номерами строк и комментарии ментора под своими строками.
Ментор вводит номер строки и текст в одну форму под кодом (без JS), отправка идёт
`POST /submissions/{id}/line-comments` с редиректом `303` на `#L{n}` страницы сдачи (LC-09, LC-10). Ученик-автор
только читает. Вся серверная логика (хранение, права, проверка номера строки и текста, маршрут, `render_submission`)
- у команды логики; UI-команда делает шаблоны и стили и опирается на общий контракт
[`specs/line-comments-contract.md`](../line-comments-contract.md) и [contracts/service-expectations.md](contracts/service-expectations.md).
Решения - в [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (как в проекте)

**Primary Dependencies**: FastAPI, Jinja2, SQLAlchemy 2.0 (из `requirements.txt`; новых зависимостей нет)

**Storage**: N/A для UI. Новая таблица `line_comments` принадлежит команде логики ([data-model.md](data-model.md) описывает только вид данных для UI)

**Testing**: pytest + `TestClient`; тесты фичи в `tests/test_line_comments_ui.py`, docstring ссылается на `LC-NN` и на `[UI FR-nnn]` (LC-29)

**Target Platform**: Linux server, браузеры без JavaScript

**Project Type**: web-service (серверный рендер Jinja2)

**Performance Goals**: N/A; комментарии сдачи грузятся одним запросом, обход строк кода - один проход в шаблоне

**Constraints**: без JS и сборки фронтенда; `|safe` запрещён; baseline, `review-queue`, `path-id-bounds` не меняются; слои не меняются

**Scale/Scope**: один экран (страница сдачи), один новый POST-маршрут (пишет логика); код до 100 000 символов (`CODE_MAX`), комментарии - до 2 000 (LC-06)

## Constitution Check

*GATE: пройден до Phase 0, перепроверен после Phase 1.*

| Принцип | Оценка |
|---|---|
| I. Приоритет `AGENTS.md` и `docs/baseline.md` | Пройден: baseline не меняется, `docs/baseline.md` и `scripts/check.sh` не трогаем |
| II. Слои | Пройден: UI пишет только шаблоны и CSS; правила и роуты - у логики. Строки кода и `line_count` шаблон получает из контекста (`code_lines`, LC-04, LC-11), сам не делит |
| III. Трассировка тестов | Пройден: `tests/test_line_comments_ui.py`, docstring с `LC-NN` и `[UI FR-nnn]` (LC-29) |
| IV. Объём по спеке | Пройден: редактирование, удаление, черновики и уведомления не планируются |
| V. Неоднозначности на plan | Зафиксированы как допущения (см. ниже и [research.md](research.md)); вопросов нет |
| Контракт `specs/line-comments-contract.md` | Пройден: спека и план приведены к контракту; общая часть - ссылками на `LC-NN` |
| OpenSpec-поведение | `review-queue` и `path-id-bounds` сохраняются: `assignment_id` передаётся через POST как у ревью (LC-13), id вне `INTEGER` -> `404` |

Нарушений нет, Complexity Tracking не нужен.

### Допущения плана (неоднозначности, решения приняты без вопросов)

- **A-1**: Интерфейс сервиса, маршрут, ключи контекста и ошибки заданы общим контрактом (LC-07, LC-09…LC-14); `contracts/service-expectations.md` только ссылается на него.
- **A-2**: Числовых GET-параметров у страницы сдачи нет (LC-09, LC-18); единственный параметр - `assignment_id` (LC-13).
- **A-3**: Для ученика формы и поля номера строки нет (`can_comment = False`, LC-19).
- **A-4**: Ошибки номера строки и текста выводятся у своих полей через `_field_error.html` (`line_comment_errors`, LC-16); отдельного баннера нет.
- **A-5**: Якорь строки - `id="L{n}"`; редирект после успеха ведёт на `#L{n}` (LC-10), его проверяют тесты.
- **A-6**: Поля формы: видимое поле `line`, `textarea name=text`, скрытое `assignment_id` (как у формы ревью, LC-13, LC-18).

## Project Structure

### Documentation (this feature)

```text
specs/001-line-comments-ui/
├── spec.md
├── plan.md                              # этот файл
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── ui-routes.md                     # маршруты, поля, статусы, DOM-ориентиры для тестов
    └── service-expectations.md          # что UI ожидает от команды логики
```

### Source Code (repository root)

```text
app/
  web/
    submissions.py       # зона логики: render_submission (LC-12); UI не пишет
    line_comments.py     # зона логики: POST /submissions/{id}/line-comments; UI не создаёт (LC-26)
  templates/
    _code.html           # изменить: макрос по code_lines с явными номерами, id="L{n}" и комментариями под строками
    _line_comment.html   # новый: один комментарий (автор, дата, текст)
    _line_comment_form.html  # новый: единственная форма под кодом (номер + текст)
    submissions/detail.html  # изменить: пустое состояние, ошибки у полей, вызов нового макроса
  static/style.css      # изменить: стили строк, комментариев, формы, выделения строк с комментариями
  services/line_comments.py  # зона команды логики (UI не пишет)
tests/
  test_line_comments_ui.py   # новый
```

**Structure Decision**: слои проекта не меняются (`docs/architecture.md`). Роутер `app/web/line_comments.py` и `render_submission` пишет логика (LC-26), UI - шаблоны и CSS (LC-27); порядок: сначала логика (LC-28). Таблица страниц в `docs/architecture.md` не обновляется в рамках этого плана (документ вне зоны `specs/`); добавление строки - задача для tasks.

## Phase 0/1 результаты

- Research: [research.md](research.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/ui-routes.md](contracts/ui-routes.md), [contracts/service-expectations.md](contracts/service-expectations.md)
- Quickstart: [quickstart.md](quickstart.md)
