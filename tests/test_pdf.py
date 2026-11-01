import html
import io
import unittest
import zipfile

from PIL import Image
from pypdf import PdfReader, PdfWriter

from app import app
from core import RATE
from tools.pdf import PdfError, parse_pages


def make_pdf(n, sizes=True):
    """n pages; page i is (100 + 10*i) points wide so order can be checked."""
    w = PdfWriter()
    for i in range(n):
        w.add_blank_page(width=100 + 10 * i, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def widths(data):
    return [round(float(p.mediabox.width)) for p in PdfReader(io.BytesIO(data)).pages]


def upload(data, name="doc.pdf", ctype="application/pdf"):
    return (io.BytesIO(data), name, ctype)


class Pdf(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        RATE.clear()

    def post(self, path, files, **form):
        data = dict(form)
        data["files"] = files if isinstance(files, list) else [files]
        return self.c.post(path, data=data, content_type="multipart/form-data")

    def test_parse_pages(self):
        self.assertEqual(parse_pages("1-3,5", 10), [0, 1, 2, 4])
        self.assertEqual(parse_pages("8-", 10), [7, 8, 9])
        self.assertEqual(parse_pages("-2", 10), [0, 1])
        self.assertEqual(parse_pages("last", 10), [9])
        self.assertEqual(parse_pages("3-1", 10), [2, 1, 0])
        for bad in ("", "0", "11", "x", "1-99"):
            with self.assertRaises(PdfError, msg=bad):
                parse_pages(bad, 10)

    def test_merge(self):
        r = self.post("/pdf/merge", [upload(make_pdf(3), "a.pdf"), upload(make_pdf(2), "b.pdf")])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.mimetype, "application/pdf")
        self.assertIn("attachment", r.headers["Content-Disposition"])
        self.assertEqual(widths(r.data), [100, 110, 120, 100, 110])
        self.assertIn("at least two", self.post("/pdf/merge", upload(make_pdf(1))).get_data(as_text=True))

    def test_bad_files(self):
        r = self.post("/pdf/merge", [upload(b"not a pdf", "a.pdf"), upload(make_pdf(1), "b.pdf")])
        self.assertEqual(r.status_code, 400)
        self.assertIn("not a PDF", r.get_data(as_text=True))
        broken = b"%PDF-1.4\n" + b"garbage" * 50
        self.assertIn("Could not read", self.post("/pdf/extract", upload(broken), spec="1").get_data(as_text=True))
        self.assertIn("Choose a file", self.c.post("/pdf/merge", data={}).get_data(as_text=True))

    def test_split_modes(self):
        pdf = make_pdf(5)
        z = zipfile.ZipFile(io.BytesIO(self.post("/pdf/split", upload(pdf), mode="ranges", spec="1-2,5").data))
        names = sorted(z.namelist())
        self.assertEqual(names, ["doc-part1.pdf", "doc-part2.pdf"])
        self.assertEqual(widths(z.read(names[0])), [100, 110])
        self.assertEqual(widths(z.read(names[1])), [140])
        z = zipfile.ZipFile(io.BytesIO(self.post("/pdf/split", upload(pdf), mode="each").data))
        self.assertEqual(len(z.namelist()), 5)
        z = zipfile.ZipFile(io.BytesIO(self.post("/pdf/split", upload(pdf), mode="every", n="2").data))
        self.assertEqual([len(PdfReader(io.BytesIO(z.read(n))).pages) for n in sorted(z.namelist())], [2, 2, 1])

    def test_extract_and_delete(self):
        pdf = make_pdf(5)
        self.assertEqual(widths(self.post("/pdf/extract", upload(pdf), spec="3,1,last").data), [120, 100, 140])
        self.assertIn("outside", self.post("/pdf/extract", upload(pdf), spec="9").get_data(as_text=True))
        self.assertEqual(widths(self.post("/pdf/delete", upload(pdf), spec="2,4-5").data), [100, 120])
        self.assertIn("every page", self.post("/pdf/delete", upload(pdf), spec="1-5").get_data(as_text=True))

    def test_rotate(self):
        pdf = make_pdf(3)
        out = PdfReader(io.BytesIO(self.post("/pdf/rotate", upload(pdf), spec="2", angle="90").data))
        self.assertEqual([p.rotation for p in out.pages], [0, 90, 0])
        out = PdfReader(io.BytesIO(self.post("/pdf/rotate", upload(pdf), spec="", angle="180").data))
        self.assertEqual([p.rotation for p in out.pages], [180, 180, 180])
        self.assertIn("Choose 90", self.post("/pdf/rotate", upload(pdf), angle="45").get_data(as_text=True))

    def test_protect_unlock_roundtrip(self):
        locked = self.post("/pdf/protect", upload(make_pdf(3)), password="hunter22").data
        r = PdfReader(io.BytesIO(locked))
        self.assertTrue(r.is_encrypted)
        self.assertEqual(r.decrypt("hunter22") > 0, True)
        self.assertIn("password-protected", self.post("/pdf/extract", upload(locked), spec="1").get_data(as_text=True))
        self.assertIn("at least 4", self.post("/pdf/protect", upload(make_pdf(1)), password="ab").get_data(as_text=True))
        bad = self.post("/pdf/unlock", upload(locked), password="wrong")
        self.assertEqual(bad.status_code, 400)
        out = self.post("/pdf/unlock", upload(locked), password="hunter22").data
        r = PdfReader(io.BytesIO(out))
        self.assertFalse(r.is_encrypted)
        self.assertEqual(len(r.pages), 3)
        self.assertIn("isn't password-protected", html.unescape(self.post("/pdf/unlock", upload(make_pdf(1)), password="x").get_data(as_text=True)))

    def image(self, fmt="PNG", mode="RGB", size=(300, 200)):
        buf = io.BytesIO()
        Image.new(mode, size, (200, 30, 30, 128) if mode == "RGBA" else (200, 30, 30)).save(buf, fmt)
        return buf.getvalue()

    def test_images_to_pdf(self):
        files = [upload(self.image("PNG", "RGBA"), "a.png", "image/png"), upload(self.image("JPEG"), "b.jpg", "image/jpeg")]
        out = self.post("/images-to-pdf", files, page="fit").data
        self.assertEqual(len(PdfReader(io.BytesIO(out)).pages), 2)
        fresh = upload(self.image("PNG", "RGBA"), "a.png", "image/png")
        a4 = PdfReader(io.BytesIO(self.post("/images-to-pdf", fresh, page="a4").data)).pages[0]
        self.assertAlmostEqual(float(a4.mediabox.width), 595, delta=3)
        self.assertAlmostEqual(float(a4.mediabox.height), 842, delta=3)
        self.assertIn("Could not read", self.post("/images-to-pdf", upload(b"nope", "x.png")).get_data(as_text=True))

    def test_compress_shrinks_image_pdf(self):
        import os
        noise = Image.frombytes("RGB", (900, 900), os.urandom(900 * 900 * 3))
        buf = io.BytesIO()
        noise.save(buf, "PDF", resolution=100.0)
        big = buf.getvalue()
        out = self.post("/pdf/compress", upload(big), level="strong").data
        self.assertLess(len(out), len(big))
        self.assertEqual(len(PdfReader(io.BytesIO(out)).pages), 1)
        # text-only PDFs can't shrink: the original comes back
        small = make_pdf(2)
        self.assertLessEqual(len(self.post("/pdf/compress", upload(small), level="lossless").data), len(small))

    def test_info(self):
        r = self.post("/pdf/info", upload(make_pdf(4), "report.pdf"))
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("report.pdf", body)
        self.assertIn("<span class=\"v\">4</span>", body)
        self.assertIn("No", body)

    def test_upload_limit_and_pages(self):
        old = app.config["MAX_CONTENT_LENGTH"]
        app.config["MAX_CONTENT_LENGTH"] = 500
        try:
            r = self.post("/pdf/merge", [upload(make_pdf(40), "a.pdf"), upload(make_pdf(40), "b.pdf")])
            self.assertEqual(r.status_code, 413)
            self.assertIn("too large", r.get_data(as_text=True))
        finally:
            app.config["MAX_CONTENT_LENGTH"] = old

    def test_pages_render_and_nav_groups(self):
        for path in ("/pdf/merge", "/pdf/split", "/pdf/extract", "/pdf/delete", "/pdf/rotate", "/pdf/compress",
                     "/pdf/protect", "/pdf/unlock", "/images-to-pdf", "/pdf/info"):
            r = self.c.get(path)
            self.assertEqual(r.status_code, 200, path)
            self.assertIn('enctype="multipart/form-data"', r.get_data(as_text=True))
        self.assertIn("<h3>PDF</h3>", self.c.get("/pdf/merge").get_data(as_text=True))
        self.assertIn("/pdf/merge", self.c.get("/sitemap.xml").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
