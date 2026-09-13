"""Target github-pages: one commit on gh-pages in a local bare repo standing in for GitHub."""

import shutil
import subprocess

import pytest

from manager.models import Target
from manager.models.publish_settings import defaults
from manager.publish import PublishError
from manager.publish.bundle import assemble
from manager.publish.targets import github_pages

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def bare(tmp_path):
    bare = tmp_path / "site.git"
    _git("init", "-q", "--bare", "-b", "gh-pages", str(bare))
    return bare


@pytest.fixture
def bundle(frontend, dist, tmp_path):
    return assemble(frontend, dist, defaults(), tmp_path / "bundle")


TARGET = Target(id="pages", type="github-pages", repo="owner/site")


@needs_git
def test_pushes_bundle_as_single_commit(bundle, bare, monkeypatch):
    monkeypatch.setattr(github_pages, "remote_url", lambda target: str(bare))
    line = github_pages.publish(bundle, TARGET)
    assert line == "pages: pushed to owner/site gh-pages"
    files = _git("-C", str(bare), "ls-tree", "-r", "--name-only", "gh-pages").split()
    assert {"index.html", ".nojekyll", "data/catalog.json"} <= set(files)

    github_pages.publish(bundle, TARGET)
    assert _git("-C", str(bare), "rev-list", "--count", "gh-pages").strip() == "1"


@needs_git
def test_push_error_does_not_leak_token(bundle, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "hunter2secret")
    monkeypatch.setattr(github_pages, "remote_url", lambda target: str(tmp_path / "hunter2secret"))
    with pytest.raises(PublishError, match="target pages: git push failed") as info:
        github_pages.publish(bundle, TARGET)
    assert "hunter2secret" not in str(info.value)


def test_repo_missing(bundle):
    with pytest.raises(PublishError, match="repo missing"):
        github_pages.publish(bundle, Target(id="pages", type="github-pages"))


def test_remote_url_with_and_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert github_pages.remote_url(TARGET) == "https://github.com/owner/site.git"
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    assert github_pages.remote_url(TARGET) == "https://x-access-token:tok@github.com/owner/site.git"


def test_site_url():
    assert github_pages.site_url(TARGET) == "https://owner.github.io/site/"
    assert github_pages.site_url(Target(id="pages", type="github-pages")) is None
