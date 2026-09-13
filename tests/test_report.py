"""Presentation coverage report (7.2, report row): routes with data per theme item."""

import json

from manager.build import build
from manager.build.read import read_source_data
from manager.models import PublishedRoute
from manager.report import ROUTE_DATA_ITEMS, has_item, presentation_coverage


def _published(dist) -> list[PublishedRoute]:
    return [
        PublishedRoute.model_validate_json(p.read_bytes()) for p in dist.glob("routes/*/route.json")
    ]


def test_presentation_coverage_counts_routes_per_theme_item(data, tmp_path):
    card = data / "routes" / "test-loop" / "route.json"
    second = data / "routes" / "second" / "route.json"
    second.parent.mkdir()
    (second.parent / "track.gpx").write_bytes((card.parent / "track.gpx").read_bytes())
    content = json.loads(card.read_text())
    content.update(id="second", themes=["gravel", "mtb"], segments=[], itrs={"technical": "red"})
    second.write_text(json.dumps(content))
    build(data, tmp_path / "dist")
    rows = presentation_coverage(read_source_data(data), _published(tmp_path / "dist"))

    by_key = {
        (r["theme"], r["slot"], r["item"]): (r["routes_with_data"], r["routes"]) for r in rows
    }
    assert by_key[("gravel", "key_figures", "surface_shares")] == (1, 2)
    assert by_key[("gravel", "key_figures", "itrs_endurance")] == (1, 2)
    assert by_key[("gravel", "band", "surface")] == (1, 2)
    assert by_key[("mtb", "key_figures", "itrs_technical")] == (1, 1)
    assert by_key[("mtb", "band", "itrs_technical")] == (0, 1)  # band = segment attribute
    assert by_key[("road", "band", "traffic")] == (0, 0)
    assert ("gravel", "key_figures", "length") not in by_key  # comes from the track
    assert [r["theme"] for r in rows] == sorted(
        (r["theme"] for r in rows), key=["winter", "mtb", "gravel", "road", "touring"].index
    )
    assert {r["item"] for r in rows} <= set(ROUTE_DATA_ITEMS)


def test_has_item_reads_the_published_fields(dist):
    route = _published(dist)[0]
    assert has_item(route, "itrs_endurance") and not has_item(route, "itrs_technical")
    assert has_item(route, "surface_shares") and has_item(route, "traffic")
    assert not has_item(route, "winter_maintenance") and has_item(route, "length")
    assert not has_item(route, "itrs_technical", "band")  # the fixture segment has no level
