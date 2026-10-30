import os
import tempfile

# Must run before `app` is imported by any test module.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
os.environ.setdefault("STATS_TOKEN", "secret")
os.environ.setdefault("SITE_URL", "https://example.com")
