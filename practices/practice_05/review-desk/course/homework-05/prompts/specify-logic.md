# Промпт: команда логики, `/speckit-specify`

## До промпта (Иван, в новой сессии)

```bash
cd ~/hw5/logic/practices/practice_05/review-desk && mkdir -p course/homework-05/team-logic \
  && CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude --model sonnet
```

Обычный режим, не plan mode. По очереди: `/status` (идентификатор модели - в `00-setup.md`),
`/permissions` (видны deny-правила), `/memory` (автопамять выключена; если включена - выйти).
Затем вставить текст ниже целиком.

После итога агента: `/export course/homework-05/team-logic/session-log.md`, затем `/exit`.
(`mkdir -p` выше нужен, чтобы `/export` было куда писать.)

## Промпт

````text
/speckit-specify

Работаем во фреймворке Spec Kit (скилл speckit-specify), НЕ OpenSpec: скиллы openspec-* и
каталог openspec/changes/ не используй. Ты - команда логики. Сделай только шаг specify.

## Порядок работы

1. Проверки до любой работы (команды и их вывод покажи):
   - `pwd` - должно быть `/home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk`;
   - `git branch --show-current` - должно быть `hw5-logic`; `git status --short` - пусто;
   - `echo "${CLAUDE_CODE_DISABLE_AUTO_MEMORY:-unset}"` - должно быть `1`;
   - `cat .claude/settings.local.json` - есть `"autoMemoryEnabled": false` и `"Read(~/ITMOv2/**)"` в deny;
   - `ls specs 2>&1` - каталога ещё нет или он пуст.
   Если хоть одна проверка не прошла - остановись и сообщи, ничего не создавай.
2. Создай каталог фичи скриптом (именно `bash`, под `sh` скрипт падает):
   `bash .specify/scripts/bash/create-new-feature.sh --json --number 2 --short-name line-comments-logic "Построчные комментарии ментора к коду сдачи: данные и правила"`
   Ожидается `specs/002-line-comments-logic/spec.md`. Дальше по скиллу используй
   `SPECIFY_FEATURE_DIRECTORY=specs/002-line-comments-logic`, другой каталог не создавай.
3. Описание фичи для скилла - файл `course/homework-05/01-brief.md`, прочитай его целиком.
   Текст этого сообщения - инструкции к работе, а не описание фичи: в spec.md его не переноси.
   Выполни скилл speckit-specify для этого каталога (spec.md и checklists/requirements.md).
4. Остановись. Не запускай /speckit-clarify, /speckit-plan и другие шаги. Не коммить.
   Итог: путь к spec.md, итоги чеклиста, список маркеров [NEEDS CLARIFICATION] и допущений.

## Источники требований

Только `course/homework-05/01-brief.md` и сам проект: код (`app/`, `tests/`), `docs/baseline.md`,
`docs/architecture.md`, `openspec/specs/`, `AGENTS.md`, `.specify/memory/constitution.md`.
Ничего за пределами своей worktree (`/home/ivan_korchagin/hw5/logic`) не читай, кроме файлов
проекта внутри неё. Другие git-ветки не смотри: `git log/show/diff` только по `hw5-logic`.

## Зона ответственности команды логики

Данные, алгоритм, правила и API: что хранится о комментарии и как это связано с
существующими сущностями, как определяется строка кода, кто может создавать и видеть
комментарии, какие входные данные допустимы и какие ошибки возвращаются,
какие вызовы получает интерфейс. Шаблон spec.md требует формулировок без деталей реализации:
правила и ошибки опиши на уровне требований, технические детали (схема, маршруты, сигнатуры)
придут на шаге plan. Экраны, раскладка и отображение - зона другой команды: не проектируй
их, а записывай, что логика от них ожидает, как зависимость или допущение.

## Оформление

- Спека на русском. Заголовки разделов шаблона и идентификаторы (FR-001, SC-001 и т. п.)
  оставь как в шаблоне.
- Неясное - маркер `[NEEDS CLARIFICATION: вопрос]` (не больше 3, как требует скилл) или явное
  допущение в разделе Assumptions. Решение не выдумывай молча: каждое допущение записано.
- Если после проверки чеклиста останутся маркеры, вопросы в этой сессии не задавай и ответа
  не жди: маркеры остаются в spec.md, их разберёт отдельный шаг clarify.
- Пиши только в `specs/002-line-comments-logic/` и в `.specify/feature.json` (его создают скрипт
  и скилл). Остальные файлы проекта не меняй.
````
