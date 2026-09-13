"""Git status and commit+push of the source data repo (DATA_DIR). Stdlib subprocess only.

The UI equivalent of `git -C $DATA_DIR add -A && git commit && git push`; the tool never
rewrites history in the data repo.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from manager import run

FALLBACK_IDENTITY = [
    "-c",
    "user.name=hubandcircles-manager",
    "-c",
    "user.email=manager@hubandcircles.invalid",
]

_HEADER = re.compile(r"^## (?:No commits yet on )?(?P<branch>[^. ]+)(?:\.\.\.\S+)?(?P<rest>.*)$")
_AHEAD = re.compile(r"ahead (\d+)")


class SourceRepoError(Exception):
    """git failed; the message is git's stderr."""


@dataclass
class RepoStatus:
    changed: int  # files with uncommitted changes (staged, unstaged or untracked)
    branch: str
    ahead: int  # commits not yet pushed to the upstream


def _git(data_dir: Path, *args: str) -> str:
    try:
        result = run.run(["git", "-C", str(data_dir), *args], check=True)
    except FileNotFoundError as e:
        raise SourceRepoError("git not found") from e
    except subprocess.CalledProcessError as e:
        raise SourceRepoError(e.stderr.strip() or f"git {args[0]} failed") from e
    return result.stdout


def status(data_dir: Path) -> RepoStatus:
    """Branch, number of changed files and commits ahead of the upstream."""
    lines = _git(data_dir, "status", "--porcelain", "--branch").splitlines()
    header = _HEADER.match(lines[0]) if lines else None
    if header is None:
        raise SourceRepoError(f"unexpected git status output: {lines[:1]}")
    ahead = _AHEAD.search(header["rest"])
    return RepoStatus(
        changed=len(lines) - 1,
        branch=header["branch"],
        ahead=int(ahead.group(1)) if ahead else 0,
    )


def _identity(data_dir: Path) -> list[str]:
    """Empty when git config has a user; otherwise the tool's own identity for the commit."""
    for key in ("user.name", "user.email"):
        try:
            if not _git(data_dir, "config", key).strip():
                return FALLBACK_IDENTITY
        except SourceRepoError:
            return FALLBACK_IDENTITY
    return []


def commit_and_push(data_dir: Path, message: str) -> str:
    """git add -A, commit, push. Returns the short commit hash; "nothing to commit" when clean."""
    _git(data_dir, "add", "-A")
    if not _git(data_dir, "status", "--porcelain").strip():
        return "nothing to commit"
    _git(
        data_dir, *_identity(data_dir), "-c", "commit.gpgsign=false", "commit", "-q", "-m", message
    )
    sha = _git(data_dir, "rev-parse", "--short", "HEAD").strip()
    _git(data_dir, "push", "-q")
    return sha
