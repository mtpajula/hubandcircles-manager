"""Environment variables and the .env file (chapter 13). No python-dotenv dependency."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    """Read KEY=value lines into the environment. Does not override already-set variables."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        os.environ.setdefault(name.strip(), value.strip().strip("'\""))


def env(name: str, default: str | None = None) -> str | None:
    """Value of an environment variable; an empty value (as in .env.example) counts as missing."""
    return os.environ.get(name) or default
