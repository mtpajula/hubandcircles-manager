"""publish(): settings from source data, target selection, error before publishing."""

import json

import pytest

from manager.publish import PublishError, publish


def _settings(data, **target):
    (data / "publish.json").write_text(
        json.dumps({"targets": [{"id": "k", "type": "directory", **target}], "headers": []})
    )


def test_publishes_to_all_targets(data, dist, frontend, tmp_path):
    _settings(data, path=str(tmp_path / "out"))
    b = publish(data, dist, frontend, tmp_path / "work", None)
    assert b.directory == tmp_path / "work" / "bundle"
    assert (tmp_path / "out" / "data" / "catalog.json").is_file()


def test_dry_run_does_not_publish(data, dist, frontend, tmp_path):
    _settings(data, path=str(tmp_path / "out"))
    publish(data, dist, frontend, tmp_path / "work", None, dry_run=True)
    assert not (tmp_path / "out").exists()


def test_unknown_target(data, dist, frontend, tmp_path):
    with pytest.raises(PublishError, match="unknown target: x"):
        publish(data, dist, frontend, tmp_path / "work", ["x"])


def test_frontend_missing(data, dist, tmp_path):
    with pytest.raises(PublishError, match="frontend missing"):
        publish(data, dist, None, tmp_path / "work", [])


def test_frontend_from_settings_relative(data, dist, frontend, tmp_path):
    (data / "publish.json").write_text(
        json.dumps({"frontend": {"path": str(frontend)}, "headers": []})
    )
    assert (publish(data, dist, None, tmp_path / "work", None).directory / "index.html").is_file()
