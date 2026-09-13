"""Tool state that is neither source data nor published data: ROOT/.state.json (gitignored).

The times of the last successful build and publish, shown on the Streamlit pages. Kept in the
tool's own repo because it describes this machine's actions, not the content.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from manager.settings import ROOT

STATE_FILE = ROOT / ".state.json"


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _last(key: str, path: Path | None) -> datetime | None:
    value = _read(path or STATE_FILE).get(key)
    return datetime.fromisoformat(value) if value else None


def _mark(key: str, path: Path | None, when: datetime | None) -> datetime:
    path = path or STATE_FILE  # resolved at call time so tests can point STATE_FILE elsewhere
    when = (when or datetime.now(UTC)).replace(microsecond=0)
    data = {**_read(path), key: when.isoformat()}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return when


def last_publish(path: Path | None = None) -> datetime | None:
    """Time of the last successful publish, or None if none is recorded."""
    return _last("last_publish", path)


def mark_published(path: Path | None = None, when: datetime | None = None) -> datetime:
    """Record a successful publish; returns the recorded time."""
    return _mark("last_publish", path, when)


def last_build(path: Path | None = None) -> datetime | None:
    """Time of the last successful build, or None if none is recorded."""
    return _last("last_build", path)


def mark_built(path: Path | None = None, when: datetime | None = None) -> datetime:
    """Record a successful build; returns the recorded time."""
    return _mark("last_build", path, when)
