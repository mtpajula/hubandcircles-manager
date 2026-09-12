"""Target directory: copies the bundle and removes leftover files from the previous publish."""

import pytest

from manager.models import Target
from manager.models.publish_settings import defaults
from manager.publish import PublishError
from manager.publish.bundle import assemble
from manager.publish.targets.directory import publish


def test_publish_to_directory(frontend, dist, tmp_path):
    bundle = assemble(frontend, dist, defaults(), tmp_path / "bundle")
    target = Target(id="k", type="directory", path=str(tmp_path / "published"))
    publish(bundle, target)
    assert (tmp_path / "published" / "index.html").is_file()
    assert (tmp_path / "published" / "data" / "catalog.json").is_file()

    (tmp_path / "published" / "assets" / "app-old.js").write_text("")
    (tmp_path / "published" / ".git").mkdir()
    publish(bundle, target)
    assert not (tmp_path / "published" / "assets" / "app-old.js").exists()
    assert (tmp_path / "published" / ".git").is_dir()
    assert (tmp_path / "published" / "assets" / "app-abc123.js").is_file()


def test_path_missing(frontend, dist, tmp_path):
    bundle = assemble(frontend, dist, defaults(), tmp_path / "bundle")
    with pytest.raises(PublishError, match="path missing"):
        publish(bundle, Target(id="k", type="directory"))
