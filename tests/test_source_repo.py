"""Source data repo: status and commit+push against a local bare remote standing in for GitHub."""

import shutil
import subprocess

import pytest

from manager import source_repo
from manager.source_repo import SourceRepoError, commit_and_push, status

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A clone of a bare remote with one commit, so push has an upstream."""
    bare = tmp_path / "data.git"
    _git("init", "-q", "--bare", "-b", "main", str(bare))
    work = tmp_path / "data"
    _git("clone", "-q", str(bare), str(work))
    (work / "project.json").write_text("{}\n")
    _git("-C", str(work), "add", "-A")
    _git("-C", str(work), *source_repo.FALLBACK_IDENTITY, "commit", "-q", "-m", "init")
    _git("-C", str(work), "push", "-q", "-u", "origin", "main")
    return work


@needs_git
def test_status_counts_changes_and_ahead(repo):
    assert status(repo) == source_repo.RepoStatus(changed=0, branch="main", ahead=0)
    (repo / "new.json").write_text("{}\n")
    (repo / "project.json").write_text('{"a": 1}\n')
    assert status(repo).changed == 2
    _git("-C", str(repo), "add", "-A")
    _git("-C", str(repo), *source_repo.FALLBACK_IDENTITY, "commit", "-q", "-m", "local")
    assert status(repo) == source_repo.RepoStatus(changed=0, branch="main", ahead=1)


@needs_git
def test_status_before_first_commit(tmp_path):
    _git("init", "-q", "-b", "main", str(tmp_path))
    assert status(tmp_path) == source_repo.RepoStatus(changed=0, branch="main", ahead=0)


@needs_git
def test_commit_and_push(repo, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")  # no user.name → fallback identity
    assert commit_and_push(repo, "Update route data") == "nothing to commit"
    (repo / "routes.json").write_text("[]\n")
    line = commit_and_push(repo, "Update route data")
    assert line.startswith("committed ") and line.endswith(" and pushed main")
    assert status(repo) == source_repo.RepoStatus(changed=0, branch="main", ahead=0)
    log = _git("-C", str(repo), "log", "-1", "--format=%s%n%an")
    assert log.split("\n")[:2] == ["Update route data", "hubandcircles-manager"]


@needs_git
def test_not_a_repo(tmp_path):
    with pytest.raises(SourceRepoError, match="not a git repository"):
        status(tmp_path)
