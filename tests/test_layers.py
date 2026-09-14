"""Layer cards in the build (5.4, 7.2): published types, written files, references, skips."""

import json
import shutil
from pathlib import Path

import pytest

from manager.build import BuildError, build
from manager.build.layers import layer_file_name
from manager.models import Catalog
from manager.validate.links import check_links

FULL = Path(__file__).parent / "fixtures" / "fx-full"

SHELTERS = {
    "id": "shelters",
    "name": {"fi": "Laavut ja tuvat", "en": "Shelters and huts"},
    "slot": "points",
    "source": {"method": "services", "categories": ["lean_to", "hut"]},
    "visible_in": {"themes": ["winter", "touring", "mtb"], "routes": []},
    "default_on": True,
    "attribution": "© OpenStreetMap contributors",
}


def _write_layer(data: Path, card: dict) -> None:
    (data / "layers").mkdir(exist_ok=True)
    (data / "layers" / f"{card['id']}.json").write_text(json.dumps(card, ensure_ascii=False))


def _edit(path: Path, change) -> None:
    card = json.loads(path.read_text())
    change(card)
    path.write_text(json.dumps(card, ensure_ascii=False))


def _catalog(dist: Path) -> Catalog:
    return Catalog.model_validate_json((dist / "catalog.json").read_bytes())


@pytest.fixture
def full(tmp_path: Path) -> Path:
    """Editable copy of fx-full: it has an OSM snapshot with one lean_to and one water point."""
    return shutil.copytree(FULL, tmp_path / "full")


def test_services_layer_writes_geojson_with_snapshot_time(full, tmp_path):
    _write_layer(full, SHELTERS)
    report = build(full, tmp_path / "dist")
    assert report.warnings == []
    layer = _catalog(tmp_path / "dist").layers[0]
    assert layer.id == "shelters" and layer.type == "geojson" and layer.slot == "points"
    assert layer.fetched_at == "2026-09-13T08:00:00Z"
    assert layer.url.startswith("layers/shelters-") and layer.url.endswith(".geojson")
    collection = json.loads((tmp_path / "dist" / layer.url).read_text(encoding="utf-8"))
    assert [f["properties"]["category"] for f in collection["features"]] == ["lean_to"]
    assert layer.model_dump(exclude_none=True)["visible_in"] == {
        "themes": ["winter", "touring", "mtb"],
        "routes": [],
    }


def test_geojson_file_layer_is_copied_under_a_content_hash(full, tmp_path):
    collection = {"type": "FeatureCollection", "features": []}
    (full / "areas.geojson").write_text(json.dumps(collection))
    _write_layer(
        full,
        {
            "id": "areas",
            "name": {"fi": "Alueet", "en": "Areas"},
            "slot": "area",
            "source": {"method": "geojson_file", "file": "areas.geojson"},
            "attribution": "test",
            "style": {"color": "#112233", "opacity": 0.4},
        },
    )
    build(full, tmp_path / "dist")
    layer = _catalog(tmp_path / "dist").layers[0]
    content = (tmp_path / "dist" / layer.url).read_bytes()
    assert layer.url == "layers/" + layer_file_name("areas", content, ".geojson")
    assert json.loads(content) == collection
    assert layer.style.color == "#112233" and layer.fetched_at is None


def test_geojson_file_layer_missing_or_broken_stops_build(full, tmp_path):
    card = {
        "id": "areas",
        "name": {"fi": "Alueet"},
        "slot": "area",
        "source": {"method": "geojson_file", "file": "areas.geojson"},
        "attribution": "test",
    }
    _write_layer(full, card)
    with pytest.raises(BuildError, match="areas.geojson"):
        build(full, tmp_path / "dist")
    (full / "areas.geojson").write_text('{"type": "Feature"}')
    with pytest.raises(BuildError, match="not a GeoJSON FeatureCollection"):
        build(full, tmp_path / "dist")


def test_external_xyz_layer_keeps_its_template_url(data, tmp_path):
    _write_layer(
        data,
        {
            "id": "toner",
            "name": {"fi": "Toner", "en": "Toner"},
            "slot": "base",
            "source": {"method": "xyz_external"},
            "url": "https://tiles.example.org/{z}/{x}/{y}.png",
            "minzoom": 0,
            "maxzoom": 18,
            "attribution": "© Example",
        },
    )
    build(data, tmp_path / "dist")
    layers = {layer.id: layer for layer in _catalog(tmp_path / "dist").layers}
    assert layers["toner"].type == "xyz" and layers["toner"].url.endswith("{z}/{x}/{y}.png")
    assert layers["toner"].maxzoom == 18 and layers["guide-map"].type == "wms"


def test_unbuilt_source_method_is_warned_and_skipped(data, tmp_path):
    _write_layer(
        data,
        {
            "id": "topo",
            "name": {"fi": "Maastokartta"},
            "slot": "base",
            "source": {"method": "tile_dir", "dir": "topo"},
            "attribution": "© MML",
        },
    )
    report = build(data, tmp_path / "dist")
    assert report.warnings == ["layer topo: source method tile_dir not implemented yet"]
    assert [f.check for f in report.findings_by_check["layers"]] == ["layers"]
    assert [layer.id for layer in _catalog(tmp_path / "dist").layers] == ["guide-map"]


def test_skipped_layer_is_not_a_basemap_target(data, tmp_path):
    _write_layer(
        data,
        {
            "id": "topo",
            "name": {"fi": "Maastokartta"},
            "slot": "base",
            "source": {"method": "tile_dir", "dir": "topo"},
            "attribution": "© MML",
        },
    )
    _edit(data / "themes" / "gravel.json", lambda d: d.update(basemap="topo"))
    with pytest.raises(BuildError, match="theme gravel: basemap references unknown id 'topo'"):
        build(data, tmp_path / "dist")


def test_theme_basemap_and_default_layers_reference_published_layers(data, tmp_path):
    _edit(
        data / "themes" / "gravel.json",
        lambda d: d.update(basemap="guide-map", default_layers=["guide-map"]),
    )
    build(data, tmp_path / "dist")
    _edit(data / "themes" / "gravel.json", lambda d: d.update(default_layers=["shelters"]))
    with pytest.raises(BuildError, match="theme gravel: default_layers references .*'shelters'"):
        build(data, tmp_path / "dist")


def test_theme_basemap_must_be_in_the_base_slot(data, tmp_path):
    _edit(data / "layers" / "guide-map.json", lambda d: d.update(slot="raster"))
    _edit(data / "themes" / "gravel.json", lambda d: d.update(basemap="guide-map"))
    with pytest.raises(BuildError, match="basemap 'guide-map' is in slot 'raster', not 'base'"):
        build(data, tmp_path / "dist")


def test_layer_visible_in_references_themes_and_routes(data, tmp_path):
    _edit(
        data / "layers" / "guide-map.json",
        lambda d: d.update(visible_in={"themes": ["bmx"], "routes": ["nowhere"]}),
    )
    with pytest.raises(BuildError) as e:
        build(data, tmp_path / "dist")
    assert "layer guide-map: visible_in.themes references unknown id 'bmx'" in str(e.value)
    assert "layer guide-map: visible_in.routes references unknown id 'nowhere'" in str(e.value)
    _edit(
        data / "layers" / "guide-map.json",
        lambda d: d.update(visible_in={"themes": "*", "routes": ["test-loop"]}),
    )
    build(data, tmp_path / "dist")


def test_broken_layer_card_stops_build(data, tmp_path):
    _edit(data / "layers" / "guide-map.json", lambda d: d.pop("wms"))
    with pytest.raises(BuildError, match="guide-map.json: root: Value error, source method"):
        build(data, tmp_path / "dist")


def test_links_check_covers_geojson_layer_files(full, tmp_path):
    _write_layer(full, SHELTERS)
    build(full, tmp_path / "dist")
    dist = tmp_path / "dist"
    (dist / _catalog(dist).layers[0].url).unlink()
    findings = check_links(dist)
    assert [f.level for f in findings] == ["error"]
    assert findings[0].message.startswith("catalog.json: layer shelters: url")
