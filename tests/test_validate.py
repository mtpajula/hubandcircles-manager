"""Every V0 check of table 7.2: broken input produces the expected error or warning."""

import json
from pathlib import Path

import pytest

from manager.build import BuildError, build
from manager.validate.links import check_links
from manager.validate.schema import check_schema
from manager.validate.translations import is_lang_text, lang_texts


def _edit(path: Path, change) -> None:
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False))


def _route(data: Path) -> Path:
    return data / "routes" / "test-loop" / "route.json"


def test_translation_default_language_missing_is_error(data, tmp_path):
    _edit(_route(data), lambda d: d["name"].pop("fi"))
    with pytest.raises(BuildError, match="route test-loop: name missing language fi"):
        build(data, tmp_path / "dist")


def test_translation_other_language_missing_is_warning(data, tmp_path):
    _edit(_route(data), lambda d: d["name"].pop("en"))
    report = build(data, tmp_path / "dist")
    assert report.warnings == ["route test-loop: name missing language en"]


def test_translation_section_content_found_generically(data, tmp_path):
    _edit(_route(data), lambda d: d["sections"][0]["content"].pop("en"))
    report = build(data, tmp_path / "dist")
    assert report.warnings == ["route test-loop: sections[0].content missing language en"]


def test_translation_theme_tagline(data, tmp_path):
    _edit(data / "themes" / "gravel.json", lambda d: d["tagline"].pop("en"))
    report = build(data, tmp_path / "dist")
    assert report.warnings == ["theme gravel: tagline missing language en"]


def test_reference_route_theme(data, tmp_path):
    _edit(_route(data), lambda d: d.update(themes=["bmx"]))
    with pytest.raises(BuildError, match="route test-loop: themes references .*'bmx'"):
        build(data, tmp_path / "dist")


def test_reference_default_theme(data, tmp_path):
    _edit(data / "project.json", lambda d: d.update(default_theme="x"))
    with pytest.raises(BuildError, match="project: default_theme references .*'x'"):
        build(data, tmp_path / "dist")


def test_reference_basemap_without_layers(data, tmp_path):
    _edit(data / "themes" / "gravel.json", lambda d: d.update(basemap="topo"))
    with pytest.raises(BuildError, match="theme gravel: basemap references .*'topo'"):
        build(data, tmp_path / "dist")


def test_secret_leak(data, tmp_path, monkeypatch):
    monkeypatch.setenv("MML_API_KEY", "secret12345")
    _edit(_route(data), lambda d: d["sections"][0]["content"].update(fi="key secret12345"))
    with pytest.raises(BuildError) as e:
        build(data, tmp_path / "dist")
    message = str(e.value)
    assert "secret12345" not in message
    assert "MML_API_KEY" in message
    # Both the source card and the published card are named.
    assert f"{data}/routes/test-loop/route.json" in message
    assert f"{tmp_path}/dist.tmp/routes/test-loop/route.json" in message


def test_secret_does_not_leak_when_absent_from_data(data, tmp_path, monkeypatch):
    monkeypatch.setenv("MML_API_KEY", "secret12345")
    build(data, tmp_path / "dist")


def test_link_track_missing(data, tmp_path):
    build(data, tmp_path / "dist")
    dist = tmp_path / "dist"
    (dist / "routes" / "test-loop" / "track.geojson").unlink()
    errors = check_links(dist)
    assert [e.level for e in errors] == ["error"]
    assert "test-loop/route.json: track" in errors[0].message


def test_link_source_gpx_missing(data, tmp_path):
    _edit(_route(data), lambda d: d.update(track="missing.gpx"))
    with pytest.raises(BuildError, match="missing.gpx"):
        build(data, tmp_path / "dist")


def test_schema_broken_route(data, tmp_path):
    build(data, tmp_path / "dist")
    dist = tmp_path / "dist"
    _edit(dist / "routes" / "test-loop" / "route.json", lambda d: d.pop("profile"))
    errors = check_schema(dist)
    assert len(errors) == 1 and "route.json" in errors[0].message


def test_schema_broken_route_json(data, tmp_path):
    _edit(_route(data), lambda d: d.pop("name"))
    with pytest.raises(BuildError) as e:
        build(data, tmp_path / "dist")
    assert "routes/test-loop/route.json" in str(e.value) and "name" in str(e.value)


LANGUAGES = {"fi", "en"}


def test_lang_text_requires_declared_language_keys():
    # A short key alone (e.g. a colour or an abbreviation) is not a language object.
    assert not is_lang_text({"abc": "x"}, LANGUAGES)
    assert is_lang_text({"fi": "x"}, LANGUAGES)
    assert is_lang_text({"fi": "x", "en": "y"}, LANGUAGES)
    # An unknown language makes the dict a plain mapping: ignored, never reported as missing.
    assert not is_lang_text({"fi": "x", "sv": "y"}, LANGUAGES)
    assert not is_lang_text({}, LANGUAGES)
    assert not is_lang_text({"fi": 1}, LANGUAGES)


def test_lang_texts_walker_skips_non_language_dicts():
    dumped = {"colors": {"abc": "#fff"}, "name": {"fi": "x"}, "items": [{"label": {"fi": "y"}}]}
    assert list(lang_texts(dumped, LANGUAGES)) == [
        ("name", {"fi": "x"}),
        ("items[0].label", {"fi": "y"}),
    ]
