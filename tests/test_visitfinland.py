"""Visit Finland importer (7.6): query, type table, parsing of a saved DataHub answer,
pagination, settings. Offline."""

import io
import json
import urllib.request
from pathlib import Path

import pytest

from manager.models import Service
from manager.sources import osm, visitfinland
from manager.sources.visitfinland import (
    SourceError,
    api_settings,
    category,
    fetch,
    opening_hours,
    parse,
    query,
)

SAMPLE = Path(__file__).parent / "fixtures" / "visitfinland" / "products_sample.json"


def products() -> list[dict]:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))["data"]["product"]


@pytest.fixture
def services() -> list[Service]:
    return parse(products(), fetched_at="2026-09-14T08:00:00Z")


def test_query_filters_by_city_and_pages():
    text = query("Rovaniemi", 500, 1000)
    assert text.startswith("{ product(limit: 500, offset: 1000, where: ")
    assert 'postalAddresses: {city: {_ilike: "Rovaniemi"}}' in text
    for field in ("postalAddresses { city", "productInformations { language", "openingHours {"):
        assert field in text


@pytest.mark.parametrize(
    ("product", "expected"),
    [
        ({"type": "accommodation"}, "accommodation"),
        ({"type": "restaurant"}, "restaurant"),
        ({"type": "shop"}, "shop"),
        (
            {"type": "rental_service", "productTags": [{"tag": "cycling_mountain_biking"}]},
            "bike_rental",
        ),
        ({"type": "rental_service", "productTags": [{"tag": "winter_biking"}]}, "bike_rental"),
        ({"type": "rental_service", "productTags": [{"tag": "bike_rental"}]}, "bike_rental"),
        ({"type": "rental_service", "productTags": [{"tag": "snowmobile"}]}, None),
        ({"type": "rental_service"}, None),
        ({"type": "experience", "productTags": [{"tag": "cycling_mountain_biking"}]}, None),
        ({"type": "event"}, None),
        ({}, None),
    ],
)
def test_type_table(product, expected):
    assert category(product) == expected


def test_parse_sample(services):
    # 5 products: the shop without a location and the experience are skipped; ids are sorted.
    assert [s.id for s in services] == [
        "vf:a1b2c3d4-0001-4000-8000-000000000001",
        "vf:a1b2c3d4-0002-4000-8000-000000000002",
        "vf:a1b2c3d4-0004-4000-8000-000000000004",
    ]
    chalets, restaurant, rental = services
    assert chalets.category == "accommodation" and chalets.source == "visitfinland"
    assert chalets.name == {"fi": "Ounasvaaran mökit", "en": "Ounasvaara Chalets"}
    assert chalets.description == {
        "fi": "Mökit Ounasvaaran laella, 2,5 km keskustasta.",
        "en": "Chalets on top of the Ounasvaara fell, 2.5 km from the city centre.",
    }
    assert chalets.url == "https://example.test/chalets/en/"  # productInformations[en].url
    assert chalets.location == (25.78476, 66.501015)  # "(lat,lon)" → (lon, lat)
    assert chalets.opening_hours == "ma 08:30–20; ke–pe 08–20; la–su 10–14"  # Tuesday closed
    assert chalets.fetched_at == "2026-09-14T08:00:00Z"
    assert restaurant.category == "restaurant" and restaurant.name == {"en": "Riverside Restaurant"}
    assert restaurant.url == "https://riverside.example.test"  # company.websiteUrl as last resort
    assert restaurant.opening_hours is None
    assert rental.category == "bike_rental" and rental.url == "https://example.test/bikes"
    assert rental.name == {"fi": "Pyörävuokraamo", "en": "Bike Rental"}  # zh-Hans dropped
    assert rental.opening_hours == "ma 10–18; ke 10–18"  # not consecutive, not merged


def test_description_is_trimmed_per_language():
    product = {
        **products()[0],
        "productInformations": [{"language": "en", "name": "X", "description": "a" * 600}],
    }
    assert parse([product])[0].description == {"en": "a" * 500}


def test_parse_without_fetched_at_stamps_utc_now():
    service = parse([products()[1]])
    assert service[0].fetched_at.endswith("Z") and service[0].fetched_at.startswith("20")


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        (None, None),
        ([], None),
        ([{"weekday": "monday", "opens": None, "closes": None, "open": True}], None),
        ([{"weekday": "monday", "opens": "10:00:00", "closes": "18:00:00", "open": False}], None),
        (
            [
                {"weekday": d, "opens": "00:00:00", "closes": "24:00:00", "open": True}
                for d in visitfinland.WEEKDAYS
            ],
            "ma–su 00–24",
        ),
        (
            [
                {"weekday": "sunday", "opens": "12:00:00", "closes": "22:30:00", "open": True},
                {"weekday": "friday", "opens": "11:00:00", "closes": "23:00:00", "open": True},
                {"weekday": "saturday", "opens": "11:00:00", "closes": "23:00:00", "open": True},
            ],
            "pe–la 11–23; su 12–22:30",
        ),
    ],
)
def test_opening_hours_text(hours, expected):
    assert opening_hours(hours) == expected


def test_snapshot_round_trip_and_diff(tmp_path, services):
    assert visitfinland.read_snapshot(tmp_path) == []
    path = visitfinland.write_snapshot(tmp_path, services)
    assert path == tmp_path / "services" / "visitfinland.geojson"
    collection = json.loads(path.read_text(encoding="utf-8"))
    assert collection["type"] == "FeatureCollection"
    assert collection["features"][0]["geometry"]["coordinates"] == [25.78476, 66.501015]
    assert visitfinland.read_snapshot(tmp_path) == services
    assert visitfinland.diff is osm.diff  # one change view for both importers
    assert visitfinland.diff(services, services[1:]).summary() == (
        "added 0, removed 1, changed 0, unchanged 2"
    )


def test_fetch_paginates_until_a_short_page(monkeypatch):
    """No network: urlopen is replaced; 500 products then 2 → two requests, 502 products."""
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        count = 500 if len(requests) == 1 else 2
        page = [{"id": f"p{len(requests)}-{i}"} for i in range(count)]
        return io.BytesIO(json.dumps({"data": {"product": page}}).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = fetch("Rovaniemi", url="https://vf.test/graphql", key="secret", timeout_s=9)
    assert len(result) == 502 and result[-1] == {"id": "p2-1"}
    assert len(requests) == 2
    first, second = requests
    assert first.full_url == "https://vf.test/graphql" and first.get_method() == "POST"
    assert first.get_header("Ocp-apim-subscription-key") == "secret"
    assert first.get_header("Content-type") == "application/json"
    assert json.loads(first.data)["query"] == query("Rovaniemi", 500, 0)
    assert json.loads(second.data)["query"] == query("Rovaniemi", 500, 500)


def test_fetch_raises_on_graphql_errors(monkeypatch):
    answer = {"errors": [{"message": "field 'foo' not found"}]}
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda request, timeout: io.BytesIO(json.dumps(answer).encode("utf-8")),
    )
    with pytest.raises(SourceError, match="field 'foo' not found"):
        fetch("Rovaniemi", key="secret")


def test_api_settings_require_the_key(monkeypatch):
    monkeypatch.delenv("VF_API_KEY", raising=False)
    monkeypatch.delenv("VF_API_URL", raising=False)
    with pytest.raises(SourceError, match="VF_API_KEY"):
        api_settings()
    monkeypatch.setenv("VF_API_KEY", "secret")
    assert api_settings() == (visitfinland.VF_API_URL, "secret")
    monkeypatch.setenv("VF_API_URL", "https://vf.test/graphql")
    assert api_settings() == ("https://vf.test/graphql", "secret")


def test_cli_fetch_visitfinland_offline(data, monkeypatch, capsys):
    from manager.__main__ import main

    monkeypatch.setenv("VF_API_KEY", "")  # empty counts as missing and shadows a real .env
    assert main(["fetch", "visitfinland", "--data", str(data)]) == 2  # no municipality, no --city
    assert "Pass --city" in capsys.readouterr().err
    assert main(["fetch", "visitfinland", "--data", str(data), "--city", "Rovaniemi"]) == 1
    assert "VF_API_KEY missing" in capsys.readouterr().err

    monkeypatch.setenv("VF_API_KEY", "secret")
    calls = []

    def fake_fetch(city, *, url, key, **_):
        calls.append((city, url, key))
        return products()

    monkeypatch.setattr(visitfinland, "fetch", fake_fetch)
    assert main(["fetch", "visitfinland", "--data", str(data), "--city", "Rovaniemi"]) == 0
    assert calls == [("Rovaniemi", visitfinland.VF_API_URL, "secret")]
    out = capsys.readouterr().out
    assert out.startswith("visitfinland: 3 services; added 3, removed 0, changed 0, unchanged 0")
    assert "  + vf:a1b2c3d4-0001-4000-8000-000000000001  accommodation  Ounasvaaran mökit" in out
    assert len(visitfinland.read_snapshot(data)) == 3
