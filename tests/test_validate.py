"""Every check of table 7.2: broken input produces the expected error, warning or info."""

import json
from pathlib import Path

import pytest

from manager.build import BuildError, build
from manager.validate import CHECKS
from manager.validate.links import check_links
from manager.validate.schema import check_schema
from manager.validate.translations import is_lang_text, lang_texts

from .conftest import write_jpeg


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


def test_enum_error_names_field_and_allowed_values(data, tmp_path):
    _edit(_route(data), lambda d: d["segments"][0].update(surface="mud"))
    with pytest.raises(BuildError) as e:
        build(data, tmp_path / "dist")
    message = str(e.value)
    assert "route.json: segments.0.surface: Input should be 'asphalt'" in message
    assert "'boardwalk' or 'snow'" in message
    assert "input_value" not in message and "errors.pydantic.dev" not in message


def test_presentation_unknown_identifier_stops_build(data, tmp_path):
    _edit(data / "themes" / "gravel.json", lambda d: d["presentation"].update(band=["speed"]))
    with pytest.raises(BuildError, match="gravel.json: presentation.band.0: Input should be"):
        build(data, tmp_path / "dist")


def test_presentation_band_over_three_lanes_stops_build(data, tmp_path):
    band = ["elevation", "surface", "traffic", "itrs_technical", "surface"]
    _edit(data / "themes" / "gravel.json", lambda d: d["presentation"].update(band=band))
    with pytest.raises(BuildError, match="lanes besides elevation"):
        build(data, tmp_path / "dist")


def test_every_check_is_reported(data, tmp_path):
    report = build(data, tmp_path / "dist")
    assert tuple(report.findings_by_check) == CHECKS
    assert report.warnings == [] and report.infos == []


# --- Segments --------------------------------------------------------------------------------


def _segments(data: Path, segments: list[dict]) -> None:
    _edit(_route(data), lambda d: d.update(segments=segments))


def test_segments_within_tolerance_pass(data, tmp_path):
    # Fixture length_km is 1.3; a gap in the middle and 0.05 km past the end are allowed.
    _segments(
        data,
        [
            {"start_km": 0, "end_km": 0.5, "surface": "gravel"},
            {"start_km": 0.6, "end_km": 1.35, "surface": "gravel"},
        ],
    )
    build(data, tmp_path / "dist")


def test_segments_overlap_is_error(data, tmp_path):
    _segments(data, [{"start_km": 0, "end_km": 0.8}, {"start_km": 0.7, "end_km": 1.3}])
    with pytest.raises(BuildError, match=r"segments\[1\]: starts at 0.7 km before the previous"):
        build(data, tmp_path / "dist")


def test_segments_out_of_order_is_error(data, tmp_path):
    _segments(data, [{"start_km": 0.5, "end_km": 1.3}, {"start_km": 0, "end_km": 0.5}])
    with pytest.raises(BuildError, match=r"segments\[1\]: starts at 0.0 km before"):
        build(data, tmp_path / "dist")


def test_segments_beyond_route_is_error(data, tmp_path):
    _segments(data, [{"start_km": 0, "end_km": 1.4}])
    with pytest.raises(BuildError, match=r"segments\[0\]: 0.0-1.4 km is outside 0-1.35 km"):
        build(data, tmp_path / "dist")


def test_segments_end_before_start_is_error(data, tmp_path):
    _segments(data, [{"start_km": 1.0, "end_km": 1.0}])
    with pytest.raises(BuildError, match=r"segments\[0\]: end_km 1.0 is not after start_km 1.0"):
        build(data, tmp_path / "dist")


# --- Hardest section -------------------------------------------------------------------------


def test_hardest_section_media_key_pass_file_without_info_fails(data, tmp_path):
    write_jpeg(data / "routes" / "test-loop" / "media" / "a.jpg")
    _edit(
        _route(data),
        lambda d: d.update(
            hardest_section={"media": "media/a.jpg", "km": 0.5},
            media={"media/a.jpg": {"author": "x", "license": "CC0"}},
        ),
    )
    build(data, tmp_path / "dist")
    # A file in the route directory passes this check but needs author and license (media check).
    _edit(_route(data), lambda d: d.update(hardest_section={"media": "media/a.jpg"}, media={}))
    with pytest.raises(BuildError, match="media info missing for 'media/a.jpg'"):
        build(data, tmp_path / "dist")


def test_hardest_section_unknown_media_is_error(data, tmp_path):
    _edit(_route(data), lambda d: d.update(hardest_section={"media": "media/missing.jpg"}))
    with pytest.raises(BuildError, match="hardest_section.media 'media/missing.jpg' is neither"):
        build(data, tmp_path / "dist")


# --- ITRS values -----------------------------------------------------------------------------


def test_itrs_values_within_scale_pass(data, tmp_path):
    _edit(data / "project.json", lambda d: d.update(itrs_scales={"exposure": 4, "wilderness": 3}))
    _edit(
        _route(data), lambda d: d.update(itrs={"exposure": 4, "wilderness": 3, "endurance": "blue"})
    )
    build(data, tmp_path / "dist")


def test_itrs_values_without_scale_only_positive(data, tmp_path):
    _edit(_route(data), lambda d: d.update(itrs={"exposure": 99, "endurance": "blue"}))
    build(data, tmp_path / "dist")


def test_itrs_values_above_scale_is_error(data, tmp_path):
    _edit(data / "project.json", lambda d: d.update(itrs_scales={"exposure": 4, "wilderness": 3}))
    _edit(_route(data), lambda d: d.update(itrs={"wilderness": 4, "endurance": "blue"}))
    with pytest.raises(BuildError, match="itrs.wilderness 4 is outside 1-3"):
        build(data, tmp_path / "dist")


# --- Maintenance reasons ---------------------------------------------------------------------


def test_maintenance_reasons_non_municipal_with_reason_pass(data, tmp_path):
    _edit(
        _route(data),
        lambda d: d.update(maintainer="non_municipal", non_municipal_reasons=["unmarked"]),
    )
    assert build(data, tmp_path / "dist").warnings == []


def test_maintenance_reasons_non_municipal_without_reason_is_error(data, tmp_path):
    _edit(_route(data), lambda d: d.update(maintainer="non_municipal"))
    with pytest.raises(BuildError, match="non_municipal but non_municipal_reasons is empty"):
        build(data, tmp_path / "dist")


def test_maintenance_reasons_on_municipal_route_is_warning(data, tmp_path):
    _edit(
        _route(data), lambda d: d.update(maintainer="municipal", non_municipal_reasons=["seasonal"])
    )
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: non_municipal_reasons given although maintainer is municipal"
    ]


# --- ITRS missing ----------------------------------------------------------------------------


def test_itrs_missing_is_warning(data, tmp_path):
    # gravel key figures include itrs_endurance; the fixture route has it.
    _edit(_route(data), lambda d: d.pop("itrs"))
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: itrs.endurance missing, shown as a key figure of theme gravel"
    ]


def test_itrs_missing_sub_field_is_warning_once(data, tmp_path):
    # mtb and gravel both show itrs_endurance: one warning per missing dimension.
    _edit(_route(data), lambda d: d.update(themes=["mtb", "gravel"], itrs={"exposure": 1}))
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: itrs.technical missing, shown as a key figure of theme mtb",
        "route test-loop: itrs.endurance missing, shown as a key figure of theme mtb",
    ]


def test_itrs_missing_not_warned_without_theme_key_figure(data, tmp_path):
    _edit(
        data / "themes" / "gravel.json", lambda d: d["presentation"].update(key_figures=["length"])
    )
    _edit(_route(data), lambda d: d.pop("itrs"))
    assert build(data, tmp_path / "dist").warnings == []


# --- Segment coverage ------------------------------------------------------------------------


def test_segment_coverage_below_80_percent_is_warning(data, tmp_path):
    _segments(data, [{"start_km": 0, "end_km": 0.78, "surface": "gravel"}])
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: surface segments cover 60% of the route, below 80% (band of theme gravel)"
    ]


def test_segment_coverage_counts_only_the_lane_attribute(data, tmp_path):
    # Segments without `surface` do not count for the surface lane.
    _segments(data, [{"start_km": 0, "end_km": 1.3, "traffic": "quiet"}])
    report = build(data, tmp_path / "dist")
    assert report.warnings == [
        "route test-loop: surface segments cover 0% of the route, below 80% (band of theme gravel)"
    ]


def test_segment_coverage_not_warned_for_lane_outside_band(data, tmp_path):
    # gravel band has surface only: missing traffic segments are fine.
    _segments(data, [{"start_km": 0, "end_km": 1.3, "surface": "gravel"}])
    assert build(data, tmp_path / "dist").warnings == []


# --- Normalisation ---------------------------------------------------------------------------


def test_normalisation_legacy_difficulty_is_info(data, tmp_path):
    _edit(_route(data), lambda d: d.update(difficulty="keskivaikea"))
    report = build(data, tmp_path / "dist")
    assert report.warnings == []
    assert report.infos == ["route test-loop: legacy difficulty value normalised to 'moderate'"]
    assert [f.level for f in report.findings_by_check["normalisation"]] == ["info"]
    assert "Info: 1" in report.text()
    route = json.loads((tmp_path / "dist" / "routes" / "test-loop" / "route.json").read_text())
    assert route["difficulty"] == "moderate"


# --- Theme contrast --------------------------------------------------------------------------


def test_theme_contrast_too_low_is_error(data, tmp_path):
    # The chapter 5.8 gravel colour: 4.99:1 against white but 4.43:1 against snow.
    _edit(data / "themes" / "gravel.json", lambda d: d["colors"].update(primary="#9A6414"))
    with pytest.raises(
        BuildError,
        match=r"theme gravel: colors.primary #9A6414 has contrast 4.43:1 against snow #F4F1EC",
    ):
        build(data, tmp_path / "dist")


def test_theme_contrast_dark_enough_pass(data, tmp_path):
    _edit(data / "themes" / "gravel.json", lambda d: d["colors"].update(primary="#000000"))
    build(data, tmp_path / "dist")


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


# --- Pure segment rule (segment editor, ADMIN-UI-SPEC 2.6) ------------------------------------


def test_segment_problems_lists_every_broken_rule():
    from manager.models import Segment
    from manager.validate.segments import segment_problems

    good = [Segment(start_km=0, end_km=0.5), Segment(start_km=0.6, end_km=1.35)]
    assert segment_problems(good, 1.3) == []
    bad = [
        Segment(start_km=0, end_km=0.8),
        Segment(start_km=0.7, end_km=0.7),
        Segment(start_km=0.7, end_km=1.4),
    ]
    problems = segment_problems(bad, 1.3)
    assert [p.split(":")[0] for p in problems] == ["segments[1]", "segments[2]", "segments[2]"]
    assert "not after start_km" in problems[0]
    assert "before the previous segment ends at 0.8 km" in problems[1]
    assert "0.7-1.4 km is outside 0-1.35 km" in problems[2]
