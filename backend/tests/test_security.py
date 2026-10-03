import base64
import json
import unittest
from dataclasses import replace

import httpx
from cryptography.exceptions import InvalidTag
from fastapi.testclient import TestClient

from src.core.config import Settings
from src.core.crypto import FieldCipher
from src.main import create_app

OWNER = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
CONFIG = Settings("https://example.supabase.co", "sb_publishable_test", b"a" * 32, b"b" * 32,
                  ("https://testserver",), True)
CLIENT = {"cpf": "012.345.678-90", "name": "Cliente Teste", "email": "teste@example.com", "phone": "85999990000", "city": "Fortaleza"}
PRODUCT = {"name": "Estojo", "category": "Papelaria", "price": 20.25, "stock": 3, "description": "Azul"}


class FakeProvider:
    """Dublê somente do HTTP externo; a API, validação e criptografia são reais."""
    def __init__(self):
        self.rows = []
        self.requests = []
        self.role = "operator"
        self.failure = None
        self.logout_failure = False
        self.user_metadata = {}

    def __call__(self, request):
        self.requests.append(request)
        path, method = request.url.path, request.method
        token = request.headers.get("authorization", "")
        if path == "/auth/v1/token":
            return httpx.Response(200, json={"access_token": "valid", "refresh_token": "refresh", "expires_in": 3600})
        if path == "/auth/v1/logout":
            return httpx.Response(503) if self.logout_failure else httpx.Response(204)
        if path == "/auth/v1/user":
            if token != "Bearer valid":
                return httpx.Response(401, json={"message": "expired"})
            return httpx.Response(200, json={"id": OWNER, "email": "owner@example.com", "app_metadata": {"access_role": self.role}, "user_metadata": self.user_metadata})
        if self.failure:
            return httpx.Response(self.failure, json={"message": "DATABASE_PASSWORD_SHOULD_NOT_LEAK"})
        if path == "/rest/v1/rpc/dashboard_totals":
            return httpx.Response(200, json={"products": 0, "clients": len(self.rows), "stock": 0, "inventory_value": 0})
        if path == "/rest/v1/clients_support":
            return httpx.Response(200, json=[] if request.url.params["id"] != "gt.0" else [{"id": 1, "name": "Cliente Teste", "city": "Fortaleza", "cpf": "012.***.***-90", "email": "t***@***", "phone": "***0000"}])
        if path == "/rest/v1/clients":
            if method == "POST":
                row = json.loads(request.content)
                if any(r["cpf_bindex"] == row["cpf_bindex"] for r in self.rows):
                    return httpx.Response(409, json={"code": "23505"})
                row["id"] = len(self.rows) + 1
                self.rows.append(row)
                return httpx.Response(201, json=[row])
            if method == "GET":
                after = int(request.url.params["id"].split(".")[1])
                rows = [r for r in self.rows if r["id"] > after]
                if "cpf_bindex" in request.url.params:
                    rows = [r for r in rows if "eq." + r["cpf_bindex"] == request.url.params["cpf_bindex"]]
                return httpx.Response(200, json=rows[:1])  # exercita paginação mesmo com limite do servidor menor
            return httpx.Response(200, json=[])
        if path == "/rest/v1/products":
            return httpx.Response(201, json=[{"id": 1, **json.loads(request.content)}]) if method == "POST" else httpx.Response(200, json=[])
        raise AssertionError(f"Requisição inesperada: {method} {path}")


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        self.client = TestClient(create_app(CONFIG, httpx.MockTransport(self.provider)), base_url="https://testserver", raise_server_exceptions=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def authenticated(self):
        self.client.headers["Authorization"] = "Bearer valid"

    def test_requires_auth_and_rejects_forged_or_expired_token(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        for token in (None, "forged", "expired"):
            if token:
                self.client.headers["Authorization"] = "Bearer " + token
            self.assertEqual(self.client.get("/api/clients").status_code, 401)
            self.assertEqual(self.client.get("/api/dashboard").status_code, 401)

    def test_login_cookie_csrf_refresh_logout(self):
        payload = {"email": "owner@example.com", "password": "password-test"}
        self.assertEqual(self.client.post("/api/auth/login", json=payload).status_code, 403)
        self.client.headers["Origin"] = "https://testserver"
        login = self.client.post("/api/auth/login", json=payload)
        self.assertEqual(login.status_code, 200)
        self.assertNotIn("access_token", login.text)
        for cookie in login.headers.get_list("set-cookie"):
            self.assertIn("HttpOnly", cookie)
            self.assertIn("Secure", cookie)
            self.assertIn("SameSite=lax", cookie)
        self.assertEqual(self.client.get("/api/auth/session").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/refresh").status_code, 200)
        self.client.headers["Origin"] = "https://evil.example"
        self.assertEqual(self.client.post("/api/clients", json=CLIENT).status_code, 403)
        self.client.headers["Origin"] = "https://testserver"
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/clients").status_code, 401)

    def test_encrypts_persists_searches_and_rejects_duplicate_cpf(self):
        self.authenticated()
        created = self.client.post("/api/clients", json=CLIENT)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["cpf"], "01234567890")
        row = self.provider.rows[0]
        serialized = json.dumps(row)
        for value in ("01234567890", CLIENT["email"], CLIENT["phone"]):
            self.assertNotIn(value, serialized)
        self.assertEqual(self.client.get("/api/clients").json(), [created.json()])
        self.assertEqual(self.client.post("/api/clients/search", json={"cpf": "01234567890"}).json(), [created.json()])
        self.assertEqual(self.client.post("/api/clients", json={**CLIENT, "cpf": "01234567890"}).status_code, 409)
        for req in self.provider.requests:
            if req.url.path.startswith("/rest/"):
                self.assertEqual(req.headers["authorization"], "Bearer valid")
                self.assertNotIn("01234567890", str(req.url))

    def test_production_rejects_http_before_processing_credentials(self):
        with TestClient(create_app(CONFIG, httpx.MockTransport(self.provider)), base_url="http://testserver") as insecure:
            result = insecure.post("/api/auth/login", json={"email": "owner@example.com", "password": "test"}, headers={"Origin": "https://testserver"})
            self.assertEqual(result.status_code, 400)
            self.assertEqual(self.provider.requests, [])

    def test_logout_clears_local_cookies_even_when_auth_is_unavailable(self):
        self.client.headers["Origin"] = "https://testserver"
        self.client.post("/api/auth/login", json={"email": "owner@example.com", "password": "test"})
        self.provider.logout_failure = True
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/session").status_code, 401)

    def test_pagination_and_shared_persistence_across_api_instances(self):
        self.authenticated()
        for cpf in ("01234567890", "01234567891", "01234567892"):
            self.assertEqual(self.client.post("/api/clients", json={**CLIENT, "cpf": cpf}).status_code, 201)
        with TestClient(create_app(CONFIG, httpx.MockTransport(self.provider)), base_url="https://testserver") as replica:
            result = replica.get("/api/clients", headers={"Authorization": "Bearer valid"})
            self.assertEqual(len(result.json()), 3)

    def test_support_reads_masked_data_but_cannot_write_or_search(self):
        self.authenticated()
        self.provider.role = "support"
        self.provider.user_metadata = {"access_role": "operator", "data_owner_id": OTHER}
        response = self.client.get("/api/clients")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["email"], "t***@***")
        for path, data in (("/api/clients", CLIENT), ("/api/products", PRODUCT), ("/api/clients/search", {"cpf": CLIENT["cpf"]})):
            self.assertEqual(self.client.post(path, json=data).status_code, 403)
        self.assertEqual(self.client.delete("/api/clients/1").status_code, 403)
        self.assertEqual(self.client.delete("/api/products/1").status_code, 403)

    def test_cpf_money_and_standard_errors(self):
        self.authenticated()
        for cpf in (None, "", "123", "abc34567890", "٠١٢٣٤٥٦٧٨٩٠", 12345678901):
            result = self.client.post("/api/clients", json={**CLIENT, "cpf": cpf})
            self.assertEqual(result.status_code, 422)
        for price in (0, -1, 1.001, "NaN", "Infinity"):
            self.assertEqual(self.client.post("/api/products", json={**PRODUCT, "price": price}).status_code, 422)
        self.assertEqual(self.client.post("/api/products", json=PRODUCT).json()["price"], 20.25)
        self.assertEqual(self.client.delete("/api/clients/999").status_code, 404)
        self.provider.failure = 500
        result = self.client.get("/api/clients")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("DATABASE_PASSWORD", result.text)


class CryptoTests(unittest.TestCase):
    def setUp(self):
        self.cipher = FieldCipher(b"a" * 32, b"b" * 32)

    def test_randomized_ciphertext_and_owner_field_binding(self):
        encrypted = self.cipher.encrypt("01234567890", OWNER, "cpf")
        self.assertNotEqual(encrypted, self.cipher.encrypt("01234567890", OWNER, "cpf"))
        self.assertEqual(self.cipher.decrypt(encrypted, OWNER, "cpf"), "01234567890")
        for owner, field in ((OTHER, "cpf"), (OWNER, "email")):
            with self.assertRaises(InvalidTag):
                self.cipher.decrypt(encrypted, owner, field)
        raw = bytearray(base64.b64decode(encrypted[3:]))
        raw[-1] ^= 1
        with self.assertRaises(InvalidTag):
            self.cipher.decrypt("v1:" + base64.b64encode(raw).decode(), OWNER, "cpf")

    def test_blind_index_is_normalized_and_scoped(self):
        index = self.cipher.blind_index("012.345.678-90", OWNER, "cpf")
        self.assertEqual(index, self.cipher.blind_index("01234567890", OWNER, "cpf"))
        self.assertNotEqual(index, self.cipher.blind_index("01234567890", OTHER, "cpf"))
        self.assertNotEqual(index, self.cipher.blind_index("01234567890", OWNER, "email"))

    def test_rejects_insecure_configuration(self):
        for values in ({"supabase_url": "http://example.com"}, {"publishable_key": "sb_secret_no"}, {"blind_index_key": b"a" * 32}, {"allowed_origins": ("*",)}, {"allowed_origins": ("http://localhost",)}):
            with self.assertRaises(ValueError):
                replace(CONFIG, **values)


if __name__ == "__main__":
    unittest.main()
