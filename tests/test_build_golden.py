"""Building the fixture data produces the expected catalog.json and route.json."""

import json

from manager.build import build

from .conftest import EXPECTED, FIXTURE


def test_golden(tmp_path):
    report = build(FIXTURE, tmp_path / "dist")
    assert report.route_count == 1 and report.warnings == [] and report.infos == []
    assert report.first_visit_bytes > 0 and "First-visit size:" in report.text()

    catalog = json.loads((tmp_path / "dist" / "catalog.json").read_text())
    expected = json.loads((EXPECTED / "catalog.json").read_text())
    assert catalog["generated_at"].endswith("Z")
    del catalog["generated_at"], expected["generated_at"]
    assert catalog == expected
    # Chapter 5.6 / 5.8: five themes in `order`, each with tagline, dark and presentation.
    assert [t["id"] for t in catalog["themes"]] == ["winter", "mtb", "gravel", "road", "touring"]
    assert all("tagline" in t and "dark" in t and "presentation" in t for t in catalog["themes"])
    # The list card fields of 5.6 are in the summary, including the computed ones of 7.11.
    summary = catalog["routes"][0]
    assert summary["difficulty"] == "easy" and summary["itrs"] == {"endurance": "blue"}
    assert summary["dominant_surface"] == "gravel" and summary["surface_shares"] == {"gravel": 1.0}
    assert summary["separated_share"] == 0.0  # traffic is known (quiet), none of it separated
    # Chapter 5.4: the wms layer card is published without `source`, with `type` from the build.
    assert catalog["schema_version"] == 1 and [x["id"] for x in catalog["layers"]] == ["guide-map"]
    assert catalog["layers"][0]["type"] == "wms" and "source" not in catalog["layers"][0]
    assert "services" not in catalog and "coverage" not in catalog

    route = (tmp_path / "dist" / "routes" / "test-loop" / "route.json").read_text()
    assert route == (EXPECTED / "route.json").read_text()
    assert (tmp_path / "dist" / "routes" / "test-loop" / "track.geojson").is_file()
    gpx = tmp_path / "dist" / "routes" / "test-loop" / "route.gpx"
    assert gpx.stat().st_size == json.loads(route)["gpx_bytes"]
    assert (tmp_path / "dist" / "overview.geojson").is_file()
    assert not (tmp_path / "dist.tmp").exists()
