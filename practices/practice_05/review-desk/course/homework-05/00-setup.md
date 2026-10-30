# 00. Установка Spec Kit

Ветка `homework-05`, проект `practices/practice_05/review-desk`. Проверки перезапущены 2026-10-30
после `specify init` (коммит `87ef349 homework_05: add Spec Kit 1.2.5 scaffold`).

## Версии

| Инструмент | Версия | Команда |
|---|---|---|
| uv | 0.13.6 (x86_64-unknown-linux-gnu) | `uv --version` |
| specify-cli | 1.2.5 (установлен через `uv tool`) | `specify --version`, `uv tool list` |
| Python | 3.14.4 | `python3 --version` |

Параметры init (`.specify/init-options.json`): `ai: claude`, `ai_skills: true`, `script: sh`,
`here: true`, `feature_numbering: sequential`.

## Проверки после init

1. `specify check` → `Specify CLI is ready to use!`, `Claude Code (available)`.
2. `sh scripts/check.sh` → `165 passed, 1 warning in 3.68s`, `CHECK: PASS`.
   Предупреждение - `StarletteDeprecationWarning` про `httpx` из `.venv`, к Spec Kit отношения не имеет.
3. `git diff --quiet HEAD -- AGENTS.md docs/baseline.md scripts/check.sh` → без изменений;
   `git diff --stat 1f682be HEAD -- AGENTS.md docs/baseline.md scripts/check.sh app tests` → пусто:
   init не тронул код, тесты и защищённые файлы.
4. Коммит init содержит только `.specify/` (20 файлов, 2742 строки).

## Замечание

Скиллы `.claude/skills/speckit-*` созданы, но не попали в коммит: `.claude/` в `.gitignore`
(`git check-ignore -v .claude/` → `.gitignore:4`). Скиллы OpenSpec игнорируются так же, так что это
сложившийся порядок проекта, а не ошибка init. Следствие: клон ветки без `specify init` не
получит `/speckit-*`.
