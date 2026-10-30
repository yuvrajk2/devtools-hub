import html
import unittest

from app import app


class Tools(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def text(self, r):
        return html.unescape(r.get_data(as_text=True))

    def test_pages_load(self):
        for url in ["/json", "/base64", "/uuid", "/qr", "/color", "/static/style.css"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_home(self):
        self.assertEqual(self.c.get("/").status_code, 200)

    def test_404(self):
        self.assertEqual(self.c.get("/nope").status_code, 404)

    def test_json_format_minify_error(self):
        r = self.c.post("/json", data={"text": '{"a":1}', "action": "format"})
        self.assertIn('"a": 1', self.text(r))
        r = self.c.post("/json", data={"text": '{"a": 1}', "action": "minify"})
        self.assertIn('{"a":1}', self.text(r))
        r = self.c.post("/json", data={"text": '{"a":1,}'})
        self.assertIn("line 1, column 8", self.text(r))

    def test_base64_round_trip(self):
        r = self.c.post("/base64", data={"text": "héllo", "mode": "encode"})
        self.assertIn("aMOpbGxv", self.text(r))
        r = self.c.post("/base64", data={"text": "aMOpbGxv", "mode": "decode"})
        self.assertIn("héllo", self.text(r))
        r = self.c.post("/base64", data={"text": "!!!", "mode": "decode"})
        self.assertIn("isn't valid Base64", self.text(r))

    def test_uuid_count_and_flags(self):
        body = self.text(self.c.get("/uuid?count=3&nodash=on&upper=on"))
        ids = body.split("<pre>")[1].split("</pre>")[0].split()
        self.assertEqual(len(ids), 3)
        self.assertTrue(all(len(i) == 32 and i == i.upper() for i in ids))

    def test_qr(self):
        self.assertIn("<svg", self.text(self.c.get("/qr?text=hi")))
        r = self.c.get("/qr.svg?text=hi")
        self.assertEqual(r.mimetype, "image/svg+xml")

    def test_color(self):
        body = self.text(self.c.get("/color?hex=%23abc"))
        self.assertIn("rgb(170, 187, 204)", body)
        self.assertIn("Not a valid hex", self.text(self.c.get("/color?hex=zzz")))
        self.assertNotIn("<script>", self.text(self.c.get("/color?hex=<script>")))

    def test_headers(self):
        self.assertIn("script-src 'none'", self.c.get("/json").headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
