# Quickstart: проверка фичи

Предусловия: зависимости из `requirements.txt`, `.venv` (если есть).

## Автоматическая проверка

```bash
sh scripts/check.sh      # ожидается: CHECK: PASS
python -m pytest tests/test_line_comments.py -q
```

Каждое требование FR-001…FR-019 покрыто тестом, в имени или docstring которого есть идентификатор FR (SC-006). Перед реализацией тесты пишутся первыми и показываются падающими (`AGENTS.md`, «Процесс»).

## Ручной сценарий

```bash
export SECRET_KEY=dev-secret
python -m app.cli create-user --username mentor --role mentor
python -m app.cli create-user --username alice --role student
python -m app.cli create-user --username bob --role student
uvicorn app.main:app --reload
```

1. Alice сдаёт код из нескольких строк.
2. Ментор отправляет форму `POST /submissions/<id>/comments` с `line=2`, `text=Замечание` → `303`.
3. Ментор повторяет для `line=2` → оба комментария в `GET /submissions/<id>/comments`, в порядке создания.
4. `line=999`, `line=05`, `line=+3`, `line=٣`, пустой `text` → `400`, комментарий не создан.
5. Alice: `GET /submissions/<id>/comments` → `200` со своими комментариями; `POST` → `403` при любом вводе.
6. Bob: `GET /submissions/<id>/comments` чужой сдачи → `404`, как у `/submissions/999999`.
7. `/submissions/9223372036854775808/comments` → `404`, не `500`.
8. Статус сдачи и ревью после создания комментария не изменились; существующие тесты baseline проходят.

Контракт: [contracts/line-comments.md](contracts/line-comments.md); модель: [data-model.md](data-model.md).
