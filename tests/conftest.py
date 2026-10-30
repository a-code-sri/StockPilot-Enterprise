import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Deterministic settings for tests; never pick up a developer's real database.
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg2://unused:unused@127.0.0.1:1/unused"
)
os.environ["DIRECT_DATABASE_URL"] = ""
os.environ.setdefault("AI_ENABLED", "true")
