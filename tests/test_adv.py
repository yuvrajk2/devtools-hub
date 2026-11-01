import base64
import hashlib
import hmac
import html
import json
import unittest
from datetime import datetime, timezone

from app import app
from core import RATE
from tools.dev import next_runs, parse_cron


def body(r):
    return html.unescape(r.get_data(as_text=True))


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class Cidr(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_v4(self):
        b = body(self.c.get("/cidr?net=192.168.1.77/24&ip=192.168.1.200"))
        for want in ("192.168.1.0/24", "255.255.255.0", "0.0.0.255", "192.168.1.255", "192.168.1.1", "192.168.1.254", "254", "Yes"):
            self.assertIn(want, b)
        self.assertIn("No", body(self.c.get("/cidr?net=10.0.0.0/8&ip=11.0.0.1")))

    def test_edges_and_v6_and_errors(self):
        self.assertIn("Usable hosts</span><span>2<", body(self.c.get("/cidr?net=10.0.0.0/31")).replace("\n", ""))
        self.assertIn("2001:db8::/32", body(self.c.get("/cidr?net=2001:db8::1/32")))
        self.assertIn("does not appear", body(self.c.get("/cidr?net=nope")))


class Regex(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def post(self, **kw):
        return body(self.c.post("/regex", data=kw))

    def test_matches_groups_and_flags(self):
        b = self.post(pattern=r"(\w+)@(\w+)\.com", text="mail bob@example.com now")
        self.assertIn("1 match", b)
        self.assertIn("<mark>bob@example.com</mark>", b)
        self.assertIn("group 1", b)
        self.assertIn("2 matches", self.post(pattern="abc", text="ABC abc", flags="i"))

    def test_invalid_and_limits(self):
        self.assertIn("Invalid pattern", self.post(pattern="(unclosed", text="x"))
        self.assertIn("limited to 500", self.post(pattern="a" * 501, text="x"))

    def test_catastrophic_pattern_times_out(self):
        b = self.post(pattern=r"(a+)+$", text="a" * 40 + "b")
        self.assertIn("Timed out", b)


class Cron(unittest.TestCase):
    def test_weekday_business_hours(self):
        sets, parts = parse_cron("*/15 9-17 * * 1-5")
        runs = next_runs(sets, parts, utc(2026, 10, 30, 12, 0))  # a Friday
        self.assertEqual(runs[0], utc(2026, 10, 30, 12, 0))
        self.assertEqual(runs[3], utc(2026, 10, 30, 12, 45))
        self.assertEqual(next_runs(sets, parts, utc(2026, 10, 30, 17, 46))[0], utc(2026, 11, 2, 9, 0))  # Monday

    def test_leap_day_and_aliases_and_either_day_rule(self):
        sets, parts = parse_cron("0 0 29 2 *")
        self.assertEqual(next_runs(sets, parts, utc(2026, 3, 1, 0, 0), 1)[0], utc(2028, 2, 29, 0, 0))
        sets, parts = parse_cron("@daily")
        self.assertEqual(next_runs(sets, parts, utc(2026, 1, 1, 0, 1), 1)[0], utc(2026, 1, 2, 0, 0))
        sets, parts = parse_cron("0 0 13 * 5")  # 13th OR any Friday
        days = {t.day for t in next_runs(sets, parts, utc(2026, 11, 1, 0, 0), 6)}
        self.assertIn(13, days)
        self.assertIn(6, days)

    def test_names_and_errors(self):
        sets, _ = parse_cron("0 0 * jan,mar mon-fri")
        self.assertEqual(sets[3], {1, 3})
        self.assertEqual(sets[4], {1, 2, 3, 4, 5})
        self.assertEqual(parse_cron("0 0 * * 7")[0][4], {0})
        for bad in ("61 * * * *", "* * * *", "*/0 * * * *", "5-1 * * * *", "a * * * *"):
            with self.assertRaises(ValueError, msg=bad):
                parse_cron(bad)

    def test_page(self):
        c = app.test_client()
        self.assertIn("Next runs", body(c.get("/cron")))
        self.assertIn("5 fields", body(c.get("/cron?expr=* * *")))


class JwtHmac(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def token(self, secret, alg="HS256"):
        enc = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).rstrip(b"=").decode()
        signing = f'{enc({"alg": alg})}.{enc({"sub": "1"})}'
        sig = hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest()
        return signing + "." + base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

    def test_verify(self):
        t = self.token("s3cret")
        self.assertIn("Valid (HS256)", body(self.c.post("/jwt", data={"text": t, "secret": "s3cret"})))
        self.assertIn("Invalid (HS256)", body(self.c.post("/jwt", data={"text": t, "secret": "wrong"})))
        self.assertNotIn("Signature", body(self.c.post("/jwt", data={"text": t})))
        self.assertIn("Cannot verify", body(self.c.post("/jwt", data={"text": self.token("k", "RS256"), "secret": "k"})))

    def test_hmac(self):
        b = body(self.c.post("/hash", data={"text": "The quick brown fox jumps over the lazy dog", "key": "key"}))
        self.assertIn("f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8", b)
        self.assertIn("HMAC-SHA-256", b)


if __name__ == "__main__":
    unittest.main()
