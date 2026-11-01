"""DevTools Hub: small developer tools, rendered server-side with Flask. No JavaScript.

This file is only the entry point. Importing a module registers its routes on the shared `app`:

    core.py       the Flask app, settings and shared helpers
    registry.py   the list of tools (names, groups, descriptions)
    content.py    the About/FAQ text shown under each tool
    hooks.py      security headers, error pages, values every template can use
    analytics.py  anonymous page counter and the private /stats page
    pages.py      home page, privacy, API docs, sitemap, robots.txt
    tools/        the tools themselves (text, security, dev, convert, pdf, api)

Run:  pip install -r requirements.txt && flask --app app run --debug
"""
import os

import analytics  # noqa: F401  (imported for the routes it registers)
import hooks  # noqa: F401
import pages  # noqa: F401
from core import app
from tools import api, convert, dev, pdf, security, text  # noqa: F401

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
