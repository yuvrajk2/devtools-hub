"""Security-minded tools: hashes and HMAC, the JWT decoder and verifier, UUIDs and passwords."""

import base64
import hashlib
import hmac
import json
import secrets
import string
import uuid
from datetime import datetime, timezone

from flask import request

from core import app, clamp, page, simple


# --- Hashes -----------------------------------------------------------------
ALGOS = ("md5", "sha1", "sha256", "sha512")


def hashes(text):
    return {a: hashlib.new(a, text.encode("utf-8")).hexdigest() for a in ALGOS}


@app.route("/hash", methods=["GET", "POST"], endpoint="hash")
def hash_tool():
    text = request.form.get("text", "")
    key = request.form.get("key", "")
    rows = None
    if request.method == "POST" and text:
        label = lambda a: a.upper().replace("SHA", "SHA-")
        if key:  # HMAC instead of a plain hash
            rows = [("HMAC-" + label(a), hmac.new(key.encode(), text.encode(), a).hexdigest()) for a in ALGOS]
        else:
            rows = [(label(a), h) for a, h in hashes(text).items()]
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
            if request.form.get("secret"):
                rows.append(("Signature", jwt_verify(header, head, payload, _signature, request.form["secret"])))
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


# --- JWT signature check (used by /jwt when a secret is given) ------------------
HS = {"HS256": "sha256", "HS384": "sha384", "HS512": "sha512"}


def jwt_verify(header, head, payload, sig, secret):
    alg = header.get("alg") if isinstance(header, dict) else None
    if alg not in HS:
        return f"Cannot verify alg {alg!r} here (only HS256, HS384, HS512)"
    expected = hmac.new(secret.encode(), f"{head}.{payload}".encode(), HS[alg]).digest()
    try:
        given = base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
    except ValueError:
        return "Invalid (malformed signature)"
    return f"Valid ({alg})" if hmac.compare_digest(expected, given) else f"Invalid ({alg}): wrong secret or tampered token"


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


# --- Password ---------------------------------------------------------------
CLASSES = {"lower": string.ascii_lowercase, "upper": string.ascii_uppercase,
           "digits": string.digits, "symbols": "!@#$%^&*()-_=+[]{};:,.?"}


def make_password(length, pools):
    chars = [secrets.choice(p) for p in pools]  # at least one from each chosen type
    allowed = "".join(pools)
    chars += [secrets.choice(allowed) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


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
