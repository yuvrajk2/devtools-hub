"""PDF tools. Everything is processed in memory: uploads are read, changed and streamed back, never saved."""

import io
import re
import warnings
import zipfile
from pathlib import Path

from flask import render_template, request, send_file
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from werkzeug.utils import secure_filename

from core import app, clamp, limited
from registry import INFO, TOOLS


# --- PDF tools ------------------------------------------------------------------
# Everything is processed in memory: uploads are read, transformed and streamed back.
# Nothing is written to disk.
MAX_PDF_FILES, MAX_PDF_PAGES = 20, 1000
Image.MAX_IMAGE_PIXELS = 25_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)  # treat huge images as errors


class PdfError(Exception):
    """A problem with the user's input, safe to show on the page."""


def stem_of(f):
    return secure_filename(Path(f.filename or "").stem) or "document"


def load_pdf(f, password=""):
    data = f.read()
    if b"%PDF-" not in data[:1024]:
        raise PdfError(f"{f.filename or 'That file'} is not a PDF.")
    try:
        r = PdfReader(io.BytesIO(data))
        if r.is_encrypted and not r.decrypt(password or ""):
            raise PdfError(f"{f.filename} is password-protected. Remove the password with the Unlock tool first, or check the password.")
        if len(r.pages) > MAX_PDF_PAGES:
            raise PdfError(f"{f.filename} has more than {MAX_PDF_PAGES} pages.")
    except PdfError:
        raise
    except Exception:  # pypdf raises many types on damaged files
        raise PdfError(f"Could not read {f.filename or 'that file'}. It may be damaged.") from None
    return r


def write_pdf(w):
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def pages_pdf(r, idxs):
    w = PdfWriter()
    for i in idxs:
        w.add_page(r.pages[i])
    return write_pdf(w)


def parse_pages(spec, n):
    """'1-3,5,8-' or 'last' -> zero-based page indexes, in the order written. '5-3' runs backwards."""
    parts = [p for p in re.split(r"[,\s]+", (spec or "").strip().lower()) if p]
    if not parts:
        raise PdfError("Enter the pages, for example 1-3,5,8-")
    out = []
    num = lambda x: n if x == "last" else int(x)
    for part in parts:
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = (num(a) if a else 1), (num(b) if b else n)
            else:
                a = b = num(part)
        except ValueError:
            raise PdfError(f"Can't read '{part}'. Use numbers like 3, 2-5, 8- or last.") from None
        if not (1 <= a <= n and 1 <= b <= n):
            raise PdfError(f"'{part}' is outside this PDF's {n} pages.")
        out.extend(range(a - 1, b) if a <= b else range(a - 1, b - 2, -1))
        if len(out) > 5000:
            raise PdfError("That page list is too long.")
    return out


def h_merge(files, form):
    if len(files) < 2:
        raise PdfError("Choose at least two PDF files to merge.")
    w = PdfWriter()
    for f in files:
        w.append(load_pdf(f))
        if len(w.pages) > MAX_PDF_PAGES:
            raise PdfError(f"The merged file would exceed {MAX_PDF_PAGES} pages.")
    return write_pdf(w), "merged.pdf"


def h_split(files, form):
    r = load_pdf(files[0])
    n, mode = len(r.pages), form.get("mode", "ranges")
    if mode == "each":
        groups = [[i] for i in range(n)]
    elif mode == "every":
        k = clamp(form.get("n"), 1, n, 2)
        groups = [list(range(i, min(i + k, n))) for i in range(0, n, k)]
    else:
        parts = [p for p in re.split(r"[,\s]+", (form.get("spec") or "").strip()) if p]
        groups = [parse_pages(p, n) for p in parts] or parse_pages("", n)
    if len(groups) > 200:
        raise PdfError("That would create more than 200 files.")
    stem, buf = stem_of(files[0]), io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, g in enumerate(groups, 1):
            z.writestr(f"{stem}-part{i}.pdf", pages_pdf(r, g))
    return buf.getvalue(), f"{stem}-split.zip"


def h_extract(files, form):
    r = load_pdf(files[0])
    return pages_pdf(r, parse_pages(form.get("spec"), len(r.pages))), f"{stem_of(files[0])}-extracted.pdf"


def h_delete(files, form):
    r = load_pdf(files[0])
    n = len(r.pages)
    drop = set(parse_pages(form.get("spec"), n))
    keep = [i for i in range(n) if i not in drop]
    if not keep:
        raise PdfError("That would delete every page.")
    return pages_pdf(r, keep), f"{stem_of(files[0])}-edited.pdf"


def h_rotate(files, form):
    r = load_pdf(files[0])
    n = len(r.pages)
    angle = {"90": 90, "180": 180, "270": 270}.get(form.get("angle", "90"))
    if not angle:
        raise PdfError("Choose 90, 180 or 270 degrees.")
    idxs = parse_pages(form.get("spec"), n) if (form.get("spec") or "").strip() else range(n)
    w = PdfWriter(clone_from=r)
    for i in set(idxs):
        w.pages[i].rotate(angle)
    return write_pdf(w), f"{stem_of(files[0])}-rotated.pdf"


LEVELS = {"lossless": None, "medium": 70, "strong": 40}


def h_compress(files, form):
    raw = files[0].read()
    files[0].stream.seek(0)
    quality = LEVELS.get(form.get("level", "medium"), 70)
    w = PdfWriter(clone_from=load_pdf(files[0]))
    for page in w.pages:
        page.compress_content_streams()
        if quality:
            try:
                for img in page.images:
                    img.replace(img.image, quality=quality)  # re-encode JPEG-backed images
            except Exception:
                pass  # leave images we can't recompress as they are
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    out = write_pdf(w)
    return (out if len(out) < len(raw) else raw), f"{stem_of(files[0])}-compressed.pdf"


def h_protect(files, form):
    pw = form.get("password", "")
    if len(pw) < 4:
        raise PdfError("Use a password of at least 4 characters.")
    w = PdfWriter(clone_from=load_pdf(files[0]))
    w.encrypt(user_password=pw, algorithm="AES-256")
    return write_pdf(w), f"{stem_of(files[0])}-protected.pdf"


def h_unlock(files, form):
    r = load_pdf(files[0], form.get("password", ""))
    if not r.is_encrypted:
        raise PdfError("That PDF isn't password-protected.")
    return write_pdf(PdfWriter(clone_from=r)), f"{stem_of(files[0])}-unlocked.pdf"


def h_img2pdf(files, form):
    if len(files) > 50:
        raise PdfError("Up to 50 images at a time.")
    a4, pages = form.get("page") == "a4", []
    for f in files:
        try:
            im = ImageOps.exif_transpose(Image.open(f.stream))
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                flat = Image.new("RGB", im.size, "white")
                flat.paste(im, mask=im.split()[-1])
                im = flat
            else:
                im = im.convert("RGB")
            if a4:  # A4 at 150 dpi, image centered with a margin
                canvas = Image.new("RGB", (1240, 1754), "white")
                im.thumbnail((1160, 1674))
                canvas.paste(im, ((1240 - im.width) // 2, (1754 - im.height) // 2))
                im = canvas
        except Exception:
            raise PdfError(f"Could not read {f.filename} as an image (JPG, PNG, WebP, GIF, BMP or TIFF).") from None
        pages.append(im)
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:], resolution=150.0)
    return buf.getvalue(), "images.pdf"


def h_info(files, form):
    f = files[0]
    f.stream.seek(0, 2)
    size = f.stream.tell()
    f.stream.seek(0)
    r = load_pdf(f)
    box = r.pages[0].mediabox
    mm = lambda pt: round(float(pt) * 25.4 / 72)
    rows = [("File", f.filename), ("Size", f"{size / 1024:,.1f} KB"), ("Pages", str(len(r.pages))),
            ("Page 1 size", f"{mm(box.width)} x {mm(box.height)} mm"), ("PDF version", str(r.pdf_header).lstrip("%")),
            ("Password-protected", "Yes" if r.is_encrypted else "No")]
    meta = r.metadata
    for label, attr in (("Title", "title"), ("Author", "author"), ("Subject", "subject"),
                        ("Creator", "creator"), ("Producer", "producer")):
        v = getattr(meta, attr, None) if meta else None
        if v:
            rows.append((label, str(v)))
    if meta and getattr(meta, "creation_date", None):
        rows.append(("Created", meta.creation_date.isoformat()))
    return rows


def spec_field(label, placeholder):
    """A text box for page numbers like 1-3,5,8-."""
    return {"name": "spec", "label": label, "kind": "text", "placeholder": placeholder}


PDF_TOOLS = {
    "pdf_merge": dict(path="/pdf/merge", title="Merge PDF", button="Merge PDFs", handler=h_merge, multiple=True,
                      label="PDF files (choose 2 or more; they are joined in the order selected)", fields=[]),
    "pdf_split": dict(path="/pdf/split", title="Split PDF", button="Split", handler=h_split, label="PDF file", fields=[
        {"name": "mode", "label": "Split by", "kind": "radio", "default": "ranges", "options": [
            ("ranges", "Ranges: each comma-separated part becomes its own PDF"),
            ("each", "Every page as its own PDF"), ("every", "Every N pages")]},
        spec_field("Ranges (for the first option)", "1-3,4-6,7-"),
        {"name": "n", "label": "N (for the third option)", "kind": "number", "default": "2"}]),
    "pdf_extract": dict(path="/pdf/extract", title="Extract PDF Pages", button="Extract", handler=h_extract,
                        label="PDF file", fields=[spec_field("Pages to keep, in the order you want them", "3,1,5-7")]),
    "pdf_delete": dict(path="/pdf/delete", title="Delete PDF Pages", button="Delete pages", handler=h_delete,
                       label="PDF file", fields=[spec_field("Pages to delete", "2,4-6")]),
    "pdf_rotate": dict(path="/pdf/rotate", title="Rotate PDF", button="Rotate", handler=h_rotate, label="PDF file", fields=[
        spec_field("Pages (leave empty for all)", "all pages"),
        {"name": "angle", "label": "Rotate clockwise", "kind": "select", "default": "90",
         "options": [("90", "90 degrees"), ("180", "180 degrees"), ("270", "270 degrees")]}]),
    "pdf_compress": dict(path="/pdf/compress", title="Compress PDF", button="Compress", handler=h_compress,
                         label="PDF file", fields=[
        {"name": "level", "label": "Level", "kind": "radio", "default": "medium", "options": [
            ("lossless", "Lossless (no quality change)"), ("medium", "Medium (JPEG images at quality 70)"),
            ("strong", "Strong (JPEG images at quality 40)")]}]),
    "pdf_protect": dict(path="/pdf/protect", title="Protect PDF", button="Encrypt", handler=h_protect, label="PDF file",
                        fields=[{"name": "password", "label": "Password", "kind": "password"}]),
    "pdf_unlock": dict(path="/pdf/unlock", title="Unlock PDF", button="Remove password", handler=h_unlock,
                       label="Password-protected PDF", fields=[{"name": "password", "label": "Password", "kind": "password"}]),
    "img2pdf": dict(path="/images-to-pdf", title="Images to PDF", button="Create PDF", handler=h_img2pdf, multiple=True,
                    accept="image/*", label="Images (JPG, PNG, WebP, GIF, BMP, TIFF; one page each, in the order selected)",
                    fields=[{"name": "page", "label": "Page size", "kind": "select", "default": "fit",
                             "options": [("fit", "Same size as each image"), ("a4", "A4 with margins")]}]),
    "pdf_info": dict(path="/pdf/info", title="PDF Info", button="Show info", handler=h_info, label="PDF file", fields=[]),
}


def make_pdf_view(slug):
    cfg = PDF_TOOLS[slug]

    def view():
        ctx = dict(cfg=cfg, info=INFO[slug], error=None, rows=None, vals=request.form)
        if request.method == "POST":
            files = [f for f in request.files.getlist("files") if f and f.filename]
            try:
                if limited():
                    raise PdfError("Too many requests. Please wait a minute.")
                if not files:
                    raise PdfError("Choose a file first.")
                if len(files) > MAX_PDF_FILES or (not cfg.get("multiple") and len(files) > 1):
                    raise PdfError("Too many files." if cfg.get("multiple") else "Choose one file.")
                result = cfg["handler"](files, request.form)
            except PdfError as e:
                return render_template("pdf.html", tools=TOOLS, active=slug, **{**ctx, "error": str(e)}), 400
            except Exception:
                app.logger.exception("PDF tool failed: %s", slug)
                return render_template("pdf.html", tools=TOOLS, active=slug,
                                       **{**ctx, "error": "Something went wrong while processing that file."}), 500
            if isinstance(result, list):
                ctx["rows"] = result
            else:
                data, name = result
                return send_file(io.BytesIO(data), as_attachment=True, download_name=name)
        return render_template("pdf.html", tools=TOOLS, active=slug, **ctx)

    view.__name__ = slug
    return view


for _slug, _cfg in PDF_TOOLS.items():
    app.add_url_rule(_cfg["path"], endpoint=_slug, view_func=make_pdf_view(_slug), methods=["GET", "POST"])
