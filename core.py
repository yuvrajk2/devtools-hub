"""The Flask app itself, plus the small helpers every tool uses."""
import os
from collections import defaultdict, deque
from datetime import datetime

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from registry import INFO, SIMPLE, TOOLS

app = Flask(__name__)

# Settings come from environment variables, so you can change them without editing code.
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024  # also limits uploads
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")  # e.g. https://tools.example.com
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))
STATS_TOKEN = os.environ.get("STATS_TOKEN", "")
if os.environ.get("TRUST_PROXY") == "1":  # only set this behind a reverse proxy you control
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def tool_slug():
    """Which tool the current request belongs to. The unit pages all count as "units"."""
    return "units" if request.endpoint == "units_cat" else request.endpoint


def page(slug, **ctx):
    """Render templates/<slug>.html inside the site layout."""
    return render_template(f"{slug}.html", tools=TOOLS, active=slug, **ctx)


def simple(slug, text="", **ctx):
    """Render the shared "text in, result out" template used by the url, jwt, case and hash tools."""
    ctx = {"out": None, "rows": None, "error": None, **ctx}
    return render_template("simple.html", tools=TOOLS, active=slug, meta=SIMPLE[slug],
                           info=INFO[slug], text=text, extra=request.form, **ctx)


def clamp(value, lo, hi, default):
    """Turn user input into an int between lo and hi, or use the default if it is not a number."""
    try:
        return min(hi, max(lo, int(value)))
    except (TypeError, ValueError):
        return default


# Simple in-memory rate limit: 60 requests per minute per client (per worker process).
RATE = defaultdict(deque)


def limited():
    """Return True if this client has used up its requests for the last minute."""
    now = datetime.now().timestamp()
    recent = RATE[request.remote_addr]
    while recent and now - recent[0] > 60:
        recent.popleft()
    if len(recent) >= 60:
        return True
    recent.append(now)
    return False
