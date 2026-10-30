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
      "Edit(~/ITMOv2/**)"
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

## Аудит логов (после обеих сессий, до merge)

```bash
P=practices/practice_05/review-desk
COMMON='hw5-notes|handoff|\.claude/(projects|paste-cache|file-history|plans|history\.jsonl)|/memory/'
grep -nE "specs/002-|002-line-comments|line-comments-logic|hw5/logic|hw5-logic|$COMMON" \
  ~/hw5/ui/$P/course/homework-05/team-ui/session-log.md
grep -nE "specs/001-|001-line-comments|line-comments-ui|hw5/ui|hw5-ui|$COMMON" \
  ~/hw5/logic/$P/course/homework-05/team-logic/session-log.md
```

Ожидание: пустой вывод. Любое совпадение разбирается и записывается сюда, а не удаляется из лога.

## Результаты

_Заполняется после выполнения команд._
