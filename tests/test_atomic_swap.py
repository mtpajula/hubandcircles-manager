"""A failed build leaves the old dist/ untouched and keeps dist.tmp for inspection."""

import json

import pytest

from manager.build import BuildError, build


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
