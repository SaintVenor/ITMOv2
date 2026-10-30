# Implementation Plan: Построчные комментарии ментора к коду сдачи: интерфейс

**Branch**: `001-line-comments-ui` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-line-comments-ui/spec.md`

## Summary

Страница сдачи `GET /submissions/{id}` показывает код с явными номерами строк и комментарии ментора под своими строками.
Ментор выбирает строку ссылкой `?line=N` (перезагрузка, без JS), под строкой открывается форма, отправка идёт
`POST /submissions/{id}/line-comments` с редиректом `303` обратно на сдачу. Ученик-автор только читает. Вся
серверная логика (хранение, права, проверка номера строки и текста) - в `app/services/line_comments.py` команды логики;
UI-команда делает шаблоны, роуты-обёртки и стили и опирается на интерфейс сервиса из
[contracts/service-expectations.md](contracts/service-expectations.md). Решения и отвергнутые варианты - в
[research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (как в проекте)

**Primary Dependencies**: FastAPI, Jinja2, SQLAlchemy 2.0 (из `requirements.txt`; новых зависимостей нет)

**Storage**: N/A для UI. Новая таблица `line_comments` принадлежит команде логики ([data-model.md](data-model.md) описывает только вид данных для UI)

**Testing**: pytest + `TestClient`; тесты фичи в `tests/test_line_comments_ui.py`, имя или docstring ссылаются на `FR-NNN`

**Target Platform**: Linux server, браузеры без JavaScript

**Project Type**: web-service (серверный рендер Jinja2)

**Performance Goals**: N/A; комментарии сдачи грузятся одним запросом, обход строк кода - один проход в шаблоне

**Constraints**: без JS и сборки фронтенда; `|safe` запрещён; baseline, `review-queue`, `path-id-bounds` не меняются; слои не меняются

**Scale/Scope**: один экран (страница сдачи), один новый POST-маршрут; код до 100 000 символов (`CODE_MAX`), комментарии - до 5 000

## Constitution Check

*GATE: пройден до Phase 0, перепроверен после Phase 1.*

| Принцип | Оценка |
|---|---|
| I. Приоритет `AGENTS.md` и `docs/baseline.md` | Пройден: baseline не меняется, `docs/baseline.md` и `scripts/check.sh` не трогаем |
| II. Слои | Пройден: роуты в `app/web/` только разбирают форму и рендерят; правила - в сервисе. Единственный путь, где UI знает о строках, - вычисление `line_count` для рендера, оно берётся из сервиса |
| III. Трассировка тестов | Пройден: `tests/test_line_comments_ui.py`, `FR-NNN` в имени/docstring |
| IV. Объём по спеке | Пройден: редактирование, удаление, черновики и уведомления не планируются |
| V. Неоднозначности на plan | Зафиксированы как допущения (см. ниже и [research.md](research.md)); вопросов нет |
| Контракт `specs/line-comments-contract.md` | Файла нет. Допущение: при его появлении он приоритетнее; расхождения правятся в `contracts/` этой фичи |
| OpenSpec-поведение | `review-queue` и `path-id-bounds` сохраняются: `assignment_id` передаётся через POST как у ревью, id вне `INTEGER` -> `404` |

Нарушений нет, Complexity Tracking не нужен.

### Допущения плана (неоднозначности, решения приняты без вопросов)

- **A-1**: Контракта `line-comments-contract.md` нет; интерфейс сервиса в `contracts/service-expectations.md` - предложение UI-команды, логика его подтверждает или корректирует.
- **A-2**: Невалидный параметр `?line=` на `GET` молча игнорируется (форма не открывается, страница `200`). `404/400` на `GET` не нужны: страница сдачи существует.
- **A-3**: Для ученика `?line=` игнорируется.
- **A-4**: Сообщение об ошибке номера строки - общий баннер над кодом (`errors["line"]`); ошибка текста - под полем (`errors["text"]`).
- **A-5**: Якорь `#line-N` в редиректе после успеха и в ссылке «Комментировать» - только удобство прокрутки, на тесты не влияет.
- **A-6**: Поле формы называется `text`, номер строки - скрытое поле `line`; `assignment_id` (фильтр очереди) передаётся скрытым полем, как у формы ревью.

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
    submissions.py       # изменить: GET читает ?line=, передаёт comments и open_line в render_submission
    line_comments.py     # новый: POST /submissions/{id}/line-comments (подключить в main.py)
  templates/
    _code.html           # изменить: макрос code_block(code, ...) с явными номерами и комментариями под строками
    _line_comment.html   # новый: один комментарий (автор, дата, текст)
    _line_comment_form.html  # новый: форма под строкой
    submissions/detail.html  # изменить: пустое состояние, баннер ошибки, вызов нового макроса
  static/style.css      # изменить: стили строк, комментариев, формы, выделения
  main.py                # изменить: include_router(line_comments.router)
  services/line_comments.py  # зона команды логики (UI не пишет)
tests/
  test_line_comments_ui.py   # новый
```

**Structure Decision**: слои проекта не меняются (`docs/architecture.md`). Новый роутер `app/web/line_comments.py` по образцу `app/web/review.py`; рендер страницы сдачи переиспользует `render_submission`. Таблица страниц в `docs/architecture.md` не обновляется в рамках этого плана (документ вне зоны `specs/`); добавление строки - задача для tasks.

## Phase 0/1 результаты

- Research: [research.md](research.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/ui-routes.md](contracts/ui-routes.md), [contracts/service-expectations.md](contracts/service-expectations.md)
- Quickstart: [quickstart.md](quickstart.md)
