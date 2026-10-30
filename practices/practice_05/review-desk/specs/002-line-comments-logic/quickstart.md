# Quickstart: проверка фичи

Предусловия: зависимости из `requirements.txt`, `.venv` (если есть).

## Автоматическая проверка

```bash
sh scripts/check.sh      # ожидается: CHECK: PASS
python -m pytest tests/test_line_comments.py -q
```

Каждое требование FR-001…FR-019 покрыто тестом, в docstring которого есть `[Л FR-nnn]` и `LC-NN` (SC-006, LC-29). Перед реализацией тесты пишутся первыми и показываются падающими (`AGENTS.md`, «Процесс»).

## Ручной сценарий

```bash
export SECRET_KEY=dev-secret
python -m app.cli create-user --username mentor --role mentor
python -m app.cli create-user --username alice --role student
python -m app.cli create-user --username bob --role student
uvicorn app.main:app --reload
```

1. Alice сдаёт код из нескольких строк.
2. Ментор отправляет форму `POST /submissions/<id>/line-comments` с `line=2`, `text=Замечание` и `assignment_id=<K>` → `303`, `Location: /submissions/<id>?assignment_id=<K>#L2`.
3. Ментор повторяет для `line=2` → на странице `GET /submissions/<id>` оба комментария под строкой 2, в порядке создания.
4. `line=999`, `line=05`, `line=+3`, `line=٣`, `line=1_000`, пустой `text` → `400`, комментарий не создан, введённые значения возвращены в форму; оба поля неверны → ошибки у обоих.
5. Alice: `GET /submissions/<id>` → `200` со своими комментариями, формы нет; `POST` → `403` при любом вводе.
6. Bob: `GET /submissions/<id>` чужой сдачи → `404`, как у `/submissions/999999`; `GET /submissions/<id>/line-comments` → не `200` (404 или 405).
7. `POST /submissions/9223372036854775808/line-comments` от ментора → `404`, не `500`; `/submissions/abc/line-comments` → `404`.
8. Ревью без вердикта (`400`) на сдаче с комментариями показывает их, без пустого состояния.
9. Статус сдачи и ревью после создания комментария не изменились; новая попытка Alice не наследует комментарии; существующие тесты baseline проходят.

Контракт: [contracts/line-comments.md](contracts/line-comments.md); модель: [data-model.md](data-model.md).
