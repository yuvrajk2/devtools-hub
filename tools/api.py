"""The small public JSON API under /api/v1."""

import json
import uuid

from flask import abort, jsonify, request

from core import app, limited
from tools.security import hashes
from tools.text import b64_decode, b64_encode


# --- JSON API ---------------------------------------------------------------
def api_call(fn):
    if limited():
        return jsonify(error="rate limit: 60 requests per minute"), 429
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if not isinstance(text, str):
        return jsonify(error='send JSON like {"text": "..."}'), 400
    try:
        return jsonify(result=fn(text, data))
    except ValueError as e:
        return jsonify(error=str(e)), 422


@app.post("/api/v1/json/<action>")
def api_json(action):
    if action not in ("format", "minify"):
        abort(404)
    mini = action == "minify"
    return api_call(lambda t, d: json.dumps(json.loads(t), ensure_ascii=False,
                                            indent=None if mini else 2,
                                            separators=(",", ":") if mini else None))


@app.post("/api/v1/base64/<action>")
def api_base64(action):
    if action not in ("encode", "decode"):
        abort(404)
    return api_call(lambda t, d: b64_encode(t, bool(d.get("urlsafe"))) if action == "encode" else b64_decode(t))


@app.post("/api/v1/hash")
def api_hash():
    return api_call(lambda t, d: hashes(t))


@app.get("/api/v1/uuid")
def api_uuid():
    if limited():
        return jsonify(error="rate limit: 60 requests per minute"), 429
    try:
        n = min(500, max(1, int(request.args.get("count", 1))))
    except ValueError:
        n = 1
    return jsonify(result=[str(uuid.uuid4()) for _ in range(n)])
