"""Converters: color, timestamps, units and currency.

Units and currency share a no-JavaScript "everything stays in sync" form, explained in the Converters section."""

import colorsys
import json
import math
import os
import re
import threading
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime

from flask import abort, redirect, render_template, request, url_for

from core import app, page
from registry import INFO, TOOLS


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
