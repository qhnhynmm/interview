import os
import sys
from pathlib import Path

# Tests must not require a running Phoenix collector.
os.environ.setdefault("OTEL_ENABLED", "false")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    from app.config import get_settings

    get_settings.cache_clear()