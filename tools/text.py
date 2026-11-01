"""Text tools: JSON, Base64, URL encoding, text diff, lorem ipsum and case conversion.

Each tool is a function that reads the form, does the work in plain Python, and renders a template."""

import base64
import difflib
import json
import random
import re
import urllib.parse

from flask import request

from core import app, clamp, page, simple


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


# --- URL --------------------------------------------------------------------
@app.route("/url", methods=["GET", "POST"], endpoint="url")
def url_tool():
    text = request.form.get("text", "")
    out = None
    if request.method == "POST" and text:
        out = urllib.parse.quote(text, safe="") if request.form.get("mode") == "encode" else urllib.parse.unquote(text)
    return simple("url", text, out=out)


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
