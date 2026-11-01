"""Anonymous usage counter (views per day and path, no IP, no user agent) and the private /stats page."""

import hmac
import os
import sqlite3
from contextlib import closing

from flask import abort, render_template, request

from core import DATA_DIR, STATS_TOKEN, app
from registry import TOOLS


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
