"""Target `github-pages`: force-push the bundle as a single commit to the gh-pages branch.

The bundle is regenerable, so the branch keeps no history: every publish replaces the previous
commit, which keeps the site repo small. Authentication is either GITHUB_TOKEN in .env or git's
own credential helper (the maintainer's machine). The token is never printed.
"""

import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from manager.models import Target
from manager.publish.bundle import Bundle
from manager.publish.errors import PublishError
from manager.settings import env

BRANCH = "gh-pages"
IDENTITY = [
    "-c",
    "user.name=hubandcircles-manager",
    "-c",
    "user.email=manager@hubandcircles.invalid",
    "-c",
    "commit.gpgsign=false",
]


def remote_url(target: Target) -> str:
    """HTTPS remote for the site repo; with GITHUB_TOKEN set, the token is embedded for git."""
    token = env("GITHUB_TOKEN")
    auth = f"x-access-token:{token}@" if token else ""
    return f"https://{auth}github.com/{target.repo}.git"


def _git(target: Target, cwd: Path, *args: str) -> None:
    token = env("GITHUB_TOKEN")
    try:
        subprocess.run(["git", *args], check=True, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError as e:
        raise PublishError("git not found") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip()
        if token:
            stderr = stderr.replace(token, "***")
        raise PublishError(f"target {target.id}: git {args[0]} failed: {stderr}") from e


def publish(bundle: Bundle, target: Target) -> str:
    """Commit the bundle (plus .nojekyll) into a fresh repo and force-push it to gh-pages."""
    if not target.repo:
        raise PublishError(f"target {target.id}: repo missing (owner/name)")
    stamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        _git(target, work, "init", "-q", "-b", BRANCH)
        shutil.copytree(bundle.directory, work, dirs_exist_ok=True)
        # GitHub Pages must not run Jekyll: it would drop _headers and other _-prefixed files.
        (work / ".nojekyll").write_text("")
        _git(target, work, "add", "-A")
        _git(target, work, *IDENTITY, "commit", "-q", "-m", f"Publish {stamp}")
        _git(target, work, "push", "-q", "--force", remote_url(target), BRANCH)
    return f"{target.id}: pushed to {target.repo} {BRANCH}"
