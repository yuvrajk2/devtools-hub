"""The site pages: home page with search, privacy, API docs, sitemap and robots.txt."""


from flask import Response, render_template, request, url_for

from core import SITE_URL, app
from registry import INFO, TOOLS
from tools.convert import UNITS


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
