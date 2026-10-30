import html
import io
import json
import unittest
from unittest import mock

import app as appmod
from app import RATE, app
from tests.helpers import prime_rates


def body(r):
    return html.unescape(r.get_data(as_text=True))


class Currency(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()
        prime_rates()

    def test_default_rows(self):
        b = body(self.c.get("/currency"))
        self.assertIn('name="v-USD" value="1.00"', b)
        self.assertIn('name="v-EUR" value="0.5"', b)
        self.assertIn('name="v-JPY" value="75.00"', b)
        self.assertIn("Rates By Exchange Rate API", b)

    def test_edit_any_field_updates_all(self):
        b = body(self.c.post("/currency", data={"v-USD": "1.00", "p-USD": "1.00", "v-EUR": "10", "p-EUR": "0.5"}))
        self.assertIn('name="v-USD" value="20.00"', b)
        self.assertIn('name="v-GBP" value="5.00"', b)
        self.assertIn('name="v-JPY" value="1,500.00"', b)

    def test_thousands_and_errors(self):
        b = body(self.c.post("/currency", data={"v-USD": "1,000", "p-USD": "1.00"}))
        self.assertIn('name="v-EUR" value="500.00"', b)
        b = body(self.c.post("/currency", data={"v-USD": "abc", "p-USD": "1.00"}))
        self.assertIn("Enter a number", b)

    def test_add_currency(self):
        b = body(self.c.post("/currency", data={"also": "npr, xyz"}))
        self.assertIn('name="v-NPR" value="80.00"', b)
        self.assertNotIn("v-XYZ", b)

    def test_unavailable(self):
        with mock.patch("app.get_rates", return_value=None):
            r = self.c.get("/currency")
        self.assertEqual(r.status_code, 503)
        self.assertIn("unavailable", body(r))

    def test_fetch_success_and_stale_fallback(self):
        payload = {"result": "success", "time_last_update_utc": "now", "rates": {"USD": 1.1, "GBP": 0.9}}
        appmod._rates.update(at=0.0, retry=0.0, rates=None)
        with mock.patch("app.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(payload).encode())):
            r = appmod.get_rates()
        self.assertEqual(r["rates"]["EUR"], 1.0)
        self.assertEqual(r["rates"]["USD"], 1.1)
        self.assertFalse(r["stale"])
        appmod._rates.update(at=0.0, retry=0.0)  # expire the cache, then fail
        with mock.patch("app.urllib.request.urlopen", side_effect=OSError):
            r = appmod.get_rates()
        self.assertTrue(r["stale"])
        self.assertEqual(r["rates"]["USD"], 1.1)  # old data kept
        appmod._rates.update(retry=0.0)
        appmod._rates.update(rates=None)
        with mock.patch("app.urllib.request.urlopen", side_effect=OSError):
            self.assertIsNone(appmod.get_rates())

    def test_api_error_response_rejected(self):
        appmod._rates.update(at=0.0, retry=0.0, rates=None)
        bad = io.BytesIO(json.dumps({"result": "error", "error-type": "x"}).encode())
        with mock.patch("app.urllib.request.urlopen", return_value=bad):
            self.assertIsNone(appmod.get_rates())


class Units(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def test_routes(self):
        self.assertEqual(self.c.get("/units").status_code, 302)
        for cat in appmod.UNITS:
            self.assertEqual(self.c.get(f"/units/{cat}").status_code, 200, cat)
        self.assertEqual(self.c.get("/units/nope").status_code, 404)

    def test_length(self):
        b = body(self.c.post("/units/length", data={"v-m": "1000", "p-m": "1"}))
        self.assertIn('name="v-km" value="1"', b)
        self.assertIn('name="v-mi" value="0.6213711922"', b)

    def test_weight_and_data(self):
        self.assertIn('name="v-lb" value="2.204622622"', body(self.c.get("/units/weight")))
        b = body(self.c.post("/units/data", data={"v-GiB": "1", "p-GiB": "", "v-MB": "1", "p-MB": "1"}))
        self.assertIn('name="v-MiB" value="1024"', b)

    def test_temperature(self):
        b = body(self.c.post("/units/temperature", data={"v-c": "100", "p-c": "20"}))
        self.assertIn('name="v-f" value="212"', b)
        self.assertIn('name="v-k" value="373.15"', b)
        b = body(self.c.post("/units/temperature", data={"v-f": "32", "p-f": "68"}))
        self.assertIn('name="v-c" value="0"', b)

    def test_bad_input_and_overflow(self):
        self.assertIn("Enter a number", body(self.c.post("/units/length", data={"v-m": "x", "p-m": "1"})))
        self.assertIn("Enter a number", body(self.c.post("/units/length", data={"v-m": "1e999", "p-m": "1"})))

    def test_sitemap_lists_categories(self):
        x = self.c.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("/units/temperature", x)
        self.assertIn("/currency", x)


if __name__ == "__main__":
    unittest.main()
