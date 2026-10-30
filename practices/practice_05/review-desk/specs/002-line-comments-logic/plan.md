# Implementation Plan: Построчные комментарии ментора к коду сдачи — данные и правила

**Branch**: `002-line-comments-logic` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-line-comments-logic/spec.md`

## Summary

Ментор оставляет текстовые комментарии к конкретным строкам кода сдачи; ученик читает комментарии своей сдачи, ментор — любой. Подход: одна новая таблица `line_comments` (создаётся существующим `create_all`, остальные таблицы не меняются), новый сервис `app/services/line_comments.py` со всеми правилами (определение строки, права, диапазон строк, длина текста, поиск сдачи), тонкий роутер `app/web/line_comments.py` (`POST /submissions/{id}/line-comments`) и `render_submission`, который сам загружает комментарии и наполняет контекст страницы сдачи на всех путях рендера. Интерфейс, маршрут, ключи контекста и ошибки — в общем контракте [`specs/line-comments-contract.md`](../line-comments-contract.md). Новых категорий ошибок нет: `NotFound` 404, `Forbidden` 403, `ValidationError` 400.

## Technical Context

**Language/Version**: Python 3.11+ (как в `docs/architecture.md`)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Jinja2, Starlette sessions — только уже имеющиеся в `requirements.txt`; новых зависимостей нет

**Storage**: SQLite; одна новая таблица `line_comments` через `Base.metadata.create_all` (без миграций)

**Testing**: pytest + `TestClient`, SQLite в памяти на тест (`tests/conftest.py`); единая проверка `sh scripts/check.sh` → `CHECK: PASS`

**Target Platform**: Linux-сервер, серверный рендеринг, без JS

**Project Type**: web-service (FastAPI, слои `services/` и `web/`)

**Performance Goals**: не задаются; список комментариев сдачи — один запрос с сортировкой по индексу

**Constraints**: не менять схему `users`, `assignments`, `submissions`, `reviews` (FR-002); не менять поведение baseline, `review-queue`, `path-id-bounds` (FR-015); бизнес-правила только в `services/`

**Scale/Scope**: комментарии не лимитируются (Assumptions); текст ≤ `LINE_COMMENT_MAX` = 2 000 символов (LC-06), код сдачи ≤ 100 000 символов (существующий `CODE_MAX`)

Открытых вопросов нет; допущения плана собраны в [research.md](research.md).

## Constitution Check

*GATE: проверено до Phase 0 и повторно после Phase 1.*

| Принцип | Оценка |
|---|---|
| I. Источники правды (`AGENTS.md`, `docs/baseline.md`) | Pass: baseline не меняется; правила из `AGENTS.md` соблюдены |
| II. Слои | Pass: правила в `app/services/line_comments.py`, роуты только разбирают форму и вызывают сервис |
| III. Трассировка тестов | Pass: тесты в `tests/test_line_comments.py`, docstring с `LC-NN` и `[Л FR-nnn]` (LC-29, см. quickstart) |
| IV. Spec-driven scope | Pass: реализуются только FR-001…FR-019 |
| V. Неоднозначность на plan | Pass: неясности зафиксированы допущениями в research.md; вопросов нет |
| Preserved OpenSpec behavior | Pass: `review-queue`, `path-id-bounds` не затрагиваются; для id используется тот же `fits_sqlite_int` |

Общий контракт `specs/line-comments-contract.md` из конституции записан; план приведён к нему и при расхождении уступает ему.

Нарушений нет, раздел Complexity Tracking не заполняется.

## Project Structure

### Documentation (this feature)

```text
specs/002-line-comments-logic/
├── plan.md              # этот файл
├── research.md          # решения и допущения
├── data-model.md        # таблица line_comments и правила
├── quickstart.md        # как проверить фичу
├── contracts/
│   └── line-comments.md # детали логики поверх общего контракта (ссылки на LC-NN)
└── tasks.md             # создаёт /speckit-tasks (не этим шагом)
```

### Source Code (repository root)

```text
app/
├── models.py                  # + класс LineComment (новая таблица)
├── services/
│   └── line_comments.py       # НОВЫЙ: split_code_lines, line_count, can_comment, create_line_comment, list_line_comments, LINE_COMMENT_MAX
└── web/
    ├── line_comments.py       # НОВЫЙ: POST /submissions/{id}/line-comments (единственный экземпляр файла, LC-26)
    ├── submissions.py         # render_submission: db и новые аргументы только keyword-only в конце, сам загружает комментарии (LC-12)
    └── review.py              # только передача db= в render_submission (400 ревью показывает комментарии)
app/main.py                    # + include_router(line_comments.router)
tests/
└── test_line_comments.py      # НОВЫЙ: тесты по FR-001…FR-019 и LC-NN (docstring: LC-NN, [Л FR-nnn])
```

**Structure Decision**: слои проекта не меняются. Новые файлы лежат в существующих `services/` и `web/`, новая модель — в существующем `app/models.py`. Правки существующих файлов — только добавления (импорт, `include_router`, аргументы и ключи контекста `render_submission`, `db=` в его вызове из `review.py`). Шаблоны, раскладку и стили делает команда UI; эта фича шаблонов не трогает. Порядок реализации — сначала логика (LC-28).

## Complexity Tracking

Не заполняется: нарушений Constitution Check нет.
