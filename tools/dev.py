"""Developer tools: QR codes, the CIDR calculator, the sandboxed regex tester and the cron explainer."""

import io
import ipaddress
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from flask import Response, request

from core import app, page

try:
    import segno  # pure-Python QR encoder, no dependencies of its own
except ImportError:  # the QR page degrades instead of crashing the app
    segno = None


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


# --- CIDR / subnet calculator ---------------------------------------------------
@app.get("/cidr", endpoint="cidr")
def cidr_tool():
    raw = request.args.get("net", "192.168.1.0/24").strip()
    check = request.args.get("ip", "").strip()
    rows = error = None
    try:
        iface = ipaddress.ip_interface(raw)
        n = iface.network
        rows = [("Address", str(iface.ip)), ("Network", str(n)), ("Netmask", str(n.netmask)),
                ("Wildcard", str(n.hostmask)), ("Total addresses", f"{n.num_addresses:,}")]
        if n.version == 4:
            wide = n.prefixlen <= 30  # /31 and /32 have no network/broadcast addresses to exclude
            rows += [("Broadcast", str(n.broadcast_address)),
                     ("First host", str(n.network_address + 1 if wide else n.network_address)),
                     ("Last host", str(n.broadcast_address - 1 if wide else n.broadcast_address)),
                     ("Usable hosts", f"{n.num_addresses - 2 if wide else n.num_addresses:,}")]
        rows.append(("Type", "Public (global)" if iface.ip.is_global else "Private or reserved"))
        if check:
            rows.append((f"Contains {check}?", "Yes" if ipaddress.ip_address(check) in n else "No"))
    except ValueError as e:
        rows, error = None, str(e)
    return page("cidr", net=raw, check=check, rows=rows, error=error)


# --- Regex tester (runs in a separate process with a hard timeout) ----------------
REGEX_RUNNER = r'''
import json, re, sys
d = json.load(sys.stdin)
flags = 0
for f in d["flags"]:
    flags |= {"i": re.I, "m": re.M, "s": re.S, "x": re.X}[f]
try:
    rx = re.compile(d["pattern"], flags)
except re.error as e:
    print(json.dumps({"error": "Invalid pattern: " + str(e)}))
    sys.exit()
out = []
for m in rx.finditer(d["text"]):
    out.append({"span": [m.start(), m.end()], "text": m.group(0), "groups": list(m.groups())})
    if len(out) >= 200:
        break
print(json.dumps({"matches": out}))
'''


def run_regex(pattern, text, flags):
    """User patterns can backtrack forever, so never run them inside the web worker."""
    payload = json.dumps({"pattern": pattern, "text": text, "flags": flags})
    try:
        p = subprocess.run([sys.executable, "-I", "-c", REGEX_RUNNER], input=payload,
                           capture_output=True, text=True, timeout=2)
        return json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "Timed out after 2 seconds. The pattern may be backtracking catastrophically."}
    except ValueError:
        return {"error": "The pattern could not be evaluated."}


@app.route("/regex", methods=["GET", "POST"], endpoint="regex")
def regex_tool():
    f = request.form
    pattern, text = f.get("pattern", ""), f.get("text", "")
    flags = [x for x in "imsx" if x in f.getlist("flags")]
    matches = segments = error = None
    if request.method == "POST" and pattern:
        if len(pattern) > 500 or len(text) > 20000:
            error = "Pattern is limited to 500 characters and text to 20,000."
        else:
            res = run_regex(pattern, text, flags)
            error, matches = res.get("error"), res.get("matches")
            if matches is not None:
                segments, pos = [], 0
                for m in matches:
                    a, b = m["span"]
                    if b == a or a < pos:
                        continue
                    if a > pos:
                        segments.append((False, text[pos:a]))
                    segments.append((True, text[a:b]))
                    pos = b
                if pos < len(text):
                    segments.append((False, text[pos:]))
    return page("regex", pattern=pattern, text=text, flags=flags, matches=matches, segments=segments, error=error)


# --- Cron explainer (UTC) ---------------------------------------------------------
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
DOWS = {d: i for i, d in enumerate("sun mon tue wed thu fri sat".split())}
CRON_FIELDS = [("minute", 0, 59, {}), ("hour", 0, 23, {}), ("day of month", 1, 31, {}),
               ("month", 1, 12, MONTHS), ("day of week", 0, 7, DOWS)]
CRON_ALIASES = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
                "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *"}


def cron_field(text, name, lo, hi, names):
    def val(x):
        v = names[x] if x in names else int(x)
        if not lo <= v <= hi:
            raise ValueError(f"{name}: {x} is out of range {lo}-{hi}")
        return v
    out = set()
    try:
        for part in text.lower().split(","):
            base, _, step_s = part.partition("/")
            step = int(step_s) if step_s else 1
            if step < 1:
                raise ValueError(f"{name}: step must be at least 1")
            if base in ("*", "?"):
                a, b = lo, hi
            elif "-" in base:
                a, b = (val(x) for x in base.split("-", 1))
            else:
                a = val(base)
                b = hi if step_s else a
            if a > b:
                raise ValueError(f"{name}: range {base} is backwards")
            out.update(range(a, b + 1, step))
    except ValueError as e:
        raise ValueError(str(e) if str(e).startswith(name) else f"{name}: can't read '{text}'") from None
    return {v % 7 for v in out} if name == "day of week" else out


def parse_cron(expr):
    parts = CRON_ALIASES.get(expr.lower(), expr).split()
    if len(parts) != 5:
        raise ValueError("A cron expression has 5 fields: minute hour day-of-month month day-of-week")
    return [cron_field(p, *spec) for p, spec in zip(parts, CRON_FIELDS)], parts


def next_runs(sets, parts, start, count=5):
    mins, hours, doms, months, dows = (sorted(s) for s in sets)
    # Classic cron: when BOTH day fields are restricted, a day matches if EITHER one matches.
    both = not parts[2].startswith(("*", "?")) and not parts[4].startswith(("*", "?"))
    out, day = [], start.replace(hour=0, minute=0)
    for _ in range(366 * 5):
        dom_ok, dow_ok = day.day in doms, (day.weekday() + 1) % 7 in dows
        if day.month in months and (dom_ok or dow_ok if both else dom_ok and dow_ok):
            for h in hours:
                for m in mins:
                    t = day.replace(hour=h, minute=m)
                    if t >= start:
                        out.append(t)
                        if len(out) == count:
                            return out
        day += timedelta(days=1)
    return out


@app.get("/cron", endpoint="cron")
def cron_tool():
    expr = request.args.get("expr", "*/15 9-17 * * 1-5").strip()
    rows = runs = error = None
    try:
        sets, parts = parse_cron(expr)
        rows = []
        for i, (name, _lo, _hi, _names) in enumerate(CRON_FIELDS):
            vals = sorted(sets[i])
            shown = ", ".join(map(str, vals[:12])) + (" ..." if len(vals) > 12 else "")
            rows.append((name, parts[i], f"{len(vals)} value(s): {shown}"))
        start = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
        runs = [t.strftime("%a %Y-%m-%d %H:%M UTC") for t in next_runs(sets, parts, start)]
    except ValueError as e:
        rows, error = None, str(e)
    return page("cron", expr=expr, rows=rows, runs=runs, error=error)
