# Архитектура: Review Desk

## Стек

- Python 3.11+, FastAPI, шаблоны Jinja2 (серверный рендеринг, без SPA и сборки фронтенда).
- SQLite через SQLAlchemy 2.0 (декларативные модели, `Session` на запрос).
- Сессии: `SessionMiddleware` из Starlette, ключ из переменной окружения `SECRET_KEY`.
- Хэш паролей: `bcrypt`.
- Тесты: pytest + `TestClient`, отдельная БД SQLite в памяти на каждый тест.

## Слои

```text
app/
  main.py          # создание приложения, middleware, подключение роутеров
  config.py        # настройки из окружения: SECRET_KEY, DATABASE_URL
  db.py            # engine, SessionLocal, get_db
  models.py        # User, Assignment, Submission, Review
  services/        # вся бизнес-логика; не знает про HTTP и шаблоны
    auth.py
    assignments.py
    submissions.py
    reviews.py
  web/             # HTTP-роуты: разбор формы → вызов сервиса → шаблон или редирект
    deps.py        # current_user, require_mentor, require_student
    auth.py
    assignments.py
    submissions.py
    review.py
  templates/
  static/style.css
  cli.py           # create-user
tests/
scripts/check.sh   # единая команда проверки
```

Правило: роуты в `web/` не содержат бизнес-правил. Проверки прав и статусов живут в `services/` и выражаются исключениями (`NotFound`, `Forbidden`, `Conflict`, `ValidationError`), которые `web/` переводит в коды ответа и сообщения.

## Модель данных

| Таблица | Поля |
|---|---|
| `users` | `id`, `username` (unique), `display_name`, `password_hash`, `role` (`mentor`/`student`), `created_at` |
| `assignments` | `id`, `title`, `description`, `author_id` → users, `created_at` |
| `submissions` | `id`, `assignment_id` → assignments, `student_id` → users, `attempt`, `code`, `status` (`pending`/`accepted`/`changes_requested`), `created_at`; unique (`assignment_id`, `student_id`, `attempt`) |
| `reviews` | `id`, `submission_id` → submissions (unique), `mentor_id` → users, `verdict`, `comment`, `created_at` |

## Страницы

| Метод и путь | Кто | Что |
|---|---|---|
| `GET/POST /login`, `POST /logout` | все | вход и выход |
| `GET /assignments` | все | список задач; у ученика — статус по каждой |
| `GET/POST /assignments/new` | mentor | создание задачи |
| `GET /assignments/{id}` | все | описание; у ученика — форма сдачи и свои попытки |
| `POST /assignments/{id}/submissions` | student | новая попытка |
| `GET /submissions/{id}` | mentor, автор | код, статус, ревью; у ментора — форма ревью |
| `POST /submissions/{id}/review` | mentor | вердикт и комментарий |
| `GET /review` | mentor | очередь `pending` |

## Запуск

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=dev-secret
python -m app.cli create-user --username mentor --role mentor
python -m app.cli create-user --username alice --role student
uvicorn app.main:app --reload
```
