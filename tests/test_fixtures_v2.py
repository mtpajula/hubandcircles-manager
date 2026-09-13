"""V2 fixture sets (chapter 17): fx-full, fx-partial and fx-legacy build as expected.

fx-full    every 5.3 field on one route → no findings, every computed field present.
fx-partial three sparse routes → warnings only (itrs_missing, segment_coverage, translations).
fx-legacy  a legacy difficulty value → normalised with an info; `invalid/` holds a route and a
           theme that stop the build when copied in.
"""

import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from manager.build import BuildError, build
from manager.build.projection import km_along_lines
from manager.build.routes import geometry_lines
from manager.models import Catalog, PublishedRoute

FIXTURES = Path(__file__).parent / "fixtures"
FULL, PARTIAL, LEGACY = (FIXTURES / n for n in ("fx-full", "fx-partial", "fx-legacy"))


def _route(dist: Path, route_id: str) -> dict:
    return json.loads((dist / "routes" / route_id / "route.json").read_text(encoding="utf-8"))


def _warning_checks(report) -> set[str]:
    return {
        check
        for check, findings in report.findings_by_check.items()
        if any(f.level == "warning" for f in findings)
    }


# --- fx-full ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, object]:
    dist = tmp_path_factory.mktemp("full") / "dist"
    return dist, build(FULL, dist)


def test_full_builds_without_findings(full):
    dist, report = full
    assert report.route_count == 1 and report.warnings == [] and report.infos == []
    assert set(report.findings_by_check) >= {"schema", "segments", "hardest_section", "media"}
    Catalog.model_validate_json((dist / "catalog.json").read_bytes())
    PublishedRoute.model_validate_json((dist / "routes" / "full-loop" / "route.json").read_bytes())


def test_full_shares_and_dominant_surface(full):
    dist, _ = full
    route = _route(dist, "full-loop")
    for key in ("surface_shares", "traffic_shares", "itrs_technical_shares"):
        shares = route[key]
        assert "unknown" in shares and shares["unknown"] == pytest.approx(0.08, abs=0.01)
        assert sum(shares.values()) == pytest.approx(1.0, abs=1e-9)
    assert route["dominant_surface"] == "mixed"  # 0.5 / 0.5 / 0.2 km, nothing reaches 50 %
    assert route["separated_share"] == route["traffic_shares"]["separated"]
    # The 1.0–1.1 gap is published as an all-null segment (5.3).
    assert {"start_km": 1.0, "end_km": 1.1} in route["segments"]


def test_full_hardest_section_km_is_projected_from_exif(full):
    dist, _ = full
    route = _route(dist, "full-loop")
    location = route["media"]["media/rocky-descent.jpg"]["location"]
    assert location == pytest.approx([25.725, 66.501], abs=1e-5)
    track = json.loads((dist / "routes" / "full-loop" / "track.geojson").read_text())
    expected = km_along_lines(geometry_lines(track["geometry"]), tuple(location))
    assert route["hardest_section"]["km"] == pytest.approx(expected, abs=0.05)
    assert route["hardest_section"]["description"]["fi"]


def test_full_gpx_and_catalog_images(full):
    dist, _ = full
    route = _route(dist, "full-loop")
    assert route["gpx_bytes"] > 0
    assert (dist / "routes" / "full-loop" / route["gpx"]).stat().st_size == route["gpx_bytes"]
    catalog = json.loads((dist / "catalog.json").read_text(encoding="utf-8"))
    summary = catalog["routes"][0]
    assert summary["hardest_image"].startswith("routes/full-loop/media/rocky-descent-")
    assert summary["cover_image"].startswith("routes/full-loop/media/cover-")
    assert (dist / summary["hardest_image"]).is_file() and (dist / summary["cover_image"]).is_file()
    assert summary["maintainer"] == "non_municipal" and "lipas_id" not in summary
    assert route["ascent_m"] == 29 and route["winter_maintenance"] == "groomed"
    assert route["itrs"]["assessed_on"] == "2026-08-14"
    assert [s["type"] for s in route["sections"]] == [
        "text",
        "gallery",
        "video",
        "elevation_profile",
    ]


def test_full_services_nearby_and_gaps(full):
    dist, _ = full
    route = _route(dist, "full-loop")
    # services/osm.geojson: a water point and a lean-to near the track (5.3, 7.11).
    assert route["nearby_services"] == [
        {"id": "osm:node/102", "km": 0.4},
        {"id": "osm:node/103", "km": 0.9},
    ]
    assert route["service_gaps"] == {
        "hut": 1.3,
        "lean_to": 0.9,
        "water": 0.9,
        "cafe": 1.3,
        "bike_repair": 1.3,
    }
    assert route["longest_service_gap"] == {
        "winter": {"km": 0.9, "start_km": 0.0, "end_km": 0.9},
        "mtb": {"km": 0.5, "start_km": 0.4, "end_km": 0.9},
        "road": {"km": 1.3, "start_km": 0.0, "end_km": 1.3},
    }
    catalog = json.loads((dist / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["services"] == "services.geojson"
    services = json.loads((dist / catalog["services"]).read_text(encoding="utf-8"))
    assert [f["properties"]["id"] for f in services["features"]] == ["osm:node/102", "osm:node/103"]
    assert "location" not in services["features"][0]["properties"]


def test_full_media_sizes_exist_without_metadata(full):
    dist, _ = full
    route = _route(dist, "full-loop")
    assert set(route["media"]) == {"media/cover.jpg", "media/rocky-descent.jpg"}
    for media in route["media"].values():
        assert set(media["sizes"]) == {"400", "1600"}
        for path in media["sizes"].values():
            webp = dist / "routes" / "full-loop" / path
            assert webp.is_file()
            with Image.open(webp) as image:
                assert image.format == "WEBP" and dict(image.getexif()) == {}
                assert not {"exif", "icc_profile", "xmp"} & set(image.info)


def test_full_source_jpegs_are_small():
    for jpeg in (FULL / "routes" / "full-loop" / "media").glob("*.jpg"):
        assert jpeg.stat().st_size < 20 * 1024, jpeg


# --- fx-partial ------------------------------------------------------------------------------


def test_partial_warns_exactly_for_missing_itrs_coverage_and_translations(tmp_path):
    report = build(PARTIAL, tmp_path / "dist")
    assert report.route_count == 3 and report.infos == []
    assert _warning_checks(report) == {"itrs_missing", "segment_coverage", "translations"}
    assert "route municipal-loop: name missing language en" in report.warnings


def test_partial_bare_route_hides_what_it_does_not_know(tmp_path):
    dist = tmp_path / "dist"
    build(PARTIAL, dist)
    bare = _route(dist, "bare")
    # No elevations, no ITRS, no segments: nothing invented (P11).
    assert "ascent_m" not in bare and bare["profile"] == []
    for key in ("itrs", "surface_shares", "traffic_shares", "dominant_surface", "hardest_section"):
        assert key not in bare
    assert bare["segments"] == [] and bare["gpx_bytes"] > 0
    municipal = _route(dist, "municipal-loop")
    assert municipal["lipas_id"] == 613791 and municipal["maintainer"] == "municipal"
    half = _route(dist, "half-covered")
    assert half["surface_shares"] == {"asphalt": 0.5, "unknown": 0.5}
    assert half["separated_share"] == 0.5


# --- fx-legacy -------------------------------------------------------------------------------


def test_legacy_difficulty_is_normalised_with_info(tmp_path):
    dist = tmp_path / "dist"
    report = build(LEGACY, dist)
    assert report.warnings == []
    assert [f.level for f in report.findings_by_check["normalisation"]] == ["info"]
    assert "legacy-difficulty" in report.infos[0] and "'moderate'" in report.infos[0]
    assert _route(dist, "legacy-difficulty")["difficulty"] == "moderate"


def test_legacy_non_municipal_without_reasons_stops_build(tmp_path):
    data = shutil.copytree(LEGACY, tmp_path / "data")
    shutil.copytree(LEGACY / "invalid" / "routes" / "no-reasons", data / "routes" / "no-reasons")
    with pytest.raises(BuildError, match="route no-reasons: maintainer is non_municipal"):
        build(data, tmp_path / "dist")
    assert not (tmp_path / "dist").exists()


def test_legacy_unknown_presentation_identifier_names_field_and_values(tmp_path):
    data = shutil.copytree(LEGACY, tmp_path / "data")
    shutil.copy(LEGACY / "invalid" / "themes" / "bogus.json", data / "themes" / "bogus.json")
    with pytest.raises(BuildError) as e:
        build(data, tmp_path / "dist")
    message = str(e.value)
    assert "bogus.json: presentation.key_figures.0: Input should be 'length'" in message
    assert "'longest_service_gap'" in message and "input_value" not in message
