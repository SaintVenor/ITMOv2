"""Тесты безопасности по мерам из THREAT_MODEL.md (раздел 4).

Только стандартная библиотека, стиль test_service.py / test_http.py (unittest).
Каждый тест проверяет БЕЗОПАСНОЕ поведение из соответствующей меры и поэтому
падает на исходном уязвимом сервисе; после исправлений в service.py должен
проходить. Имена тестов совпадают с колонкой «Тест» модели угроз.

Отдельный класс FunctionalityTest проверяет, что полезные сценарии из
lab/README.md сохраняются — эти тесты должны проходить и на исходном коде,
и после исправлений.

Коды ответов согласованы с мерами: 401 — нет аутентификации, 403 — доступ
запрещён, 400 — неверный запрос, 415 — неверный Content-Type, 429 —
ограничение частоты.
"""

import contextlib
import io
import json
import sqlite3
import threading
import unittest
from http.client import HTTPConnection
from unittest import mock
from http.server import ThreadingHTTPServer

from sandbox import Sandbox
from service import Shop, make_handler


# ==========================================================================
# Тесты на уровне Shop.dispatch (как ShopTest в test_service.py).
# ==========================================================================

class ShopSecurityTest(unittest.TestCase):
    def setUp(self):
        self.shop = Shop()
        self.addCleanup(self.shop.close)

    def request(self, method, path, body=None, headers=None):
        with self.shop.lock:
            return self.shop.dispatch(method, path, body or {}, headers or {})

    def login(self, username="alice", password="learn-alice"):
        status, result = self.request("POST", "/login", {"username": username, "password": password})
        self.assertEqual(status, 200)
        return {"X-Token": result["token"]}, result["token"]

    # --- T02 ---------------------------------------------------------------
    def test_login_rate_limited(self):
        """20 неверных попыток подряд должны заблокировать вход, даже верный."""
        for _ in range(20):
            self.request("POST", "/login", {"username": "alice", "password": "nope"})
        status, result = self.request("POST", "/login", {"username": "alice", "password": "learn-alice"})
        self.assertIn(status, (401, 429))
        self.assertNotIn("token", result)

    def test_login_username_length_limited(self):
        """Слишком длинное имя отклоняется (400) и не попадает в счётчик неудач."""
        name = "a" * 1000
        self.assertEqual(self.request("POST", "/login", {"username": name, "password": "x"})[0], 400)
        self.assertNotIn(name, getattr(self.shop, "login_failures", {}))

    def test_login_lockout_survives_failures_overflow(self):
        """Переполнение счётчика неудач чужими именами не снимает блокировку alice."""
        for _ in range(5):
            self.request("POST", "/login", {"username": "alice", "password": "nope"})
        failures = vars(self.shop).setdefault("login_failures", {})
        failures.update({f"spray-{i}": (1, 0.0) for i in range(10000)})
        self.request("POST", "/login", {"username": "mallory", "password": "nope"})
        status, result = self.request("POST", "/login", {"username": "alice", "password": "learn-alice"})
        self.assertEqual(status, 429)
        self.assertNotIn("token", result)

    # --- T03 ---------------------------------------------------------------
    def test_token_expires_and_logout(self):
        """Токен отзывается по истечении срока жизни и после /logout (401)."""
        auth, token = self.login()
        self.assertEqual(self.request("GET", "/orders", headers=auth)[0], 200)
        self.shop.sessions[token]["created"] = 0.0  # выдан в 1970 году: срок жизни истёк
        self.assertEqual(self.request("GET", "/orders", headers=auth)[0], 401)
        auth, _ = self.login()
        self.assertEqual(self.request("GET", "/orders", headers=auth)[0], 200)
        logout_status, _ = self.request("POST", "/logout", {}, auth)
        self.assertEqual(logout_status, 200)
        self.assertEqual(self.request("GET", "/orders", headers=auth)[0], 401)

    # --- T05 ---------------------------------------------------------------
    def test_passwords_not_stored_plain(self):
        """В accounts не должно быть паролей открытым текстом."""
        stored = json.dumps(self.shop.accounts, ensure_ascii=False)
        self.assertNotIn("learn-alice", stored)
        self.assertNotIn("learn-staff", stored)

    # --- T06 ---------------------------------------------------------------
    def test_profile_requires_owner(self):
        """Без токена — 401; alice не может читать чужой профиль id=2."""
        self.assertEqual(self.request("GET", "/profile?id=2")[0], 401)
        auth, _ = self.login()
        self.assertIn(self.request("GET", "/profile?id=2", headers=auth)[0], (403, 404))

    # --- T07 ---------------------------------------------------------------
    def test_profile_sql_injection_blocked(self):
        auth, _ = self.login()
        status, _ = self.request("GET", "/profile?id=1 OR 1=1", headers=auth)
        self.assertEqual(status, 400)
        status, result = self.request("GET", "/profile?id=0 UNION SELECT id,product,price,owner FROM orders",
                                      headers=auth)
        self.assertEqual(status, 400)
        self.assertNotIn("chair", json.dumps(result, ensure_ascii=False))

    # --- T08 ---------------------------------------------------------------
    def test_search_sql_injection_blocked(self):
        auth, _ = self.login("staff", "learn-staff")
        status, result = self.request("GET", "/search?q=' UNION SELECT id,product,price,owner FROM orders --",
                                      headers=auth)
        self.assertIn(status, (200, 400))
        self.assertNotIn("chair", json.dumps(result, ensure_ascii=False))
        self.assertNotIn("lamp", json.dumps(result, ensure_ascii=False))

    # --- T09 ---------------------------------------------------------------
    def test_search_staff_only(self):
        self.assertIn(self.request("GET", "/search?q=")[0], (401, 403))
        auth, _ = self.login()
        self.assertIn(self.request("GET", "/search?q=", headers=auth)[0], (401, 403))

    # --- T10 ---------------------------------------------------------------
    def test_orders_list_only_own(self):
        self.assertEqual(self.request("GET", "/orders")[0], 401)
        auth, _ = self.login()
        status, result = self.request("GET", "/orders", headers=auth)
        self.assertEqual(status, 200)
        owners = {row["owner"] for row in result}
        self.assertEqual(owners, {1})

    # --- T11 ---------------------------------------------------------------
    def test_order_price_from_catalog(self):
        auth, _ = self.login()
        status, order = self.request("POST", "/orders", {"product": "chair", "price": 1}, auth)
        self.assertEqual(status, 201)
        self.assertEqual(order["price"], 5000)

    # --- T12 ---------------------------------------------------------------
    def test_order_has_audit_fields(self):
        auth, _ = self.login()
        _, order = self.request("POST", "/orders", {"product": "chair"}, auth)
        keys = set(order)
        self.assertTrue(any("time" in k or "date" in k or "created" in k for k in keys),
                        f"нет поля времени в заказе: {sorted(keys)}")

    # --- T13 ---------------------------------------------------------------
    def test_export_requires_staff_session(self):
        self.assertIn(self.request("GET", "/admin/export", headers={"X-Role": "staff"})[0], (401, 403))
        auth, _ = self.login()
        self.assertEqual(self.request("GET", "/admin/export", headers={**auth, "X-Role": "staff"})[0], 403)
        staff_auth, _ = self.login("staff", "learn-staff")
        self.assertEqual(self.request("GET", "/admin/export", headers=staff_auth)[0], 200)

    # --- T14 ---------------------------------------------------------------
    def test_files_only_own_receipt(self):
        auth, _ = self.login()
        self.assertIn(self.request("GET", "/files?user=bob&path=receipt.txt", headers=auth)[0], (403, 404))

    # --- T15 ---------------------------------------------------------------
    def test_files_cannot_reach_private(self):
        auth, _ = self.login()
        for path in ("/files?user=..&path=private/operator-note.txt",
                     "/files?user=alice&path=../../private/operator-note.txt",
                     "/files?user=../private&path=operator-note.txt"):
            status, result = self.request("GET", path, headers=auth)
            self.assertIn(status, (403, 404))
            self.assertNotIn("TEST_ONLY_OPERATOR_SECRET", json.dumps(result, ensure_ascii=False))

    # --- T16, T17 вынесены в HttpSecurityTest: на уровне dispatch исключение
    #     поднимается наружу, обобщение ошибок делает HTTP-обработчик.
    # --- T18 ---------------------------------------------------------------
    def test_logs_mask_secrets(self):
        auth, token = self.login()
        self.request("GET", "/orders", headers=auth)
        dumped = json.dumps(self.shop.logs, ensure_ascii=False)
        self.assertNotIn("learn-alice", dumped)
        self.assertNotIn(token, dumped)

    # --- T19 ---------------------------------------------------------------
    def test_debug_logs_not_public(self):
        auth, _ = self.login()
        status, result = self.request("GET", "/debug/logs")
        self.assertIn(status, (401, 403, 404))
        self.assertNotIn("learn-alice", json.dumps(result, ensure_ascii=False))
        status, result = self.request("GET", "/debug/logs", headers=auth)
        self.assertEqual(status, 403)
        self.assertNotIn("learn-alice", json.dumps(result, ensure_ascii=False))

    # --- T20 ---------------------------------------------------------------
    def test_review_requires_login_and_known_product(self):
        self.assertEqual(self.request("POST", "/reviews", {"product": "chair", "text": "x"})[0], 401)
        auth, _ = self.login()
        self.assertEqual(self.request("POST", "/reviews", {"product": "unknown", "text": "x"}, auth)[0], 400)

    # --- T21 ---------------------------------------------------------------
    def test_review_text_validated(self):
        auth, _ = self.login()
        self.assertEqual(self.request("POST", "/reviews", {"product": "chair", "text": "A" * 10000}, auth)[0], 400)
        self.assertEqual(self.request("POST", "/reviews", {"product": "chair", "text": {"x": 1}}, auth)[0], 400)

    # --- T22 ---------------------------------------------------------------
    def test_reviews_view_escapes_html(self):
        auth, _ = self.login()
        self.request("POST", "/reviews", {"product": "chair", "text": "<script>alert(1)</script>"}, auth)
        _, html = self.request("GET", "/reviews/view", headers=auth)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    # --- T23 ---------------------------------------------------------------
    def test_assistant_context_only_own_order(self):
        auth, _ = self.login()
        self.assertIn(self.request("GET", "/assistant/context?order_id=2", headers=auth)[0], (403, 404))

    # --- T24 ---------------------------------------------------------------
    def test_assistant_context_sql_injection_blocked(self):
        auth, _ = self.login()
        status, result = self.request(
            "GET", "/assistant/context?order_id=0 UNION SELECT id,name,email,address FROM profiles", headers=auth)
        self.assertEqual(status, 400)
        self.assertNotIn("bob@example.invalid", json.dumps(result, ensure_ascii=False))

    # --- L01 ---------------------------------------------------------------
    def test_injected_review_cannot_trigger_delete(self):
        """Решение delete_tree, пришедшее от клиента, не должно удалять файлы."""
        auth, _ = self.login()
        status, _ = self.request("POST", "/assistant/execute",
                                 {"decision": {"tool": "delete_tree", "arguments": {"path": "files"}}}, auth)
        self.assertIn(status, (400, 403))
        self.assertIn("TEST_ALICE", self.shop.sandbox.read("files/alice/receipt.txt"))

    # --- L03 ---------------------------------------------------------------
    def test_customer_assistant_tools_restricted(self):
        auth, _ = self.login()
        self.assertEqual(self.request("POST", "/assistant/execute",
                                      {"decision": {"tool": "export_profiles", "arguments": {}}}, auth)[0], 403)
        self.assertIn(self.request("POST", "/assistant/execute",
                                   {"decision": {"tool": "delete_tree", "arguments": {"path": "files"}}}, auth)[0],
                      (400, 403))

    # --- L04 ---------------------------------------------------------------
    def test_assistant_execute_requires_login(self):
        status, _ = self.request("POST", "/assistant/execute",
                                 {"decision": {"tool": "export_profiles", "arguments": {}}})
        self.assertEqual(status, 401)

    # --- L05 ---------------------------------------------------------------
    def test_assistant_read_file_only_own(self):
        auth, _ = self.login()
        for path in ("files/bob/receipt.txt", "private/operator-note.txt",
                     "files/alice/../../private/operator-note.txt"):
            status, result = self.request("POST", "/assistant/execute",
                                          {"decision": {"tool": "read_file", "arguments": {"path": path}}}, auth)
            self.assertIn(status, (403, 404))
            self.assertNotIn("TEST_ONLY_OPERATOR_SECRET", json.dumps(result, ensure_ascii=False))
            self.assertNotIn("TEST_BOB", json.dumps(result, ensure_ascii=False))

    # --- L06 ---------------------------------------------------------------
    def test_delete_tree_denied_for_customer(self):
        auth, _ = self.login()
        for path in (".", "", "files"):
            status, _ = self.request("POST", "/assistant/execute",
                                     {"decision": {"tool": "delete_tree", "arguments": {"path": path}}}, auth)
            self.assertIn(status, (400, 403))
        # аноним тоже не может
        self.assertEqual(self.request("POST", "/assistant/execute",
                                      {"decision": {"tool": "delete_tree", "arguments": {"path": "."}}})[0], 401)
        for receipt in ("files/alice/receipt.txt", "files/bob/receipt.txt", "private/operator-note.txt"):
            self.assertTrue(self.shop.sandbox.read(receipt))

    # --- L07 ---------------------------------------------------------------
    def test_assistant_context_has_no_foreign_pii(self):
        auth, _ = self.login()
        # чужой отзыв и чужой профиль не должны попадать в контекст alice
        other_auth, _ = self.login("bob", "learn-bob")
        self.request("POST", "/reviews", {"product": "lamp", "text": "foreign review"}, other_auth)
        _, result = self.request("GET", "/assistant/context?order_id=1", headers=auth)
        prompt = result.get("prompt", "") if isinstance(result, dict) else ""
        self.assertNotIn("TEST_BOB", prompt)
        self.assertNotIn("bob@example.invalid", prompt)
        self.assertNotIn("foreign review", prompt)

    # --- L08 ---------------------------------------------------------------
    def test_assistant_context_size_bounded(self):
        auth, _ = self.login()
        for i in range(100):
            self.request("POST", "/reviews", {"product": "chair", "text": f"r{i}-" + "x" * 300}, auth)
        _, result = self.request("GET", "/assistant/context?order_id=1", headers=auth)
        prompt = result.get("prompt", "") if isinstance(result, dict) else ""
        self.assertLess(len(prompt), 100 * 300)

    # --- L09 ---------------------------------------------------------------
    def test_assistant_actions_audited(self):
        auth, _ = self.login()
        self.request("POST", "/assistant/execute",
                     {"decision": {"tool": "read_file", "arguments": {"path": "files/alice/receipt.txt"}}}, auth)
        audit = getattr(self.shop, "audit", None)
        self.assertTrue(audit, "нет журнала действий помощника (shop.audit)")
        dumped = json.dumps(audit, ensure_ascii=False)
        self.assertIn("read_file", dumped)
        self.assertNotIn("TEST_ALICE receipt", dumped)  # содержимое файла не логируется


# ==========================================================================
# Тесты на уровне реального HTTP (как HttpTest в test_http.py): Content-Type,
# Host — проверки транспорта, которых нет в dispatch.
# ==========================================================================

class HttpSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shop = Shop()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.shop))
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()
        cls.shop.close()

    def raw(self, method, path, body=None, content_type="application/json", host=None, headers=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        data = body.encode() if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
        conn.putrequest(method, path, skip_host=(host is not None))
        if host is not None:
            conn.putheader("Host", host)
        for name, value in (headers or {}).items():
            conn.putheader(name, value)
        if content_type is not None:
            conn.putheader("Content-Type", content_type)
        if data is not None:
            conn.putheader("Content-Length", str(len(data)))
        conn.endheaders(data)
        resp = conn.getresponse()
        text = resp.read().decode("utf-8", "replace")
        conn.close()
        return resp.status, text

    def alice(self):
        _, text = self.raw("POST", "/login", {"username": "alice", "password": "learn-alice"})
        return {"X-Token": json.loads(text)["token"]}

    # --- T25 (Content-Type) ------------------------------------------------
    def test_post_requires_json_content_type(self):
        status, _ = self.raw("POST", "/assistant/execute",
                             json.dumps({"decision": {"tool": "export_profiles", "arguments": {}}}),
                             content_type="text/plain")
        self.assertEqual(status, 415)

    # --- T25 (Host) --------------------------------------------------------
    def test_foreign_host_rejected(self):
        status, _ = self.raw("GET", "/health", content_type=None, host="evil.example")
        self.assertEqual(status, 400)

    # --- T16 ---------------------------------------------------------------
    def test_file_errors_hide_paths(self):
        """Ошибки ФС у вошедшего клиента не раскрывают абсолютный путь стенда."""
        auth = self.alice()
        receipt = self.shop.sandbox.path("files/alice/receipt.txt")
        content = receipt.read_text(encoding="utf-8")
        receipt.unlink()  # свой чек пропал: законный запрос получает ошибку ФС
        self.addCleanup(receipt.write_text, content, encoding="utf-8")
        for path in ("/files?user=alice&path=.", "/files?user=alice&path=missing.txt",
                     "/files?user=alice&path=receipt.txt"):
            status, text = self.raw("GET", path, body=None, content_type=None, headers=auth)
            self.assertIn(status, (403, 404), path)
            self.assertNotIn(str(self.shop.sandbox.root), text)
            self.assertNotIn("/tmp/", text)
            self.assertNotIn("Error", text)

    # --- T17 ---------------------------------------------------------------
    def test_internal_errors_are_generic(self):
        """Битый SQL и внутреннее исключение не возвращают текст и тип исключения."""
        auth = self.alice()
        status, text = self.raw("GET", "/profile?id=1;DROP", body=None, content_type=None, headers=auth)
        self.assertEqual(status, 400)
        self.assertNotIn("Error", text)       # напр. ProgrammingError в поле type
        self.assertNotIn("statement", text)   # текст исключения SQLite
        self.assertNotIn("sqlite", text.lower())
        # Настоящая внутренняя ошибка: запрос к БД падает внутри маршрута.
        server_log = io.StringIO()
        failure = sqlite3.OperationalError('near "DROP": syntax error')
        with mock.patch.object(self.shop, "rows", side_effect=failure), contextlib.redirect_stderr(server_log):
            status, text = self.raw("GET", "/profile", body=None, content_type=None, headers=auth)
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(text), {"error": "internal error"})
        self.assertIn("OperationalError", server_log.getvalue())  # детали — только в журнал сервера

    # --- T27 (Unicode-цифры в id) -------------------------------------------
    def test_ids_reject_unicode_digits(self):
        """«²» проходит str.isdigit(), но не int(): ответ 400, а не 500."""
        auth = self.alice()
        for path in ("/profile?id=%C2%B2", "/assistant/context?order_id=%C2%B2"):
            status, _ = self.raw("GET", path, body=None, content_type=None, headers=auth)
            self.assertEqual(status, 400, path)

    # --- T27 ---------------------------------------------------------------
    def test_malformed_body_returns_400(self):
        """Тело-массив и тело без обязательных полей → 400, а не 500.

        Тело без поля decision отправляется с токеном: по мере L04 запрос без
        токена к /assistant/execute получает 401 раньше проверки тела.
        """
        self.assertEqual(self.raw("POST", "/reviews", "[]")[0], 400)
        _, text = self.raw("POST", "/login", {"username": "alice", "password": "learn-alice"})
        auth = {"X-Token": json.loads(text)["token"]}
        self.assertEqual(self.raw("POST", "/assistant/execute", "{}", headers=auth)[0], 400)
        self.assertEqual(self.raw("POST", "/reviews", "{}", headers=auth)[0], 400)
        self.assertEqual(self.raw("POST", "/orders", "[]", headers=auth)[0], 400)
        self.assertEqual(self.raw("POST", "/assistant/execute", "{}")[0], 401)


# ==========================================================================
# Полезная функциональность из lab/README.md — проходит и до, и после фикса.
# ==========================================================================

class FunctionalityTest(unittest.TestCase):
    def setUp(self):
        self.shop = Shop()
        self.addCleanup(self.shop.close)

    def request(self, method, path, body=None, headers=None):
        with self.shop.lock:
            return self.shop.dispatch(method, path, body or {}, headers or {})

    def login(self, username="alice", password="learn-alice"):
        status, result = self.request("POST", "/login", {"username": username, "password": password})
        self.assertEqual(status, 200)
        return {"X-Token": result["token"]}

    def test_func_alice_sees_own_profile(self):
        auth = self.login()
        status, profile = self.request("GET", "/profile?id=1", headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(profile[0]["name"], "TEST_ALICE")

    def test_func_alice_sees_own_receipt(self):
        auth = self.login()
        status, receipt = self.request("GET", "/files?user=alice&path=receipt.txt", headers=auth)
        self.assertEqual(status, 200)
        self.assertIn("TEST_ALICE", receipt["content"])

    def test_func_buy_at_catalog_price(self):
        auth = self.login()
        status, order = self.request("POST", "/orders", {"product": "lamp"}, auth)
        self.assertEqual(status, 201)
        self.assertEqual((order["owner"], order["price"]), (1, 1500))

    def test_func_alice_can_leave_review(self):
        auth = self.login()
        status, _ = self.request("POST", "/reviews", {"product": "chair", "text": "Удобный стул"}, auth)
        self.assertEqual(status, 201)

    def test_func_assistant_reads_own_receipt(self):
        auth = self.login()
        status, context = self.request("GET", "/assistant/context?order_id=1", headers=auth)
        self.assertEqual(status, 200)
        self.assertIn("chair", context["prompt"])
        status, result = self.request("POST", "/assistant/execute",
                                      {"decision": {"tool": "read_file",
                                                    "arguments": {"path": "files/alice/receipt.txt"}}}, auth)
        self.assertEqual(status, 200)
        self.assertIn("TEST_ALICE", result["content"])

    def test_func_staff_can_export(self):
        auth = {**self.login("staff", "learn-staff"), "X-Role": "staff"}
        status, profiles = self.request("GET", "/admin/export", headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(len(profiles), 2)


if __name__ == "__main__":
    unittest.main()
