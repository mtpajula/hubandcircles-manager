"""Tool state that is neither source data nor published data: ROOT/.state.json (gitignored).

Currently only the time of the last publish, shown in the Streamlit sidebar. Kept in the tool's
own repo because it describes this machine's actions, not the content.
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


def last_publish(path: Path = STATE_FILE) -> datetime | None:
    """Time of the last successful publish, or None if none is recorded."""
    value = _read(path).get("last_publish")
    return datetime.fromisoformat(value) if value else None


def mark_published(path: Path = STATE_FILE, when: datetime | None = None) -> datetime:
    """Record a successful publish; returns the recorded time."""
    when = (when or datetime.now(UTC)).replace(microsecond=0)
    data = {**_read(path), "last_publish": when.isoformat()}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return when
