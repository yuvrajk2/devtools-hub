"""DevTools Hub: small developer tools, rendered server-side with Flask.

No JavaScript. Everything is a plain HTML form handled in Python.
Run:  pip install -r requirements.txt && flask --app app run
"""
import base64
import colorsys
import difflib
import hashlib
import hmac
import io
import json
import math
import os
import random
import re
import secrets
import sqlite3
import string
import threading
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict, deque
from contextlib import closing
from datetime import datetime, timezone
from email.utils import format_datetime

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from content import CONTENT

try:
    import segno  # pure-Python QR encoder, no dependencies of its own
except ImportError:  # the QR page degrades instead of crashing the app
    segno = None

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000  # 1 MB per request

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")  # e.g. https://devtools.example.com
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
STATS_TOKEN = os.environ.get("STATS_TOKEN", "")
if os.environ.get("TRUST_PROXY") == "1":  # only set this behind a reverse proxy you control
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

TOOLS = [
    ("json", "JSON"),
    ("base64", "Base64"),
    ("url", "URL Encode"),
    ("jwt", "JWT Decoder"),
    ("hash", "Hashes"),
    ("uuid", "UUID"),
    ("qr", "QR Code"),
    ("color", "Color"),
    ("currency", "Currency"),
    ("units", "Units"),
    ("time", "Timestamp"),
    ("diff", "Text Diff"),
    ("password", "Password"),
    ("lorem", "Lorem Ipsum"),
    ("case", "Case Convert"),
]
SLUGS = {s for s, _ in TOOLS}
INFO = {
    "currency": "Convert between 150+ currencies. Edit any amount and every other currency updates.",
    "units": "Length, weight, temperature, volume, area, speed, time, data size and pressure. Edit any field and all units update.",
    "json": "Format, minify and validate JSON. Errors show the line and column.",
    "base64": "Encode and decode Base64, UTF-8 safe, with a URL-safe option.",
    "url": "Percent-encode or decode text for URLs and query strings.",
    "jwt": "Decode a JSON Web Token's header and payload. The signature is not verified.",
    "hash": "MD5, SHA-1, SHA-256 and SHA-512 hashes of any text.",
    "uuid": "Generate random version 4 UUIDs in bulk.",
    "qr": "Turn text or a URL into a scannable QR code and download it as SVG.",
    "color": "Convert HEX, RGB and HSL and build a CSS linear gradient.",
    "time": "Convert Unix timestamps and ISO dates, seconds or milliseconds.",
    "diff": "Compare two blocks of text and see what changed, line by line.",
    "password": "Generate strong random passwords with the length and characters you choose.",
    "lorem": "Generate lorem ipsum placeholder paragraphs for layouts and mockups.",
    "case": "Convert text to camelCase, snake_case, kebab-case, Title Case and more.",
}
# slug -> (page title, textarea placeholder, [(button value, label, primary)])
SIMPLE = {
    "url": ("URL Encoder / Decoder", "Text or URL", [("encode", "Encode", 1), ("decode", "Decode", 0)]),
    "jwt": ("JWT Decoder", "eyJhbGciOi...", [("decode", "Decode", 1)]),
    "case": ("Case Converter", "Type or paste text", [("convert", "Convert", 1)]),
    "hash": ("Hash Generator", "Text to hash", [("hash", "Generate hashes", 1)]),
}


def tool_slug():
    return "units" if request.endpoint == "units_cat" else request.endpoint


@app.after_request
def security_headers(resp):
    slug = tool_slug()
    if slug == "password":
        resp.headers["Cache-Control"] = "no-store"
    if resp.status_code == 200 and slug in SLUGS:
        record(request.path)
        seen = [x for x in request.cookies.get("recent", "").split(",") if x in SLUGS and x != slug]
        resp.set_cookie("recent", ",".join([slug] + seen[:3]), max_age=60 * 60 * 24 * 30,
                        samesite="Lax", httponly=True)
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; base-uri 'none'; form-action 'self'"
    )
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.errorhandler(404)
@app.errorhandler(413)
def error_page(e):
    msg = "Page not found." if e.code == 404 else "That input is too large (1 MB max)."
    return render_template("error.html", tools=TOOLS, active=None, code=e.code, msg=msg), e.code


def page(slug, **ctx):
    return render_template(f"{slug}.html", tools=TOOLS, active=slug, **ctx)


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(os.path.join(DATA_DIR, "stats.db"))
    c.execute("CREATE TABLE IF NOT EXISTS hits (day TEXT, path TEXT, n INTEGER, PRIMARY KEY (day, path))")
    return c


def record(path):
    """Anonymous usage counter: one row per day and path. No IP, no user agent."""
    try:
        with closing(db()) as c, c:
            c.execute("INSERT INTO hits VALUES (date('now'), ?, 1) "
                      "ON CONFLICT(day, path) DO UPDATE SET n = n + 1", (path,))
    except (sqlite3.Error, OSError):
        pass


@app.context_processor
def inject():
    c = CONTENT.get(tool_slug())
    ld = None
    if c:
        ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in c["faq"]]}).replace("<", "\\u003c")
    return {"site": SITE_URL, "content": c, "ld": ld,
            "sponsor": (os.environ.get("SPONSOR_TEXT"), os.environ.get("SPONSOR_URL"))}


@app.get("/")
def index():
    q = request.args.get("q", "").strip().lower()
    cards = [(s, n, INFO[s]) for s, n in TOOLS if not q or q in n.lower() or q in INFO[s].lower()]
    names = dict(TOOLS)
    recent = [(s, names[s]) for s in request.cookies.get("recent", "").split(",") if s in names]
    return render_template("index.html", tools=TOOLS, active="index", cards=cards, recent=recent, q=q)


@app.get("/privacy", endpoint="privacy")
def privacy():
    return render_template("privacy.html", tools=TOOLS, active=None)


@app.get("/api", endpoint="api_docs")
def api_docs():
    return render_template("api.html", tools=TOOLS, active=None)


def base_url():
    return SITE_URL or request.url_root.rstrip("/")


@app.get("/sitemap.xml")
def sitemap():
    paths = [url_for("index")] + [url_for(s) for s, _ in TOOLS if s != "units"] + [url_for("units_cat", cat=c) for c in UNITS] + [url_for("api_docs"), url_for("privacy")]
    body = "".join(f"  <url><loc>{base_url()}{p}</loc></url>\n" for p in paths)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n')
    return Response(xml, mimetype="application/xml")


@app.get("/robots.txt")
def robots():
    return Response(f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /stats\n"
                    f"Sitemap: {base_url()}/sitemap.xml\n", mimetype="text/plain")


def simple(slug, text="", **ctx):
    ctx = {"out": None, "rows": None, "error": None, **ctx}
    return render_template("simple.html", tools=TOOLS, active=slug, meta=SIMPLE[slug],
                           info=INFO[slug], text=text, **ctx)


# --- JSON -------------------------------------------------------------------
INDENTS = {"2": 2, "4": 4, "tab": "\t"}


@app.route("/json", methods=["GET", "POST"], endpoint="json")
def json_tool():
    text = request.form.get("text", "")
    indent = request.form.get("indent", "2")
    action = request.form.get("action", "format")
    out = error = None
    if request.method == "POST" and text.strip():
        try:
            data = json.loads(text)
            if action == "minify":
                out = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            else:
                out = json.dumps(data, indent=INDENTS.get(indent, 2), ensure_ascii=False)
        except json.JSONDecodeError as e:
            error = f"{e.msg} (line {e.lineno}, column {e.colno})"
    return page("json", text=text, indent=indent, out=out, error=error)


# --- Base64 -----------------------------------------------------------------
def b64_encode(text, urlsafe):
    raw = text.encode("utf-8")
    if urlsafe:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return base64.b64encode(raw).decode()


def b64_decode(text):
    t = text.strip().replace("-", "+").replace("_", "/")
    t += "=" * (-len(t) % 4)
    return base64.b64decode(t, validate=True).decode("utf-8")


@app.route("/base64", methods=["GET", "POST"], endpoint="base64")
def base64_tool():
    text = request.form.get("text", "")
    urlsafe = "urlsafe" in request.form
    mode = request.form.get("mode")
    out = error = None
    if request.method == "POST" and text:
        try:
            out = b64_encode(text, urlsafe) if mode == "encode" else b64_decode(text)
        except ValueError:  # bad Base64 (binascii.Error) or not UTF-8 text
            error = "That isn't valid Base64, or it doesn't decode to UTF-8 text."
    return page("base64", text=text, urlsafe=urlsafe, mode=mode, out=out, error=error)


# --- UUID -------------------------------------------------------------------
@app.get("/uuid", endpoint="uuid")
def uuid_tool():
    try:
        count = min(500, max(1, int(request.args.get("count", 5))))
    except ValueError:
        count = 5
    upper = "upper" in request.args
    nodash = "nodash" in request.args
    ids = []
    for _ in range(count):
        u = str(uuid.uuid4())
        u = u.replace("-", "") if nodash else u
        ids.append(u.upper() if upper else u)
    return page("uuid", count=count, upper=upper, nodash=nodash, ids="\n".join(ids))


# --- QR ---------------------------------------------------------------------
def make_qr(text, level):
    level = level if level in ("L", "M", "Q", "H") else "M"
    return segno.make(text, error=level, micro=False)


@app.get("/qr", endpoint="qr")
def qr_tool():
    text = request.args.get("text", "https://example.com")
    level = request.args.get("level", "M")
    svg = error = None
    if segno is None:
        error = "The segno package isn't installed (pip install segno)."
    elif text:
        try:
            svg = make_qr(text, level).svg_inline(scale=6, border=2)
        except ValueError:
            error = "That text is too long for this error-correction level."
    return page("qr", text=text, level=level, svg=svg, error=error)


@app.get("/qr.svg")
def qr_download():
    text = request.args.get("text", "")
    if segno is None or not text:
        return Response("Missing text", status=400)
    try:
        buf = io.BytesIO()
        make_qr(text, request.args.get("level", "M")).save(buf, kind="svg", scale=6, border=2)
    except ValueError:
        return Response("Text too long", status=400)
    return Response(buf.getvalue(), mimetype="image/svg+xml",
                    headers={"Content-Disposition": "attachment; filename=qr.svg"})


# --- Color ------------------------------------------------------------------
def norm_hex(value, default):
    v = (value or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", v):
        v = "".join(c * 2 for c in v)
    return "#" + v.lower() if re.fullmatch(r"[0-9a-fA-F]{6}", v) else default


def conversions(h):
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return [
        ("HEX", h),
        ("RGB", f"rgb({r}, {g}, {b})"),
        ("HSL", f"hsl({round(hue * 360)}, {round(sat * 100)}%, {round(light * 100)}%)"),
    ]


@app.get("/color", endpoint="color")
def color_tool():
    a = request.args
    hex_ = norm_hex(a.get("hex"), "#c0392b")
    bad = bool(a.get("hex")) and norm_hex(a.get("hex"), None) is None
    c1 = norm_hex(a.get("c1"), "#1f4e79")
    c2 = norm_hex(a.get("c2"), "#c0392b")
    try:
        angle = int(a.get("angle", 135)) % 361
    except ValueError:
        angle = 135
    css = f"background: linear-gradient({angle}deg, {c1}, {c2});"
    return page("color", bad=bad, hex=hex_, rows=conversions(hex_), c1=c1, c2=c2, angle=angle, css=css)


# --- URL --------------------------------------------------------------------
@app.route("/url", methods=["GET", "POST"], endpoint="url")
def url_tool():
    text = request.form.get("text", "")
    out = None
    if request.method == "POST" and text:
        out = urllib.parse.quote(text, safe="") if request.form.get("mode") == "encode" else urllib.parse.unquote(text)
    return simple("url", text, out=out)


# --- Hashes -----------------------------------------------------------------
ALGOS = ("md5", "sha1", "sha256", "sha512")


def hashes(text):
    return {a: hashlib.new(a, text.encode("utf-8")).hexdigest() for a in ALGOS}


@app.route("/hash", methods=["GET", "POST"], endpoint="hash")
def hash_tool():
    text = request.form.get("text", "")
    rows = None
    if request.method == "POST" and text:
        rows = [(a.upper().replace("SHA", "SHA-"), h) for a, h in hashes(text).items()]
    return simple("hash", text, rows=rows)


# --- JWT --------------------------------------------------------------------
def jwt_part(part):
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


@app.route("/jwt", methods=["GET", "POST"], endpoint="jwt")
def jwt_tool():
    text = request.form.get("text", "").strip()
    rows = error = None
    if request.method == "POST" and text:
        try:
            head, payload, _signature = text.split(".")
            header, body = jwt_part(head), jwt_part(payload)
            rows = [("Header", json.dumps(header, indent=2)), ("Payload", json.dumps(body, indent=2))]
            if isinstance(body, dict):
                for k in ("iat", "nbf", "exp"):
                    if isinstance(body.get(k), (int, float)):
                        rows.append((k, iso(body[k])))
                if isinstance(body.get("exp"), (int, float)):
                    expired = body["exp"] < datetime.now(timezone.utc).timestamp()
                    rows.append(("Status", "Expired" if expired else "Not expired"))
        except (ValueError, OverflowError, OSError):
            rows, error = None, "That doesn't look like a valid JWT (expected header.payload.signature)."
    return simple("jwt", text, rows=rows, error=error)


# --- Timestamp --------------------------------------------------------------
def parse_time(v):
    try:
        n = float(v)
        return datetime.fromtimestamp(n / 1000 if abs(n) > 1e11 else n, timezone.utc)
    except ValueError:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@app.get("/time", endpoint="time")
def time_tool():
    raw = request.args.get("value", "").strip()
    d = error = None
    try:
        d = parse_time(raw) if raw else datetime.now(timezone.utc)
    except (ValueError, OverflowError, OSError):
        error = "Use a Unix timestamp (seconds or milliseconds) or an ISO date like 2026-10-29T12:00:00Z."
    rows = None if d is None else [
        ("ISO 8601 (UTC)", d.isoformat()), ("Unix seconds", int(d.timestamp())),
        ("Unix milliseconds", int(d.timestamp() * 1000)), ("RFC 2822", format_datetime(d)),
    ]
    return page("time", value=raw, rows=rows, error=error, showing_now=not raw)


# --- Diff -------------------------------------------------------------------
@app.route("/diff", methods=["GET", "POST"], endpoint="diff")
def diff_tool():
    a, b = request.form.get("a", ""), request.form.get("b", "")
    lines = None
    if request.method == "POST" and (a or b):
        lines = []
        for line in difflib.unified_diff(a.splitlines(), b.splitlines(), "original", "changed", lineterm="", n=3):
            if line.startswith(("+++", "---", "@@")):
                kind = "hdr"
            else:
                kind = {"+": "add", "-": "del"}.get(line[:1], "ctx")
            lines.append((kind, line))
        lines = lines or [("ctx", "No differences.")]
    return page("diff", a=a, b=b, lines=lines)


# --- Password ---------------------------------------------------------------
CLASSES = {"lower": string.ascii_lowercase, "upper": string.ascii_uppercase,
           "digits": string.digits, "symbols": "!@#$%^&*()-_=+[]{};:,.?"}


def make_password(length, pools):
    chars = [secrets.choice(p) for p in pools]  # at least one from each chosen type
    allowed = "".join(pools)
    chars += [secrets.choice(allowed) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def clamp(value, lo, hi, default):
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default


@app.get("/password", endpoint="password")
def password_tool():
    a = request.args
    on = {k: (k in a if a else True) for k in CLASSES}
    noambig = "noambig" in a
    length, count = clamp(a.get("length"), 8, 128, 20), clamp(a.get("count"), 1, 20, 1)
    pools = [p for k, p in CLASSES.items() if on[k]]
    if noambig:
        pools = ["".join(c for c in p if c not in "Il1O0") for p in pools]
    out = error = None
    if pools:
        out = "\n".join(make_password(length, pools) for _ in range(count))
    else:
        error = "Pick at least one character type."
    return page("password", on=on, noambig=noambig, length=length, count=count, out=out, error=error)


# --- Lorem ipsum ------------------------------------------------------------
WORDS = ("lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore "
         "et dolore magna aliqua enim ad minim veniam quis nostrud exercitation ullamco laboris nisi aliquip "
         "ex ea commodo consequat duis aute irure in reprehenderit voluptate velit esse cillum fugiat nulla "
         "pariatur excepteur sint occaecat cupidatat non proident sunt culpa qui officia deserunt mollit anim "
         "id est laborum").split()


def lorem(paragraphs):
    out = []
    for i in range(paragraphs):
        sentences = []
        for j in range(random.randint(4, 7)):
            words = random.choices(WORDS, k=random.randint(6, 14))
            if i == 0 and j == 0:
                words[:5] = ["lorem", "ipsum", "dolor", "sit", "amet"]
            sentences.append(" ".join(words).capitalize() + ".")
        out.append(" ".join(sentences))
    return "\n\n".join(out)


@app.get("/lorem", endpoint="lorem")
def lorem_tool():
    n = clamp(request.args.get("paragraphs"), 1, 10, 3)
    return page("lorem", paragraphs=n, out=lorem(n))


# --- Case converter ---------------------------------------------------------
def words_of(text):
    return re.findall(r"[^\W_]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text))


@app.route("/case", methods=["GET", "POST"], endpoint="case")
def case_tool():
    text = request.form.get("text", "")
    rows = None
    w = words_of(text) if request.method == "POST" else []
    if w:
        cap = [x.capitalize() for x in w]
        rows = [("UPPER CASE", text.upper()), ("lower case", text.lower()), ("Title Case", " ".join(cap)),
                ("camelCase", w[0].lower() + "".join(cap[1:])), ("PascalCase", "".join(cap)),
                ("snake_case", "_".join(x.lower() for x in w)), ("kebab-case", "-".join(x.lower() for x in w)),
                ("CONSTANT_CASE", "_".join(x.upper() for x in w))]
    return simple("case", text, rows=rows)


# --- Converters (currency + units) --------------------------------------------
# No JavaScript needed for "everything stays in sync": every field is an input that
# carries a hidden copy of its previous value. On submit, the field whose text changed
# is the one you edited; all other fields are recomputed from it.
def parse_number(raw):
    raw = raw.strip().replace(" ", "")
    if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+(\.\d+)?", raw):  # 1,234.5 style thousands
        raw = raw.replace(",", "")
    v = float(raw)  # ValueError for anything else
    if not math.isfinite(v):
        raise ValueError(raw)
    return v


def synced(keys, form, default):
    if request.method != "POST":
        return default
    edited = next((k for k in keys if form.get(f"v-{k}", "").strip() != form.get(f"p-{k}", "")), None)
    src = edited or form.get("s")
    if src not in keys:
        return default
    try:
        return src, parse_number(form.get(f"v-{src}", ""))
    except ValueError:
        return src, None


def fmt_num(x):
    return f"{x:.10g}" if math.isfinite(x) else "overflow"


def fmt_money(x):
    if not math.isfinite(x):
        return "overflow"
    return f"{x:,.2f}" if abs(x) >= 1 else f"{x:.6g}"


def converter_view(active, title, info, defs, src, val, compute, fmt, status=200, **ctx):
    """defs: [(key, label)]. compute(src, val) -> {key: number}."""
    error = None
    if val is None:
        error = "Enter a number, for example 1234.5"
        values = {k: request.form.get(f"p-{k}", "") for k, _ in defs}
    else:
        out = compute(src, val)
        values = {k: fmt(out[k]) for k, _ in defs}
    rows = [(k, label, values[k]) for k, label in defs]
    return render_template("converter.html", tools=TOOLS, active=active, title=title, info=info,
                           rows=rows, src=src, error=error, **ctx), status


# Exchange rates: ExchangeRate-API open endpoint (no key, updated daily, attribution required).
# With EXCHANGERATE_API_KEY set, the keyed endpoint is used (hourly or faster on paid plans).
RATES_KEY = os.environ.get("EXCHANGERATE_API_KEY", "")
RATES_URL = (f"https://v6.exchangerate-api.com/v6/{RATES_KEY}/latest/EUR" if RATES_KEY
             else "https://open.er-api.com/v6/latest/EUR")
RATES_TTL = int(os.environ.get("RATES_TTL", "3600" if RATES_KEY else "21600"))
_rates = {"at": 0.0, "retry": 0.0, "updated": "", "rates": None, "stale": False}
_rates_lock = threading.Lock()


def get_rates():
    now = datetime.now().timestamp()
    with _rates_lock:
        if (_rates["rates"] and now - _rates["at"] < RATES_TTL) or now < _rates["retry"]:
            return _rates if _rates["rates"] else None
        try:
            req = urllib.request.Request(RATES_URL, headers={"User-Agent": "devtools-hub"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
            if data.get("result") != "success":
                raise ValueError("api error")
            table = data.get("rates") or data["conversion_rates"]
            rates = {k: float(v) for k, v in table.items() if float(v) > 0}
            rates.setdefault("EUR", 1.0)
            _rates.update(at=now, retry=0.0, rates=rates, stale=False,
                          updated=data.get("time_last_update_utc", ""))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            _rates.update(retry=now + 60, stale=bool(_rates["rates"]))  # keep old data, don't hammer the API
        return _rates if _rates["rates"] else None


POPULAR = ["USD", "EUR", "GBP", "JPY", "CNY", "INR", "AUD", "CAD", "CHF", "SGD", "AED", "KRW", "MXN", "BRL", "ZAR", "SEK"]
CURRENCY_NAMES = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "JPY": "Japanese Yen", "CNY": "Chinese Yuan",
    "INR": "Indian Rupee", "AUD": "Australian Dollar", "CAD": "Canadian Dollar", "CHF": "Swiss Franc",
    "SGD": "Singapore Dollar", "AED": "UAE Dirham", "KRW": "South Korean Won", "MXN": "Mexican Peso",
    "BRL": "Brazilian Real", "ZAR": "South African Rand", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
    "DKK": "Danish Krone", "NZD": "New Zealand Dollar", "HKD": "Hong Kong Dollar", "PLN": "Polish Zloty",
    "TRY": "Turkish Lira", "THB": "Thai Baht", "IDR": "Indonesian Rupiah", "MYR": "Malaysian Ringgit",
    "PHP": "Philippine Peso", "SAR": "Saudi Riyal", "NPR": "Nepalese Rupee", "PKR": "Pakistani Rupee",
    "BDT": "Bangladeshi Taka", "LKR": "Sri Lankan Rupee", "EGP": "Egyptian Pound", "NGN": "Nigerian Naira",
}


@app.route("/currency", methods=["GET", "POST"], endpoint="currency")
def currency_tool():
    r = get_rates()
    ctx = dict(kind="currency", show_also=True, also="", updated="", stale=False, tabs=None)
    if not r:
        return render_template("converter.html", tools=TOOLS, active="currency", title="Currency Converter",
                               info=INFO["currency"], rows=[], src="USD", **{**ctx, "show_also": False},
                               error="Exchange rates are unavailable right now. Please try again in a minute."), 503
    rates = r["rates"]
    also = request.form.get("also", "")
    extra = []
    for c in re.findall(r"[A-Za-z]{3}", also)[:30]:
        c = c.upper()
        if c in rates and c not in POPULAR and c not in extra:
            extra.append(c)
    codes = [c for c in POPULAR if c in rates] + extra
    src, val = synced(codes, request.form, ("USD" if "USD" in codes else codes[0], 1.0))
    defs = [(c, f"{c} {CURRENCY_NAMES.get(c, '')}".strip()) for c in codes]
    ctx.update(also=also, updated=r["updated"], stale=r["stale"])
    return converter_view("currency", "Currency Converter", INFO["currency"], defs, src, val,
                          lambda s, v: {k: v / rates[s] * rates[k] for k in codes}, fmt_money, **ctx)


UNITS = {
    "length": ("Length", ("m", 1), [("km", "Kilometer (km)", 1000), ("m", "Meter (m)", 1), ("cm", "Centimeter (cm)", 0.01), ("mm", "Millimeter (mm)", 0.001), ("mi", "Mile (mi)", 1609.344), ("yd", "Yard (yd)", 0.9144), ("ft", "Foot (ft)", 0.3048), ("in", "Inch (in)", 0.0254), ("nmi", "Nautical mile (nmi)", 1852)]),
    "weight": ("Weight", ("kg", 1), [("t", "Tonne (t)", 1000), ("kg", "Kilogram (kg)", 1), ("g", "Gram (g)", 0.001), ("mg", "Milligram (mg)", 1e-6), ("lb", "Pound (lb)", 0.45359237), ("oz", "Ounce (oz)", 0.028349523125), ("st", "Stone (st)", 6.35029318)]),
    "temperature": ("Temperature", ("c", 20), [("c", "Celsius (°C)", None), ("f", "Fahrenheit (°F)", None), ("k", "Kelvin (K)", None)]),
    "volume": ("Volume", ("L", 1), [("L", "Liter (L)", 1), ("mL", "Milliliter (mL)", 0.001), ("m3", "Cubic meter (m³)", 1000), ("gal", "US gallon", 3.785411784), ("qt", "US quart", 0.946352946), ("pt", "US pint", 0.473176473), ("cup", "US cup", 0.2365882365), ("floz", "US fluid ounce", 0.0295735295625), ("tbsp", "US tablespoon", 0.01478676478125), ("tsp", "US teaspoon", 0.00492892159375), ("igal", "Imperial gallon", 4.54609)]),
    "area": ("Area", ("m2", 1), [("km2", "Square kilometer (km²)", 1e6), ("ha", "Hectare (ha)", 1e4), ("m2", "Square meter (m²)", 1), ("cm2", "Square centimeter (cm²)", 1e-4), ("mi2", "Square mile (mi²)", 2589988.110336), ("ac", "Acre (ac)", 4046.8564224), ("yd2", "Square yard (yd²)", 0.83612736), ("ft2", "Square foot (ft²)", 0.09290304), ("in2", "Square inch (in²)", 0.00064516)]),
    "speed": ("Speed", ("kmh", 100), [("ms", "Meters per second (m/s)", 1), ("kmh", "Kilometers per hour (km/h)", 1 / 3.6), ("mph", "Miles per hour (mph)", 0.44704), ("kn", "Knot (kn)", 1852 / 3600), ("fts", "Feet per second (ft/s)", 0.3048)]),
    "time": ("Time", ("h", 1), [("ms", "Millisecond (ms)", 0.001), ("s", "Second (s)", 1), ("min", "Minute (min)", 60), ("h", "Hour (h)", 3600), ("d", "Day (d)", 86400), ("wk", "Week (wk)", 604800), ("yr", "Year (365.25 days)", 31557600)]),
    "data": ("Data size", ("MB", 1), [("bit", "Bit", 0.125), ("B", "Byte (B)", 1), ("KB", "Kilobyte (KB, 1000 B)", 1e3), ("MB", "Megabyte (MB)", 1e6), ("GB", "Gigabyte (GB)", 1e9), ("TB", "Terabyte (TB)", 1e12), ("KiB", "Kibibyte (KiB, 1024 B)", 1024), ("MiB", "Mebibyte (MiB)", 1024 ** 2), ("GiB", "Gibibyte (GiB)", 1024 ** 3), ("TiB", "Tebibyte (TiB)", 1024 ** 4)]),
    "pressure": ("Pressure", ("bar", 1), [("Pa", "Pascal (Pa)", 1), ("kPa", "Kilopascal (kPa)", 1e3), ("bar", "Bar", 1e5), ("psi", "PSI", 6894.757293168), ("atm", "Atmosphere (atm)", 101325), ("mmHg", "mmHg (Torr)", 133.322387415)]),
}
TEMP = {"c": (lambda v: v, lambda b: b),
        "f": (lambda v: (v - 32) * 5 / 9, lambda b: b * 9 / 5 + 32),
        "k": (lambda v: v - 273.15, lambda b: b + 273.15)}


def convert_units(cat, defs, src, val):
    if cat == "temperature":
        base = TEMP[src][0](val)
        return {k: TEMP[k][1](base) for k, _, _ in defs}
    factor = {k: f for k, _, f in defs}
    base = val * factor[src]
    return {k: base / factor[k] for k in factor}


@app.get("/units", endpoint="units")
def units_home():
    return redirect(url_for("units_cat", cat="length"))


@app.route("/units/<cat>", methods=["GET", "POST"], endpoint="units_cat")
def units_page(cat):
    if cat not in UNITS:
        abort(404)
    title, default, defs = UNITS[cat]
    src, val = synced([k for k, _, _ in defs], request.form, default)
    return converter_view("units", f"{title} Converter",
                          f"Convert {title.lower()} units. Edit any field and every other unit updates.",
                          [(k, label) for k, label, _ in defs], src, val,
                          lambda s, v: convert_units(cat, defs, s, v), fmt_num,
                          kind="units", show_also=False, tabs=[(c, UNITS[c][0]) for c in UNITS], cat=cat)


# --- JSON API ---------------------------------------------------------------
RATE = defaultdict(deque)


def limited():
    """60 requests per minute per client, in memory (per worker)."""
    now = datetime.now().timestamp()
    q = RATE[request.remote_addr]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= 60:
        return True
    q.append(now)
    return False


def api_call(fn):
    if limited():
        return jsonify(error="rate limit: 60 requests per minute"), 429
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if not isinstance(text, str):
        return jsonify(error='send JSON like {"text": "..."}'), 400
    try:
        return jsonify(result=fn(text, data))
    except ValueError as e:
        return jsonify(error=str(e)), 422


@app.post("/api/v1/json/<action>")
def api_json(action):
    if action not in ("format", "minify"):
        abort(404)
    mini = action == "minify"
    return api_call(lambda t, d: json.dumps(json.loads(t), ensure_ascii=False,
                                            indent=None if mini else 2,
                                            separators=(",", ":") if mini else None))


@app.post("/api/v1/base64/<action>")
def api_base64(action):
    if action not in ("encode", "decode"):
        abort(404)
    return api_call(lambda t, d: b64_encode(t, bool(d.get("urlsafe"))) if action == "encode" else b64_decode(t))


@app.post("/api/v1/hash")
def api_hash():
    return api_call(lambda t, d: hashes(t))


@app.get("/api/v1/uuid")
def api_uuid():
    if limited():
        return jsonify(error="rate limit: 60 requests per minute"), 429
    try:
        n = min(500, max(1, int(request.args.get("count", 1))))
    except ValueError:
        n = 1
    return jsonify(result=[str(uuid.uuid4()) for _ in range(n)])


# --- Private usage stats (set STATS_TOKEN to enable) --------------------------
@app.get("/stats", endpoint="stats")
def stats():
    if not STATS_TOKEN or not hmac.compare_digest(request.args.get("token", ""), STATS_TOKEN):
        abort(404)
    with closing(db()) as c:
        rows = c.execute("SELECT path, SUM(n) FROM hits GROUP BY path ORDER BY 2 DESC").fetchall()
        daily = c.execute("SELECT day, SUM(n) FROM hits GROUP BY day ORDER BY day DESC LIMIT 14").fetchall()
    return render_template("stats.html", tools=TOOLS, active=None, rows=rows, daily=daily)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
