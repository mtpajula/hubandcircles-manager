"""Building the fixture data produces the expected catalog.json and route.json."""

import json

from manager.build import build

from .conftest import EXPECTED, FIXTURE


def test_golden(tmp_path):
    report = build(FIXTURE, tmp_path / "dist")
    assert report.route_count == 1 and report.warnings == []
    assert report.first_visit_bytes > 0 and "First-visit size:" in report.text()

    catalog = json.loads((tmp_path / "dist" / "catalog.json").read_text())
    expected = json.loads((EXPECTED / "catalog.json").read_text())
    assert catalog["generated_at"].endswith("Z")
    del catalog["generated_at"], expected["generated_at"]
    assert catalog == expected
    # Chapter 5.6 / 5.8: five themes in `order`, each with tagline and dark; no V2/V3 keys yet.
    assert [t["id"] for t in catalog["themes"]] == ["winter", "mtb", "gravel", "road", "touring"]
    assert all("tagline" in t and "dark" in t for t in catalog["themes"])
    assert catalog["schema_version"] == 1 and catalog["layers"] == []
    assert "services" not in catalog and "coverage" not in catalog

    route = (tmp_path / "dist" / "routes" / "test-loop" / "route.json").read_text()
    assert route == (EXPECTED / "route.json").read_text()
    assert (tmp_path / "dist" / "routes" / "test-loop" / "track.geojson").is_file()
    assert (tmp_path / "dist" / "overview.geojson").is_file()
    assert not (tmp_path / "dist.tmp").exists()
