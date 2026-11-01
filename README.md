# DevTools Hub

Free developer tools built with Flask. Server-rendered, no JavaScript.

**Tools (28):** 10 PDF tools (merge, split, extract, delete, rotate, compress, protect, unlock, images to PDF, info), currency converter (live rates), unit converters (9 categories), CIDR calculator, sandboxed regex tester, cron explainer, JWT decoder with HS256/384/512 verification, HMAC, JSON, Base64, URL encode/decode, JWT decoder, hashes, UUID, QR code,
color + gradient, timestamp, text diff, password generator, lorem ipsum, case converter.
Each has its own URL (for example `/json`, `/jwt`, `/password`) plus an About and FAQ section
(see `content.py`) with FAQPage structured data for search. The home page has search and a "recent tools" list. A small JSON API lives at `/api`.

## Run

    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    flask --app app run --debug

Open http://127.0.0.1:5000. Run the tests with `python -m unittest`.

## Project layout

    app.py            entry point: imports everything so the routes get registered
    core.py           the Flask app, settings (environment variables) and shared helpers
    registry.py       the list of tools: names, nav groups, one-line descriptions
    content.py        the About + FAQ text shown under each tool
    hooks.py          security headers, error pages, values every template can use
    analytics.py      anonymous page counter and the private /stats page
    pages.py          home page, privacy, API docs, sitemap, robots.txt
    tools/
      text.py         JSON, Base64, URL, text diff, lorem ipsum, case converter
      security.py     hashes + HMAC, JWT decode/verify, UUID, password generator
      dev.py          QR code, CIDR calculator, regex tester, cron explainer
      convert.py      color, timestamps, units, currency
      pdf.py          the 10 PDF tools
      api.py          the /api/v1 JSON API
    templates/        one HTML file per page, all extending base.html
    static/style.css  the only stylesheet
    tests/            python -m unittest

## How a tool works

Every tool is one function in `tools/`. It reads the form (`request.form` or `request.args`),
does the work in plain Python, and renders a template:

    @app.route("/hash", methods=["GET", "POST"], endpoint="hash")
    def hash_tool():
        text = request.form.get("text", "")
        ...
        return simple("hash", text, rows=rows)

## Adding a tool

1. Add it to `GROUPS` and `INFO` in `registry.py`.
2. Write its route in the matching file in `tools/` and a template in `templates/`.
3. Add its About + FAQ to `content.py`. A test fails if you forget.
4. Add a test in `tests/` and run `python -m unittest`.

## Configuration (environment variables)

| Variable | Purpose |
| --- | --- |
| `EXCHANGERATE_API_KEY` | Optional. Uses the keyed ExchangeRate-API endpoint (hourly or faster on paid plans) instead of the free daily one |
| `RATES_TTL` | Seconds to cache exchange rates. Default 21600 (6 h) without a key, 3600 with one |
| `MAX_UPLOAD_MB` | Largest allowed upload, default 25 |
| `SITE_URL` | Public base URL, used for canonical links, sitemap and robots (e.g. `https://tools.example.com`) |
| `STATS_TOKEN` | Enables the private `/stats?token=...` page. Unset = page disabled |
| `DATA_DIR` | Where the anonymous hit counter (SQLite) is stored. Default `./data` |
| `SPONSOR_TEXT`, `SPONSOR_URL` | Shows a labelled sponsor link in the sidebar |
| `TRUST_PROXY` | Set to `1` only behind a reverse proxy you control, so client IPs (rate limiting) are read correctly |

## Deploy

Docker:

    docker build -t devtools-hub .
    docker run -p 8000:8000 -v devtools-data:/data \
      -e SITE_URL=https://tools.example.com -e STATS_TOKEN=change-me devtools-hub

Without Docker: `gunicorn -w 2 -b 0.0.0.0:8000 app:app`. A `Procfile` is included
for Render, Railway, Fly and Heroku-style hosts. Put it behind HTTPS (Caddy, nginx
or your host's proxy) and submit `/sitemap.xml` to Google Search Console.

## Monetization

Ad networks need JavaScript, which the Content-Security-Policy blocks on purpose.
Options that work as is: a sponsor link (`SPONSOR_TEXT` and `SPONSOR_URL`), affiliate
links in the templates, or a paid API tier built on `/api/v1`.

## Privacy

Input is processed in memory and never stored. The app keeps an anonymous per-day
page counter (no IP, no user agent) and one `recent` cookie. See `/privacy`.

## Exchange rates

The free endpoint (open.er-api.com) updates once a day and requires the attribution link
shown on the page. For hourly or 5-minute rates, buy a plan at exchangerate-api.com and set
`EXCHANGERATE_API_KEY`. If the API is down, the last known rates are shown with a notice.

## Regex sandbox

The regex tester runs each pattern in a separate Python process with a 2 second timeout, so
catastrophic backtracking cannot hang a web worker. Pattern and text sizes are capped. For a
public deployment, also run the container with memory and CPU limits.

## PDF tools

Built on `pypdf` and `Pillow`. Files are processed in memory and never written to disk. A PDF is
parsed inside the web worker, so on a public deployment keep the per-container memory/CPU limits and
the upload limit (`MAX_UPLOAD_MB`) in place. Compression re-encodes JPEG images and removes duplicate
objects; it cannot shrink scanned documents that are already tightly encoded.
