import html
import unittest

from app import RATE, SLUGS, app
from content import CONTENT
from tests.helpers import prime_rates


def unesc(r):
    return html.unescape(r.get_data(as_text=True))


class More(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def test_every_tool_has_content(self):
        self.assertEqual(set(CONTENT), SLUGS)
        prime_rates()
        for s in SLUGS:
            r = self.c.get(f"/{s}", follow_redirects=True)
            self.assertEqual(r.status_code, 200, s)
            self.assertIn("About this tool", r.get_data(as_text=True), s)

    def test_faq_markup(self):
        body = unesc(self.c.get("/json"))
        self.assertIn("Why is my JSON invalid?", body)
        self.assertIn("application/ld+json", body)
        self.assertNotIn("FAQPage", unesc(self.c.get("/")))

    def test_case(self):
        body = unesc(self.c.post("/case", data={"text": "hello world foo"}))
        for want in ("helloWorldFoo", "HelloWorldFoo", "hello_world_foo", "hello-world-foo", "HELLO_WORLD_FOO"):
            self.assertIn(want, body)
        self.assertIn("my_variable_name", unesc(self.c.post("/case", data={"text": "myVariableName"})))

    def test_password(self):
        r = self.c.get("/password?length=24&count=3&lower=on&digits=on")
        pws = unesc(r).split("<pre>")[1].split("</pre>")[0].split()
        self.assertEqual(len(pws), 3)
        for p in pws:
            self.assertEqual(len(p), 24)
            self.assertTrue(p.isalnum() and p == p.lower())
            self.assertTrue(any(ch.isdigit() for ch in p) and any(ch.isalpha() for ch in p))
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertIn("at least one", unesc(self.c.get("/password?length=10")))
        self.assertEqual(len(unesc(self.c.get("/password")).split("<pre>")[1].split("</pre>")[0].strip()), 20)

    def test_lorem(self):
        body = unesc(self.c.get("/lorem?paragraphs=2"))
        text = body.split("</textarea>")[0].split(">")[-1]
        self.assertTrue(text.startswith("Lorem ipsum dolor sit amet"))
        self.assertEqual(len(text.strip().split("\n\n")), 2)


if __name__ == "__main__":
    unittest.main()
