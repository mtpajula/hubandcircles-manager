"""Media stage (5.3, 6, 13): EXIF location, WebP sizes without metadata, cover and hardest km."""

import json

import pytest
from PIL import Image

from manager.build import BuildError, build
from manager.build.media import ExifInfo, publish_image, read_exif

from .conftest import write_jpeg

# On the fixture track, at its 3rd point (66.502, 25.723), km about 0.26.
LOCATION = (25.723, 66.502)


def test_read_exif_location_and_date(tmp_path):
    info = read_exif(write_jpeg(tmp_path / "a.jpg", LOCATION, "2026:08:14 12:34:56"))
    assert info.location == pytest.approx(LOCATION, abs=1e-5)
    assert info.taken_at is not None and info.taken_at.date().isoformat() == "2026-08-14"
    south_west = read_exif(write_jpeg(tmp_path / "b.jpg", (-70.5, -33.25)))
    assert south_west.location == pytest.approx((-70.5, -33.25), abs=1e-5)


def test_read_exif_missing_is_none(tmp_path):
    assert read_exif(write_jpeg(tmp_path / "plain.jpg")) == ExifInfo(None, None)
    (tmp_path / "not-an-image.jpg").write_bytes(b"nope")
    assert read_exif(tmp_path / "not-an-image.jpg") == ExifInfo(None, None)
    assert read_exif(tmp_path / "missing.jpg") == ExifInfo(None, None)


def test_publish_image_sizes_without_metadata_idempotent(tmp_path):
    source = write_jpeg(tmp_path / "IMG_0001.jpg", LOCATION, "2026:08:14 12:34:56")
    out = tmp_path / "out" / "media"
    sizes = publish_image(source, out, "cover")
    assert set(sizes) == {"400", "1600"}
    assert all(p.startswith("media/cover-") and p.endswith(".webp") for p in sizes.values())
    assert sizes["400"].endswith("-400.webp") and sizes["1600"].endswith("-1600.webp")
    small = out / sizes["400"].removeprefix("media/")
    large = out / sizes["1600"].removeprefix("media/")
    with Image.open(small) as image:
        assert image.format == "WEBP" and image.size == (400, 300)
        assert not image.getexif() and "exif" not in image.info and "icc_profile" not in image.info
    with Image.open(large) as image:
        assert image.size == (800, 600)  # never upscaled
    before = (small.stat().st_mtime_ns, large.stat().st_mtime_ns)
    assert publish_image(source, out, "cover") == sizes
    assert (small.stat().st_mtime_ns, large.stat().st_mtime_ns) == before


def test_publish_image_missing_source_is_build_error(tmp_path):
    with pytest.raises(BuildError, match="No such file"):
        publish_image(tmp_path / "missing.jpg", tmp_path / "out", "cover")


def _card(data):
    return data / "routes" / "test-loop" / "route.json"


def _with_images(data, media_info=True, location=LOCATION):
    """Fixture copy with a cover, a hardest-section image and a gallery, all under media/."""
    directory = data / "routes" / "test-loop"
    write_jpeg(directory / "media" / "IMG_0001.jpg", location, "2026:08:14 12:34:56")
    write_jpeg(directory / "media" / "Kivikko 2.jpg", location)
    card = json.loads(_card(data).read_text())
    card["cover_image"] = "media/IMG_0001.jpg"
    card["hardest_section"] = {
        "media": "media/Kivikko 2.jpg",
        "description": {"fi": "Kivikko", "en": "Rocks"},
    }
    card["sections"].append({"type": "gallery", "media": ["media/IMG_0001.jpg"]})
    if media_info:
        card["media"] = {
            "media/IMG_0001.jpg": {"author": "M. Pajula", "license": "CC BY 4.0"},
            "media/Kivikko 2.jpg": {"author": "M. Pajula", "license": "CC BY 4.0"},
        }
    _card(data).write_text(json.dumps(card, ensure_ascii=False))


def test_build_publishes_media_and_rewrites_cover(data, tmp_path):
    _with_images(data)
    report = build(data, tmp_path / "dist")
    assert report.warnings == []
    dist = tmp_path / "dist"
    files = sorted(p.name for p in (dist / "routes" / "test-loop" / "media").iterdir())
    assert len(files) == 4 and files[0].startswith("cover-") and files[2].startswith("kivikko-2-")
    small = next(f for f in files if f.startswith("cover-") and f.endswith("-400.webp"))

    route = json.loads((dist / "routes" / "test-loop" / "route.json").read_text())
    cover = route["media"]["media/IMG_0001.jpg"]
    assert cover["author"] == "M. Pajula" and cover["taken_at"] == "2026-08-14"
    assert cover["location"] == pytest.approx(list(LOCATION), abs=1e-5)
    assert cover["sizes"]["400"] == f"media/{small}"
    assert cover["sizes"]["1600"].endswith("-1600.webp")
    assert route["cover_image"] == f"routes/test-loop/media/{small}"
    assert (dist / route["cover_image"]).is_file()
    # Everything but cover_image is a key into media (5.3, model docstring).
    assert route["hardest_section"]["media"] == "media/Kivikko 2.jpg"
    assert route["sections"][-1]["media"] == ["media/IMG_0001.jpg"]
    assert "taken_at" not in route["media"]["media/Kivikko 2.jpg"]
    # hardest_section.km projected from the EXIF location onto the track (7.11).
    assert route["hardest_section"]["km"] == pytest.approx(0.3, abs=0.1)

    catalog = json.loads((dist / "catalog.json").read_text())
    assert catalog["routes"][0]["cover_image"] == route["cover_image"]


def test_build_source_km_wins_over_exif(data, tmp_path):
    _with_images(data)
    card = json.loads(_card(data).read_text())
    card["hardest_section"]["km"] = 1.1
    _card(data).write_text(json.dumps(card, ensure_ascii=False))
    build(data, tmp_path / "dist")
    route = json.loads((tmp_path / "dist" / "routes" / "test-loop" / "route.json").read_text())
    assert route["hardest_section"]["km"] == 1.1


def test_build_hardest_section_without_location_warns(data, tmp_path):
    _with_images(data, location=None)
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: hardest_section.km missing and image has no location"
    ]
    route = json.loads((tmp_path / "dist" / "routes" / "test-loop" / "route.json").read_text())
    assert "km" not in route["hardest_section"]
    assert "location" not in route["media"]["media/IMG_0001.jpg"]


def test_build_missing_media_info_is_error(data, tmp_path):
    _with_images(data, media_info=False)
    with pytest.raises(
        BuildError, match="route test-loop: media info missing for 'media/IMG_0001.jpg'"
    ):
        build(data, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_build_missing_media_file_is_error(data, tmp_path):
    card = json.loads(_card(data).read_text())
    card["media"] = {"media/gone.jpg": {"author": "x", "license": "CC0"}}
    _card(data).write_text(json.dumps(card))
    with pytest.raises(BuildError, match="gone.jpg"):
        build(data, tmp_path / "dist")
