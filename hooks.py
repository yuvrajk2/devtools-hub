"""Things that run around every request: security headers, usage counting, error pages
and the extra values every template can use."""
import json
import os

from flask import render_template, request

from analytics import record
from content import CONTENT
from core import MAX_UPLOAD_MB, SITE_URL, app, tool_slug
from registry import GROUPS, SLUGS, TOOLS

# No scripts are allowed at all: the site works without JavaScript, so any injected script is blocked.
CSP = ("default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; base-uri 'none'; form-action 'self'")


def remember_tool_use(resp, slug):
    """Count the visit and keep the last few tools in a cookie for the home page."""
    record(request.path)
    others = [s for s in request.cookies.get("recent", "").split(",") if s in SLUGS and s != slug]
    resp.set_cookie("recent", ",".join([slug] + others[:3]), max_age=30 * 24 * 3600,
                    samesite="Lax", httponly=True)


@app.after_request
def add_headers(resp):
    slug = tool_slug()
    if slug == "password":
        resp.headers["Cache-Control"] = "no-store"  # never cache generated passwords
    if resp.status_code == 200 and slug in SLUGS:
        remember_tool_use(resp, slug)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.errorhandler(404)
@app.errorhandler(413)
def error_page(e):
    msg = "Page not found." if e.code == 404 else f"That upload is too large ({MAX_UPLOAD_MB} MB max)."
    return render_template("error.html", tools=TOOLS, active=None, code=e.code, msg=msg), e.code


def faq_json_ld(faq):
    """FAQ structured data for search engines. "<" is escaped so it can never end the script tag."""
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    return json.dumps(data).replace("<", "\\u003c")


@app.context_processor
def template_values():
    """Values available in every template."""
    content = CONTENT.get(tool_slug())
    return {"site": SITE_URL, "content": content, "groups": GROUPS, "max_mb": MAX_UPLOAD_MB,
            "ld": faq_json_ld(content["faq"]) if content else None,
            "sponsor": (os.environ.get("SPONSOR_TEXT"), os.environ.get("SPONSOR_URL"))}
