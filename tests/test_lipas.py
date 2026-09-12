"""Lipas import: grouping, snapshot, route card conversion and file creation (7.13). Offline."""

import json
import shutil
from pathlib import Path

import gpxpy
import pytest

from manager.build import build
from manager.models import Route
from manager.sources import lipas
from manager.sources.lipas import LipasRoute, group, import_routes, snapshot, to_route

from .conftest import FIXTURE

SAMPLE = Path(__file__).parent / "fixtures" / "lipas" / "wfs_sample_4411.json"


@pytest.fixture
def routes() -> list[LipasRoute]:
    return group(json.loads(SAMPLE.read_text(encoding="utf-8"))["features"])


def _gravel_loop(**overrides) -> LipasRoute:
    fields = {
        "lipas_id": 613791,
        "name_fi": "Arctic by Cycle: Santa's Western Gravel Loop",
        "name_en": "Arctic by Cycle: Santa's Western Gravel Loop",
        "type_code": 4412,
        "surface": "Sora,Asfaltti",
        "length_km": 493.0,
        "owner": "Kunta",
        "maintainer": "Kunta / muu",
        "www": None,
        "note": None,
        "modified": "2025-08-19T15:30:07.222Z",
        "parts": [[(445229.0, 7376018.0), (445300.0, 7376100.0)]],
    }
    return LipasRoute(**{**fields, **overrides})


def test_group_joins_parts_by_lipas_id(routes):
    assert [r.lipas_id for r in routes] == [527767, 619056]
    rollo = routes[0]
    assert len(rollo.parts) == 2 and all(len(p) >= 2 for p in rollo.parts)
    assert rollo.name_en is None and rollo.surface is None  # "" and null → unknown
    assert rollo.length_km == 23.0 and rollo.type_code == 4411
    assert routes[1].name_en == "Ounasvaara Trail Center - Loimu"


def test_snapshot_is_wgs84_with_english_keys(routes):
    collection = snapshot(routes)
    assert len(collection["features"]) == 2
    for feature in collection["features"]:
        assert set(feature["properties"]) == set(lipas.PROPERTY_KEYS)
        assert feature["geometry"]["type"] == "MultiLineString"
        for line in feature["geometry"]["coordinates"]:
            for lon, lat in line:
                assert 25 < lon < 26 and 66 < lat < 67


def test_to_route_mtb(routes):
    card, gpx_text = to_route(routes[0])
    assert card.id == "rollo-mtb-maastopyorailyreitti"
    assert card.themes == ["mtb"] and card.seasons == ["summer"]
    assert card.maintainer == "municipal" and card.lipas_id == 527767
    assert card.difficulty is None and card.name == {"fi": routes[0].name_fi}
    assert card.sections[0].type == "text" and "fi" in card.sections[0].content
    gpx = gpxpy.parse(gpx_text)
    assert len(gpx.tracks) == 1 and len(gpx.tracks[0].segments) == 2
    assert all(p.elevation is None for p in gpx.tracks[0].segments[0].points)
    assert 25 < gpx.tracks[0].segments[0].points[0].longitude < 26


def test_to_route_gravel_touring():
    card, _ = to_route(_gravel_loop())
    assert card.themes == ["gravel", "touring"]
    assert card.name == {
        "fi": card.name["fi"],
        "en": "Arctic by Cycle: Santa's Western Gravel Loop",
    }
    assert card.id == "arctic-by-cycle-santa-s-western-gravel-loop"
    assert card.sections == []


def test_to_route_short_asphalt_is_road():
    card, _ = to_route(_gravel_loop(surface="Asfaltti", length_km=12.0))
    assert card.themes == ["road"]


def test_slugify_limits_and_strips():
    assert lipas.slugify("  Ääkkös-reitti / #1  ") == "aakkos-reitti-1"
    assert len(lipas.slugify("x" * 100)) == 60


def test_import_routes_never_overwrites(tmp_path, routes):
    first = import_routes(tmp_path, routes)
    assert first == [
        "created rollo-mtb-maastopyorailyreitti",
        "created ounasvaara-trail-center-loimu",
    ]
    card_path = tmp_path / "routes" / "rollo-mtb-maastopyorailyreitti" / "route.json"
    card = Route.model_validate_json(card_path.read_bytes())
    assert card.lipas_id == 527767 and "difficulty" not in json.loads(card_path.read_text())
    assert (card_path.parent / "track.gpx").is_file()

    card_path.write_text("edited")
    second = import_routes(tmp_path, routes)
    assert all(line.startswith("skipped") and line.endswith(": exists") for line in second)
    assert card_path.read_text() == "edited"


def test_import_routes_same_slug_gets_lipas_id_suffix(tmp_path):
    routes = [_gravel_loop(lipas_id=1), _gravel_loop(lipas_id=2)]
    assert import_routes(tmp_path, routes) == [
        "created arctic-by-cycle-santa-s-western-gravel-loop",
        "created arctic-by-cycle-santa-s-western-gravel-loop-2",
    ]


def test_bbox_to_3067_covers_project_area():
    minx, miny, maxx, maxy = lipas.bbox_to_3067((25.40, 66.30, 26.20, 66.70))
    assert 400_000 < minx < maxx < 500_000 and 7_350_000 < miny < maxy < 7_420_000


def test_fetch_rejects_unknown_type_code():
    with pytest.raises(ValueError, match="unknown Lipas type code"):
        lipas.fetch((0, 0, 1, 1), [4402])


def test_build_with_imported_route(tmp_path, routes):
    data = shutil.copytree(FIXTURE, tmp_path / "data")
    import_routes(data, routes[:1])
    report = build(data, tmp_path / "dist")
    assert report.route_count == 2
    published = json.loads(
        (tmp_path / "dist" / "routes" / "rollo-mtb-maastopyorailyreitti" / "route.json").read_text()
    )
    assert "ascent_m" not in published and published["profile"] == []
    assert "difficulty" not in published
    assert published["length_km"] > 0 and published["maintainer"] == "municipal"
    assert published["lipas_id"] == 527767
    track = json.loads(
        (
            tmp_path / "dist" / "routes" / "rollo-mtb-maastopyorailyreitti" / "track.geojson"
        ).read_text()
    )
    assert track["geometry"]["type"] == "MultiLineString"
    overview = json.loads((tmp_path / "dist" / "overview.geojson").read_text())
    assert {f["geometry"]["type"] for f in overview["features"]} == {
        "LineString",
        "MultiLineString",
    }
    catalog = json.loads((tmp_path / "dist" / "catalog.json").read_text())
    summary = next(r for r in catalog["routes"] if r["id"] == "rollo-mtb-maastopyorailyreitti")
    assert "ascent_m" not in summary and summary["maintainer"] == "municipal"


def test_cli_import_lipas_offline(tmp_path, monkeypatch, capsys):
    from manager.__main__ import main

    data = shutil.copytree(FIXTURE, tmp_path / "data")
    calls = []

    def fake_fetch(bbox, type_codes, **_):
        calls.append((bbox, tuple(type_codes)))
        return json.loads(SAMPLE.read_text(encoding="utf-8"))["features"]

    monkeypatch.setattr(lipas, "fetch", fake_fetch)
    assert main(["import-lipas", "--data", str(data), "--types", "4411", "--create-routes"]) == 0
    assert calls == [(lipas.bbox_to_3067((25.40, 66.30, 26.20, 66.70)), (4411,))]
    out = capsys.readouterr().out
    assert "527767  4411  Rollo MTB -maastopy" in out and "created rollo-mtb" in out
    assert (data / "sources" / "lipas.geojson").is_file()
    assert (data / "routes" / "rollo-mtb-maastopyorailyreitti" / "track.gpx").is_file()
