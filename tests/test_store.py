"""Source data writes: route/theme/project round trips, GPX and slug guards, deletion."""

import json

import pytest

from manager import store
from manager.build.read import read_source_data
from manager.models import GallerySection, Route, TextSection, Theme

GPX = (
    b'<?xml version="1.0"?><gpx version="1.1" creator="t" '
    b'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
    b'<trkpt lat="66.5" lon="25.7"></trkpt><trkpt lat="66.51" lon="25.71"></trkpt>'
    b"</trkseg></trk></gpx>"
)
ONE_POINT_GPX = GPX.replace(b'<trkpt lat="66.51" lon="25.71"></trkpt>', b"")


def _route(**overrides) -> Route:
    fields = {"id": "new-loop", "name": {"fi": "Uusi"}, "themes": ["gravel"], "seasons": ["summer"]}
    return Route(**{**fields, **overrides})


def test_save_route_writes_card_and_track(data):
    directory = store.save_route(data, _route(lipas_id=5), GPX)
    assert directory == data / "routes" / "new-loop"
    text = (directory / "route.json").read_text(encoding="utf-8")
    assert text.endswith("}\n") and "\n  " in text  # pretty, trailing newline
    assert "difficulty" not in json.loads(text)  # exclude_none
    assert (directory / "track.gpx").read_bytes() == GPX
    assert [r.id for _, r in read_source_data(data).routes] == ["new-loop", "test-loop"]


def test_save_route_keeps_track_when_no_gpx_given(data):
    before = (data / "routes" / "test-loop" / "track.gpx").read_bytes()
    existing = next(r for _, r in read_source_data(data).routes)
    store.save_route(data, existing.model_copy(update={"name": {"fi": "Muutettu"}}))
    assert (data / "routes" / "test-loop" / "track.gpx").read_bytes() == before
    assert json.loads((data / "routes" / "test-loop" / "route.json").read_text())["name"] == {
        "fi": "Muutettu"
    }


def test_save_route_refuses_new_route_without_track(data):
    with pytest.raises(store.StoreError, match="track is missing"):
        store.save_route(data, _route())
    assert not (data / "routes" / "new-loop").exists()


@pytest.mark.parametrize("gpx", [b"not xml", ONE_POINT_GPX])
def test_save_route_refuses_bad_gpx(data, gpx):
    with pytest.raises(store.StoreError, match="GPX"):
        store.save_route(data, _route(), gpx)
    assert not (data / "routes" / "new-loop").exists()


@pytest.mark.parametrize("route_id", ["Uusi Reitti", "../x", "-a", "a--b", ""])
def test_save_route_refuses_non_slug_id(data, route_id):
    with pytest.raises(store.StoreError, match="slug"):
        store.save_route(data, _route(id=route_id), GPX)


def test_delete_route_removes_directory_only_for_existing_slug(data):
    store.delete_route(data, "test-loop")
    assert not (data / "routes" / "test-loop").exists()
    with pytest.raises(store.StoreError):
        store.delete_route(data, "test-loop")
    with pytest.raises(store.StoreError):
        store.delete_route(data, "../themes")
    assert (data / "themes").is_dir()


def test_save_theme_and_project_round_trip(data):
    source = read_source_data(data)
    theme = next(t for t in source.themes if t.id == "gravel")
    changed = theme.model_copy(update={"order": 9, "tagline": None})
    assert store.save_theme(data, changed) == data / "themes" / "gravel.json"
    assert "tagline" not in json.loads((data / "themes" / "gravel.json").read_text())
    project = source.project.model_copy(update={"nearby_services_m": 750})
    assert store.save_project(data, project) == data / "project.json"
    reread = read_source_data(data)
    assert next(t for t in reread.themes if t.id == "gravel") == Theme.model_validate(
        changed.model_dump()
    )
    assert reread.project.nearby_services_m == 750


def test_description_helpers_touch_only_the_first_text_section():
    gallery = GallerySection(type="gallery", media=["a.jpg"])
    route = _route(sections=[gallery, TextSection(type="text", content={"fi": "x"})])
    assert store.description(route) == {"fi": "x"}
    assert store.description(_route()) == {}
    updated = store.with_description(route, {"fi": "y", "en": "z"})
    assert updated.sections == [gallery, TextSection(type="text", content={"fi": "y", "en": "z"})]
    assert store.with_description(route, {}).sections == [gallery]
    assert store.with_description(_route(), {"fi": "n"}).sections == [
        TextSection(type="text", content={"fi": "n"})
    ]
    assert route.sections[1].content == {"fi": "x"}  # the original is not mutated


def test_slugify_is_the_lipas_one():
    assert store.slugify("Ounasvaaran Ympäri!") == "ounasvaaran-ympari"


def test_save_route_writes_images_under_media(data):
    images = [("IMG 0001.JPG", b"\xff\xd8jpeg"), ("Kivikkoinen lasku.jpeg", b"\xff\xd8other")]
    directory = store.save_route(data, _route(), GPX, images=images)
    assert (directory / "media" / "img-0001.jpg").read_bytes() == b"\xff\xd8jpeg"
    assert (directory / "media" / "kivikkoinen-lasku.jpeg").read_bytes() == b"\xff\xd8other"
    assert store.media_key("IMG 0001.JPG") == "media/img-0001.jpg"


def test_save_route_accepts_a_grown_media_dict(data):
    from manager.models import MediaInfo

    existing = next(r for _, r in read_source_data(data).routes)
    grown = existing.model_copy(
        update={"media": {"media/img-0001.jpg": MediaInfo(author="A", license="CC0")}}
    )
    store.save_route(data, grown, images=[("IMG 0001.JPG", b"\xff\xd8jpeg")])
    reread = next(r for _, r in read_source_data(data).routes)
    assert reread.media == grown.media
    assert (data / "routes" / "test-loop" / "media" / "img-0001.jpg").is_file()


def test_remove_media_drops_file_and_every_reference(data):
    from manager.models import HardestSection, MediaInfo

    info = MediaInfo(author="A", license="CC0")
    existing = next(r for _, r in read_source_data(data).routes)
    card = existing.model_copy(
        update={
            "media": {"media/a.jpg": info, "media/b.jpg": info},
            "cover_image": "media/a.jpg",
            "hardest_section": HardestSection(media="media/a.jpg", km=0.5),
            "sections": [
                *existing.sections,
                GallerySection(type="gallery", media=["media/a.jpg", "media/b.jpg"]),
            ],
        }
    )
    store.save_route(data, card, images=[("a.jpg", b"a"), ("b.jpg", b"b")])
    updated = store.remove_media(data, "test-loop", "media/a.jpg")
    assert list(updated.media) == ["media/b.jpg"]
    assert updated.cover_image is None and updated.hardest_section is None
    assert updated.sections[-1].media == ["media/b.jpg"]
    assert not (data / "routes" / "test-loop" / "media" / "a.jpg").exists()
    assert (data / "routes" / "test-loop" / "media" / "b.jpg").is_file()
    assert next(r for _, r in read_source_data(data).routes) == updated
    store.remove_media(data, "test-loop", "media/missing.jpg")  # a missing file is not an error
    for bad in ("track.gpx", "media/../track.gpx", "media/x/y.jpg"):
        with pytest.raises(store.StoreError, match="media key"):
            store.remove_media(data, "test-loop", bad)
    assert (data / "routes" / "test-loop" / "track.gpx").is_file()
    with pytest.raises(store.StoreError, match="no such route"):
        store.remove_media(data, "nope", "media/a.jpg")
