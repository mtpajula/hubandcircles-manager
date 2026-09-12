"""Bundle: frontend at the root, dist under data/, from a directory or a zip."""

import zipfile

import pytest

from manager.models.publish_settings import defaults
from manager.publish import PublishError
from manager.publish.bundle import assemble

EXPECTED_FILES = [
    "index.html",
    "assets/app-abc123.js",
    "data/catalog.json",
    "data/routes/test-loop/route.json",
]


def test_from_directory(frontend, dist, tmp_path):
    (tmp_path / "bundle" / "old.txt").parent.mkdir()
    (tmp_path / "bundle" / "old.txt").write_text("junk")
    b = assemble(frontend, dist, defaults(), tmp_path / "bundle")
    for name in EXPECTED_FILES:
        assert (b.directory / name).is_file(), name
    assert not (b.directory / "old.txt").exists()
    assert b.file_count == sum(1 for x in b.directory.rglob("*") if x.is_file())
    assert b.total_bytes > 0 and b.largest[0].startswith("data/")


def test_from_zip_with_subdirectory(frontend, dist, tmp_path):
    z = tmp_path / "web-v1.0.0.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in frontend.rglob("*"):
            if f.is_file():
                zf.write(f, f"web-v1.0.0/{f.relative_to(frontend)}")
    b = assemble(z, dist, defaults(), tmp_path / "bundle")
    for name in EXPECTED_FILES:
        assert (b.directory / name).is_file(), name
    assert not (b.directory / "web-v1.0.0").exists()


def test_without_index_html(dist, tmp_path):
    fe = tmp_path / "fe"
    fe.mkdir()
    (fe / "main.js").write_text("")
    with pytest.raises(PublishError, match="index.html"):
        assemble(fe, dist, defaults(), tmp_path / "bundle")


def test_frontend_with_data_directory_is_rejected(frontend, dist, tmp_path):
    """A dev build that copied `public/data/` into dist/ must not silently shadow the published data."""
    (frontend / "data").mkdir()
    (frontend / "data" / "catalog.json").write_text("{}")
    with pytest.raises(PublishError, match="data/"):
        assemble(frontend, dist, defaults(), tmp_path / "bundle")
