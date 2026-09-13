"""A failed build leaves the old dist/ untouched and keeps dist.tmp for inspection; staleness."""

import json
import os

import pytest

from manager.build import BuildError, build, is_stale


def test_old_dist_survives(data, tmp_path):
    dist = tmp_path / "dist"
    build(data, dist)
    before = (dist / "catalog.json").read_bytes()

    project = data / "project.json"
    project.write_text(json.dumps({**json.loads(project.read_text()), "default_theme": "x"}))
    with pytest.raises(BuildError):
        build(data, dist)

    assert (dist / "catalog.json").read_bytes() == before
    assert (tmp_path / "dist.tmp" / "catalog.json").is_file()
    assert not (tmp_path / "dist.old").exists()


def test_is_stale_follows_source_mtimes(data, tmp_path):
    dist = tmp_path / "dist"
    assert is_stale(data, dist)  # no dist yet
    build(data, dist)
    assert not is_stale(data, dist)
    built = (dist / "catalog.json").stat().st_mtime
    (data / ".git").mkdir()
    (data / ".git" / "index").write_text("")
    os.utime(data / ".git" / "index", (built + 60, built + 60))
    assert not is_stale(data, dist)  # git bookkeeping does not count
    os.utime(data / "project.json", (built + 60, built + 60))
    assert is_stale(data, dist)
