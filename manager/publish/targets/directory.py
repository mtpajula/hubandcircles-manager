"""Target `directory`: copy the bundle to a local directory. Also the git pre-step for GitHub Pages."""

import shutil
from pathlib import Path

from manager.models import Target
from manager.publish.bundle import Bundle
from manager.publish.errors import PublishError


def publish(bundle: Bundle, target: Target) -> str:
    """Empty the target directory (except .git) and copy the bundle into it."""
    if not target.path:
        raise PublishError(f"target {target.id}: path missing")
    target_dir = Path(target.path).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    for p in target_dir.iterdir():
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    shutil.copytree(bundle.directory, target_dir, dirs_exist_ok=True)
    return f"{target.id}: copied to {target_dir}"
