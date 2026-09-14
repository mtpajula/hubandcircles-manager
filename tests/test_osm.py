"""OSM importer (7.6): query, tag table, parsing of a saved Overpass answer, diff. Offline."""

import json
from pathlib import Path

import pytest

from manager.models import Service
from manager.sources import osm
from manager.sources.osm import Diff, category, diff, parse, query

SAMPLE = Path(__file__).parent / "fixtures" / "osm" / "overpass_sample.json"
AREA = (25.40, 66.30, 26.20, 66.70)


@pytest.fixture
def services() -> list[Service]:
    elements = json.loads(SAMPLE.read_text(encoding="utf-8"))["elements"]
    return parse(elements, fetched_at="2026-09-13T08:00:00Z")


def test_query_has_the_bbox_in_south_west_north_east_order():
    text = query(AREA)
    assert text.count("(66.3,25.4,66.7,26.2)") == 3
    assert text.startswith("[out:json][timeout:90];")
    assert text.rstrip().endswith("out center tags;")
    assert 'nwr["amenity"~"^(cafe|restaurant|fast_food|drinking_water|toilets|shelter|' in text
    assert 'nwr["shop"~"^(bicycle|supermarket|convenience)$"]' in text
    assert 'nwr["tourism"~"^(wilderness_hut|camp_site|picnic_site|hotel|guest_house)$"]' in text


@pytest.mark.parametrize(
    ("tags", "expected"),
    [
        ({"amenity": "cafe"}, "cafe"),
        ({"amenity": "restaurant"}, "restaurant"),
        ({"amenity": "fast_food"}, "restaurant"),
        ({"amenity": "drinking_water"}, "water"),
        ({"amenity": "toilets"}, "toilet"),
        ({"amenity": "shelter", "shelter_type": "lean_to"}, "lean_to"),
        ({"amenity": "shelter", "shelter_type": "picnic_shelter"}, None),
        ({"amenity": "shelter"}, None),
        ({"amenity": "bicycle_repair_station"}, "bike_repair"),
        ({"shop": "bicycle"}, "bike_repair"),
        ({"shop": "supermarket"}, "shop"),
        ({"shop": "convenience"}, "shop"),
        ({"tourism": "wilderness_hut"}, "hut"),
        ({"tourism": "camp_site"}, "accommodation"),
        ({"tourism": "hotel"}, "accommodation"),
        ({"tourism": "guest_house"}, "accommodation"),
        ({"tourism": "picnic_site"}, None),
        ({"amenity": "bench"}, None),
        ({}, None),
    ],
)
def test_tag_table(tags, expected):
    assert category(tags) == expected


def test_parse_sample(services):
    # 6 elements: the picnic shelter is skipped, the way uses its centre, ids are sorted.
    assert [s.id for s in services] == [
        "osm:node/101",
        "osm:node/102",
        "osm:node/103",
        "osm:node/105",
        "osm:way/201",
    ]
    by_id = {s.id: s for s in services}
    cafe = by_id["osm:node/101"]
    assert cafe.category == "cafe" and cafe.source == "osm"
    assert cafe.name == {"fi": "Kahvila Napa", "en": "Cafe Hub"}
    assert cafe.url == "https://example.test/napa"
    assert cafe.opening_hours == "Mo-Fr 09:00-17:00"
    assert cafe.location == (25.7215, 66.5012)
    assert cafe.fetched_at == "2026-09-13T08:00:00Z"
    water = by_id["osm:node/102"]
    assert water.category == "water" and water.name is None and water.url is None
    assert by_id["osm:node/103"].category == "lean_to"
    assert by_id["osm:node/105"].name == {"fi": "Erätupa", "en": "Wilderness hut"}
    market = by_id["osm:way/201"]
    assert market.category == "shop" and market.location == (25.7295, 66.501)
    assert market.url == "https://example.test/market"  # contact:website


def test_parse_without_fetched_at_stamps_utc_now():
    service = parse(
        [{"type": "node", "id": 1, "lat": 66.5, "lon": 25.7, "tags": {"amenity": "cafe"}}]
    )
    assert service[0].fetched_at.endswith("Z") and service[0].fetched_at.startswith("20")


def test_parse_skips_ways_without_centre():
    assert parse([{"type": "way", "id": 1, "tags": {"shop": "bicycle"}}]) == []


def test_diff_by_id_ignoring_fetched_at(services):
    later = [s.model_copy(update={"fetched_at": "2026-10-01T00:00:00Z"}) for s in services]
    renamed = later[0].model_copy(update={"name": {"fi": "Uusi nimi"}})
    new = Service(id="osm:node/999", category="toilet", source="osm", location=(25.7, 66.5))
    result = diff(services, [renamed, *later[2:], new])
    assert isinstance(result, Diff)
    assert [s.id for s in result.added] == ["osm:node/999"]
    assert [s.id for s in result.removed] == ["osm:node/102"]
    assert [s.id for s in result.changed] == ["osm:node/101"]
    assert result.changed[0].name == {"fi": "Uusi nimi"}
    assert [s.id for s in result.unchanged] == ["osm:node/103", "osm:node/105", "osm:way/201"]
    assert result.summary() == "added 1, removed 1, changed 1, unchanged 3"


def test_snapshot_round_trip(tmp_path, services):
    assert osm.read_snapshot(tmp_path) == []  # missing snapshot is empty
    path = osm.write_snapshot(tmp_path, services)
    assert path == tmp_path / "services" / "osm.geojson"
    collection = json.loads(path.read_text(encoding="utf-8"))
    assert collection["type"] == "FeatureCollection"
    assert "location" not in collection["features"][0]["properties"]
    assert "name" not in collection["features"][1]["properties"]  # no name → left out (P11)
    assert osm.read_snapshot(tmp_path) == services


def test_fetch_posts_the_query_with_user_agent(monkeypatch):
    """No network: urlopen is replaced; the request built by fetch() is inspected."""
    import io
    import urllib.request

    seen = {}

    def fake_urlopen(request, timeout, context=None):
        seen["request"] = request
        seen["timeout"] = timeout
        return io.BytesIO(b'{"elements": [{"type": "node", "id": 1, "lat": 66.5, "lon": 25.7}]}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    elements = osm.fetch(AREA, base_url="https://overpass.test/api", timeout_s=7)
    assert elements == [{"type": "node", "id": 1, "lat": 66.5, "lon": 25.7}]
    request = seen["request"]
    assert request.full_url == "https://overpass.test/api" and request.get_method() == "POST"
    assert request.data.decode("utf-8") == query(AREA)
    assert request.get_header("User-agent") == "hubandcircles-manager"
    assert seen["timeout"] == 7
