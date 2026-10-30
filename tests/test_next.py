import base64
import html
import json
import unittest

from app import RATE, app


def unesc(r):
    return html.unescape(r.get_data(as_text=True))


class NewTools(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def test_pages_load(self):
        for url in ["/", "/url", "/jwt", "/hash", "/time", "/diff", "/api", "/privacy"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_url(self):
        self.assertIn("a%20b%26c", unesc(self.c.post("/url", data={"text": "a b&c", "mode": "encode"})))
        self.assertIn("a b&c", unesc(self.c.post("/url", data={"text": "a%20b%26c", "mode": "decode"})))

    def test_hash(self):
        body = unesc(self.c.post("/hash", data={"text": "abc"}))
        self.assertIn("900150983cd24fb0d6963f7d28e17f72", body)
        self.assertIn("ba7816bf8f01cfea", body)

    def test_jwt(self):
        enc = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
        token = f'{enc({"alg": "HS256"})}.{enc({"sub": "1", "exp": 1})}.sig'
        body = unesc(self.c.post("/jwt", data={"text": token}))
        self.assertIn('"sub": "1"', body)
        self.assertIn("Expired", body)
        self.assertIn("valid JWT", unesc(self.c.post("/jwt", data={"text": "nope"})))

    def test_time(self):
        self.assertIn("1970-01-01T00:00:00+00:00", unesc(self.c.get("/time?value=0")))
        self.assertIn("2023-11-14T22:13:20+00:00", unesc(self.c.get("/time?value=1700000000000")))
        self.assertIn("Use a Unix", unesc(self.c.get("/time?value=banana")))

    def test_diff(self):
        body = unesc(self.c.post("/diff", data={"a": "a\nb", "b": "a\nc"}))
        self.assertIn('class="del">-b', body)
        self.assertIn('class="add">+c', body)


class Site(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def test_home_search(self):
        body = unesc(self.c.get("/?q=jwt"))
        self.assertIn("Decode a JSON Web Token", body)
        self.assertNotIn("scannable", body)

    def test_recent_cookie(self):
        self.c.get("/hash")
        self.assertIn("Recent", unesc(self.c.get("/")))

    def test_seo(self):
        self.assertIn("https://example.com/json", self.c.get("/sitemap.xml").get_data(as_text=True))
        self.assertIn("Sitemap: https://example.com/sitemap.xml", self.c.get("/robots.txt").get_data(as_text=True))
        self.assertIn('rel="canonical" href="https://example.com/json"', self.c.get("/json").get_data(as_text=True))

    def test_stats_needs_token(self):
        self.c.get("/json")
        self.assertEqual(self.c.get("/stats").status_code, 404)
        self.assertEqual(self.c.get("/stats?token=wrong").status_code, 404)
        r = self.c.get("/stats?token=secret")
        self.assertEqual(r.status_code, 200)
        self.assertIn("/json", r.get_data(as_text=True))


class Api(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def test_json_and_base64(self):
        r = self.c.post("/api/v1/json/format", json={"text": '{"a":1}'})
        self.assertEqual(r.get_json()["result"], '{\n  "a": 1\n}')
        r = self.c.post("/api/v1/base64/encode", json={"text": "hi"})
        self.assertEqual(r.get_json()["result"], "aGk=")
        self.assertEqual(self.c.post("/api/v1/json/format", json={"text": "{"}).status_code, 422)
        self.assertEqual(self.c.post("/api/v1/hash", json={}).status_code, 400)

    def test_uuid(self):
        self.assertEqual(len(self.c.get("/api/v1/uuid?count=2").get_json()["result"]), 2)

    def test_rate_limit(self):
        codes = [self.c.get("/api/v1/uuid").status_code for _ in range(61)]
        self.assertEqual(codes[-1], 429)
        self.assertEqual(codes[0], 200)
