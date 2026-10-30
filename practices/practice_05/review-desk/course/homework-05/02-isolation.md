# 02. Изоляция команд UI и логики

Цель: доказуемо, что сессии команд не видели работу друг друга до согласования контракта.

## Каналы утечки и чем закрыты

| Канал | Чем закрыт | Чем доказывается |
|---|---|---|
| Файлы чужой команды | Отдельная worktree на команду вне `~/ITMOv2`; `deny` на Read/Edit чужой worktree | `settings.local.json` + аудит лога |
| Git: чужая ветка (`git log/show hw5-*`) | Спеки команд не коммитятся, пока обе не закончат specify/clarify/plan. До этого в ветках только база | `git log homework-05..hw5-ui` / `..hw5-logic` пусты до снимка «до» |
| Рабочие заметки Ивана (`~/hw5-notes/handoff.md`, там вопросы, которые должны дожить до согласования) | `deny` на `~/hw5-notes/**` | аудит лога |
| Транскрипты других сессий (`~/.claude/projects/**`), включая основную, где эти вопросы обсуждались; кэши ввода и правок (`~/.claude/history.jsonl`, `paste-cache/`, `file-history/`, `plans/`) | `deny` на эти пути | аудит лога |
| Автопамять Claude Code (см. ниже) | Отключение обязательно: `autoMemoryEnabled: false` в `settings.local.json` **и** `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` при запуске | `/memory` в каждой сессии команды: автопамять выключена |
| Указатель текущей фичи `.specify/feature.json` | Уже в `.specify/.gitignore` (закоммичен Spec Kit), в ветки не попадёт | `git check-ignore -v .specify/feature.json` |
| Основной репозиторий `~/ITMOv2` (там будут результаты merge и материалы основной сессии) | `deny` на `Read(~/ITMOv2/**)` и `Edit(~/ITMOv2/**)` | `settings.local.json` + аудит лога |
| Основная сессия (координатор) | До merge не читает `~/hw5/ui`, `~/hw5/logic` и ветки `hw5-*` | этот лог и лог основной сессии |

`deny` закрывает Read/Edit/Grep/Glob, но не Bash (`cat ~/hw5/logic/...` пройдёт). Поэтому
закрытие доказывается аудитом логов, а не настройками.

## Автопамять

По документации Claude Code (https://code.claude.com/docs/en/memory, версия CLI 2.1.314):

- «The `<project>` path is derived from the git repository, so all worktrees and subdirectories
  within the same repo share one auto memory directory». Для обеих worktree это
  `~/.claude/projects/-home-ivan-korchagin-ITMOv2/memory/`.
- Автопамять «loaded at the start of every conversation» (первые 200 строк или 25KB `MEMORY.md`):
  она попадает в контекст сама, без вызова Read, поэтому `deny` её **не** останавливает. Что одна
  команда запишет в память, другая получит при старте.
- Отключение: ключ `"autoMemoryEnabled": false` в настройках проекта (используем
  `settings.local.json` каждой worktree) и переменная `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Ставим
  оба: ключ работает без участия Ивана при запуске, переменная - на случай, если ключ не
  подхватится.

Состояние до создания worktree (2026-10-30): каталог
`~/.claude/projects/-home-ivan-korchagin-ITMOv2/memory/` пуст (`ls -la`: только `.` и `..`, создан
2026-10-07). В `~/.claude/projects/-home-ivan-korchagin-ITMOv2-practices-practice-05-review-desk/`
каталога `memory/` нет. `~/.claude/CLAUDE.md` нет. В `history.jsonl` и `paste-cache/` нет содержания
вопросов, отложенных до согласования (поиск по их ключевым словам: 0 совпадений); есть только
упоминание пути к рабочим заметкам. Сами вопросы есть в транскрипте основной сессии
(`~/.claude/projects/-home-ivan-korchagin-ITMOv2-practices-practice-05-review-desk/*.jsonl`),
поэтому `~/.claude/projects/**` закрыт `deny`.

## Одна модель у обеих команд

Решение Ивана: обе команды на Sonnet. Сессии запускаются с `--model sonnet`. Точный
идентификатор модели каждая сессия берёт из `/status` в начале работы, Иван записывает его в
`00-setup.md` (не по памяти и не из настроек).

## Команды (запускает Иван, из `~/ITMOv2`)

```bash
cd ~/ITMOv2
git status --short            # должно быть пусто: worktree берут закоммиченный homework-05
git worktree add ~/hw5/ui    -b hw5-ui    homework-05
git worktree add ~/hw5/logic -b hw5-logic homework-05

P=practices/practice_05/review-desk
for t in ui logic; do
  cp    ~/ITMOv2/$P/CLAUDE.md ~/hw5/$t/$P/
  cp -r ~/ITMOv2/$P/.claude   ~/hw5/$t/$P/
  ln -s ~/ITMOv2/$P/.venv     ~/hw5/$t/$P/.venv
done

# deny-правила: команда UI не видит logic, и наоборот
for pair in "ui logic" "logic ui"; do
  set -- $pair
  cat > ~/hw5/$1/$P/.claude/settings.local.json <<EOF
{
  "permissions": {
    "deny": [
      "Read(~/hw5/$2/**)",
      "Edit(~/hw5/$2/**)",
      "Read(~/hw5-notes/**)",
      "Read(~/.claude/projects/**)",
      "Read(~/.claude/history.jsonl)",
      "Read(~/.claude/paste-cache/**)",
      "Read(~/.claude/file-history/**)",
      "Read(~/.claude/plans/**)",
      "Edit(~/ITMOv2/**)",
      "Read(~/ITMOv2/**)"
    ]
  },
  "autoMemoryEnabled": false
}
EOF
done
```

`CLAUDE.md` и `.claude/` не в git (`.git/info/exclude`, `.gitignore`), поэтому их копируют
вручную. Venv общий через симлинк: editable-установок проекта в нём нет, так что `app`
импортируется из текущей worktree (проверка ниже).

## Проверки после создания (запускает Иван, вывод - в этот файл)

```bash
cd ~/ITMOv2 && git worktree list && git log --oneline -1 hw5-ui && git log --oneline -1 hw5-logic
for t in ui logic; do
  cd ~/hw5/$t/practices/practice_05/review-desk
  .venv/bin/python -c "import app; print(app.__file__)"   # ожидается путь внутри ~/hw5/$t
  git check-ignore -v .specify/feature.json CLAUDE.md .claude/
  sh scripts/check.sh | tail -1                            # ожидается CHECK: PASS
done
```

В начале каждой сессии команды, до первого промпта: `/status` (идентификатор модели - в
`00-setup.md`), `/permissions` (deny-правила видны, синтаксис принят), `/memory` (автопамять
выключена). Если `/memory` показывает автопамять включённой - сессию закрыть и не продолжать.

## Запуск сессий команд

```bash
cd ~/hw5/ui/practices/practice_05/review-desk    && CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude --model sonnet
cd ~/hw5/logic/practices/practice_05/review-desk && CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude --model sonnet
```

Нумерация фич: UI - `--number 1 --short-name line-comments-ui` (`specs/001-line-comments-ui/`),
логика - `--number 2 --short-name line-comments-logic` (`specs/002-line-comments-logic/`).
Каждая сессия в конце делает `/export course/homework-05/team-<t>/session-log.md`.

## Аудит логов (после каждой сессии команды, до merge)

Шаблон для лога команды `t`, `o` - чужая команда (`ui`/`logic`), `N` - чужой номер (`001`/`002`).
Каждый `/export` команды (specify, clarify, plan) проверяется отдельно, вместе с grep на email.

```bash
P=practices/practice_05/review-desk
audit() {  # audit <t> <o> <N> <log>
  grep -nE "specs/$3-|$3-line-comments|line-comments-$2|hw5/$2|hw5-$2|hw5-notes|handoff|\.claude/(projects|history\.jsonl|paste-cache|file-history|plans)|ITMOv2/practices" "$4"
}
for log in ~/hw5/ui/$P/course/homework-05/team-ui/*session-log.md;       do echo "== $log"; audit ui logic 002 "$log"; done
for log in ~/hw5/logic/$P/course/homework-05/team-logic/*session-log.md; do echo "== $log"; audit logic ui 001 "$log"; done
```

`ITMOv2/practices` добавлен Иваном после правила `Read(~/ITMOv2/**)`: ловит обращение к основному
checkout по пути. Память (`~/.claude/projects/<repo>/memory`) покрыта шаблоном `.claude/projects`.

Ожидание: пустой вывод. Любое совпадение разбирается и записывается сюда, а не удаляется из лога.

## Результаты

### Создание worktree (2026-10-30, выполнял Иван)

`git worktree add`, копирование `CLAUDE.md`/`.claude`, симлинк `.venv` и запись
`settings.local.json` прошли без ошибок (со слов Ивана). Обе ветки созданы от `e5d94db`
(`homework_05: add feature brief and team isolation plan`): бриф и этот план в них есть,
спек команд нет.

```text
$ cd ~/ITMOv2 && git worktree list && git log --oneline -1 hw5-ui && git log --oneline -1 hw5-logic
/home/ivan_korchagin/ITMOv2 e5d94db [homework-05]
/home/ivan_korchagin/hw5/logic e5d94db [hw5-logic]
/home/ivan_korchagin/hw5/ui e5d94db [hw5-ui]
e5d94db (HEAD -> homework-05, hw5-ui, hw5-logic) homework_05: add feature brief and team isolation plan
e5d94db (HEAD -> homework-05, hw5-ui, hw5-logic) homework_05: add feature brief and team isolation plan

$ for t in ui logic; do cd ~/hw5/$t/practices/practice_05/review-desk; .venv/bin/python -c "import app; print(app.__file__)"; git check-ignore -v .specify/feature.json CLAUDE.md .claude/; sh scripts/check.sh | tail -1; done
/home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/app/__init__.py
practices/practice_05/review-desk/.specify/.gitignore:6:feature.json .specify/feature.json
/home/ivan_korchagin/ITMOv2/.git/info/exclude:10:practices/practice_05/review-desk/CLAUDE.md CLAUDE.md
practices/practice_05/review-desk/.gitignore:4:.claude/ .claude/
CHECK: PASS
/home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/app/__init__.py
practices/practice_05/review-desk/.specify/.gitignore:6:feature.json .specify/feature.json
/home/ivan_korchagin/ITMOv2/.git/info/exclude:10:practices/practice_05/review-desk/CLAUDE.md CLAUDE.md
practices/practice_05/review-desk/.gitignore:4:.claude/ .claude/
CHECK: PASS
```

Примечание к логу: при вставке в чат markdown съел двойные подчёркивания (`app.file`,
`app/init.py`). Здесь восстановлено `__file__`/`__init__.py`, больше ничего не менялось.

Вывод:
- обе worktree на `e5d94db`, ветки `hw5-ui`/`hw5-logic` пока не отличаются от `homework-05`;
- `app` импортируется из своей worktree, общий симлинк `.venv` код не подменяет;
- `feature.json`, `CLAUDE.md`, `.claude/` игнорируются в обеих worktree (exclude общий через `.git`);
- `CHECK: PASS` в обеих.

Ещё не сделано: проверки `/status`, `/permissions`, `/memory` в каждой сессии и аудит логов.

### Наблюдение при подготовке промптов

В Spec Kit 1.2.5 скилл `speckit-specify` сам **не** вызывает `create-new-feature.sh`. Номер
каталога он берёт как «следующий свободный в `specs/`», а `specs/` пуст в обеих worktree,
поэтому обе команды получили бы `001-`. Чтобы задать номер явно, промпты сначала запускают
`bash .specify/scripts/bash/create-new-feature.sh --json --number N --short-name ...`, а затем
передают скиллу готовый `SPECIFY_FEATURE_DIRECTORY`. Под `sh` (dash) скрипт падает
(`Syntax error: "(" unexpected`), нужен `bash`, хотя в init выбрано `--script sh`.

### Правило `Read(~/ITMOv2/**)` (добавлено 2026-10-30, выполнял Иван)

Причина: worktree команд лежат вне `~/ITMOv2`, но основной checkout `~/ITMOv2` доступен с диска.
В нём будут материалы основной сессии и после merge обе спеки, а `Edit(~/ITMOv2/**)` чтение
не закрывал. Правило дописано в `deny` обоих `settings.local.json` (скрипт Ивана на python
дописывает его в конец списка, если его там ещё нет). Блок «Команды» выше обновлён, чтобы
давать то же состояние.

Побочный эффект: `.venv` в worktree - симлинк на `~/ITMOv2/.../.venv`, поэтому инструмент
Read не открывает файлы внутри `.venv`. Bash и python правило не затрагивает:
`.venv/bin/python` и `sh scripts/check.sh` работают как раньше. Командам читать
`site-packages` не нужно.

Исключение `.venv` в `.git/info/exclude` не понадобилось: `git status --short` пуст в обеих
worktree и до, и после (скрипт добавил бы исключение только при `.venv` в статусе):

```text
=== 2. git status ДО ===
[ui]
[logic]
=== 3. git status ПОСЛЕ ===
[ui]
[logic]
```

Вывод записи правила (как вставлен в чат):

```text
/home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/.claude/settings.local.json -> Read(~/ITMOv2/)
/home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/.claude/settings.local.json -> Read(~/ITMOv2/**)
```

Строки различаются: у ui нет `**`. Скорее всего, это markdown съел пару `**` при вставке, как
подчёркивания выше. Основная сессия файлы `~/hw5/*` до merge не читает, поэтому проверка
за Иваном (результат ниже). Кроме того, промпт команды первым шагом проверяет `"Read(~/ITMOv2/**)"`
в своём `settings.local.json`.

Проверка (вывод Ивана, вставлен в блоке кода, поэтому `**` сохранились):

```text
$ grep -n ITMOv2 ~/hw5/*/practices/practice_05/review-desk/.claude/settings.local.json
/home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/.claude/settings.local.json:12:      "Edit(~/ITMOv2/**)",
/home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/.claude/settings.local.json:13:      "Read(~/ITMOv2/**)"
/home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/.claude/settings.local.json:12:      "Edit(~/ITMOv2/**)",
/home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/.claude/settings.local.json:13:      "Read(~/ITMOv2/**)"
```

Вывод: в обеих worktree правила одинаковые и полные (`Edit` и `Read` на `~/ITMOv2/**`).
Расхождение в выводе выше - артефакт разметки при вставке, файлы в порядке.
Урок для процесса: вывод терминала вставлять в чат только в блоке кода.

### Сессии specify (2026-10-30, данные Ивана)

| | UI | Логика |
|---|---|---|
| Модель (`/status`) | `claude-sonnet-5-5` | `claude-sonnet-5-5` |
| cwd (`/status`) | своя worktree | своя worktree |
| Setting sources (`/status`) | User settings, Project local settings | то же |
| `/permissions` | все deny-правила загружены | то же |
| `/memory` | Auto-memory: false | то же |
| Итог specify | маркеров `[NEEDS CLARIFICATION]` - 2 | маркеров - 2 (FR-019, SC-006); чеклист 15/16, не пройден только пункт «No [NEEDS CLARIFICATION] markers remain» |
| Коммиты | нет | нет |

**Отклонение от процедуры (в обеих сессиях).** `/status`, `/permissions`, `/memory` выполнены
после промпта, а не до него, как требовал раздел «До промпта». На изоляцию это не влияет:
настройки (`deny`, `autoMemoryEnabled: false`) загружаются при запуске сессии, а не командами
просмотра, и агент сам проверил `settings.local.json` и переменную автопамяти на шаге 1 до
любой работы. Слабее стало только доказательство: проверка шла после работы, а не до неё. В
промптах clarify и plan проверки снова стоят до промпта.

**Доказательства.** Панели `/status`, `/permissions`, `/memory` в `/export` не попадают, а
скриншотов нет (решение Ивана). Изоляцию подтверждают: этот документ (настройки и проверки
worktree), вывод проверок агента на шаге 1 в логах specify и аудит логов specify (ниже).
Данные из панелей в таблице выше записаны со слов Ивана.

**Clarify и дальнейшие шаги (решение Ивана).** Отдельных доказательств изоляции не собираем:
ни скриншотов, ни аудита. Проверки агента на шаге 1 остаются в промптах, и их вывод попадёт
в `/export`.

**Аудит логов** (`team-<t>/session-log.md`, шаблоны из раздела «Аудит логов», плюс grep на email):

```text
===== ui =====
-rw-r--r-- 1 ivan_korchagin ivan_korchagin 11643 Oct 30 05:15 /home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/course/homework-05/team-ui/session-log.md
--- email ---
(пусто)
--- аудит ---
(пусто)
===== logic =====
-rw-r--r-- 1 ivan_korchagin ivan_korchagin 12245 Oct 30 05:20 /home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/course/homework-05/team-logic/session-log.md
--- email ---
(пусто)
--- аудит ---
(пусто)
```

Вывод: следов чужой команды, рабочих заметок, служебных каталогов `~/.claude` и основного
checkout в логах specify нет, email нет.


### Сессии clarify и plan (2026-10-30, данные Ивана)

Обе команды выполнили clarify и plan в своих worktree. Ничего не закоммичено, tasks/implement
не запускались, код приложения не менялся.

Аудит clarify-логов (шаблоны из раздела «Аудит логов», плюс grep на email):

```text
===== ui =====
-rw-r--r-- 1 ivan_korchagin ivan_korchagin 32282 Oct 30 05:58 /home/ivan_korchagin/hw5/ui/practices/practice_05/review-desk/course/homework-05/team-ui/clarify-session-log.md
--- email ---
(пусто)
--- аудит ---
(пусто)
===== logic =====
-rw-r--r-- 1 ivan_korchagin ivan_korchagin 49004 Oct 30 05:52 /home/ivan_korchagin/hw5/logic/practices/practice_05/review-desk/course/homework-05/team-logic/clarify-session-log.md
--- email ---
(пусто)
--- аудит ---
(пусто)
```

**Инцидент с логом clarify команды логики.** Сессию закрыли без `/export`. Лог восстановлен так:
`claude --resume`, затем `/export`. Но `/export` положил файл в `specs/002-line-comments-logic/course/...`,
потому что cwd сессии сменился. Файл перенесён в `team-logic/`, лишний каталог удалён. Вывод:
путь в `/export` разрешается от текущего cwd сессии, а не от каталога запуска; после `--resume`
нужно проверить cwd.
