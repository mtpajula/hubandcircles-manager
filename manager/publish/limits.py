"""Target limits (chapter 12.8). The numbers live in limits.json, not in code (chapter 12.2)."""

import json
from pathlib import Path

from manager.models import Target
from manager.publish.bundle import Bundle
from manager.validate.finding import Finding

LIMITS_PATH = Path(__file__).with_name("limits.json")
LABELS = {"max_files": "files", "max_total_bytes": "total size", "max_file_bytes": "largest file"}


def read_limits() -> dict[str, dict[str, int]]:
    return json.loads(LIMITS_PATH.read_text(encoding="utf-8"))


def _fmt(limit: str, value: int) -> str:
    return str(value) if limit == "max_files" else f"{value / 2**20:.1f} MiB"


def check_limits(bundle: Bundle, target: Target) -> list[Finding]:
    """Exceeding a limit is an error naming the limit, the bundle's value and the largest file."""
    name, size = bundle.largest
    values = {
        "max_files": bundle.file_count,
        "max_total_bytes": bundle.total_bytes,
        "max_file_bytes": size,
    }
    return [
        Finding(
            "error",
            f"{target.id} ({target.type}): {LABELS[limit]} {_fmt(limit, values[limit])} exceeds limit "
            f"{_fmt(limit, cap)}; largest file {name} ({_fmt('max_file_bytes', size)})",
        )
        for limit, cap in read_limits().get(target.type, {}).items()
        if values[limit] > cap
    ]
