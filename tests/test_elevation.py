"""Elevation fill from the MML DEM (AP40) against a synthetic 500 m cell; no network."""

import json
import shutil
import struct
from pathlib import Path

import pytest
from PIL import Image, TiffImagePlugin

from manager import elevation, store
from manager.__main__ import main
from manager.build.projection import to_deg, to_m
from manager.build.routes import TrackPoint, process_route, read_track
from manager.elevation import (
    ElevationError,
    cell_path,
    dem_cells,
    fill_elevations,
    fill_route,
    sample,
    write_track_with_elevations,
)
from manager.models import Route

from .conftest import FIXTURE

FX_PARTIAL = Path(__file__).parent / "fixtures" / "fx-partial"
CELL = (443000, 7376000)  # the one 500 m cell the fixture track lies in
PIXEL_M = 2
SIZE = elevation.CELL_M // PIXEL_M  # 250 px


def fake_cell(path: Path, e0: int, n0: int) -> Path:
    """A float32 GeoTIFF like MML's: elevation = 100 + column + row / 1000, tie point at the
    north-west corner, 2 m pixels; the pixel (3, 7) holds no data."""
    values = [100.0 + c + r / 1000 for r in range(SIZE) for c in range(SIZE)]
    values[7 * SIZE + 3] = -9999.0
    image = Image.frombytes(
        "F", (SIZE, SIZE), struct.pack(f"<{SIZE * SIZE}f", *values), "raw", "F;32F"
    )
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[elevation.MODEL_TIEPOINT] = (0.0, 0.0, 0.0, float(e0), float(n0 + elevation.CELL_M), 0.0)
    info[elevation.MODEL_PIXEL_SCALE] = (float(PIXEL_M), float(PIXEL_M), 0.0)
    for tag in (elevation.MODEL_TIEPOINT, elevation.MODEL_PIXEL_SCALE):
        info.tagtype[tag] = TiffImagePlugin.TiffTags.DOUBLE
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "TIFF", tiffinfo=info)
    return path


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """fetch_cell writes a fake cell instead of calling MML; returns the cache dir."""
    cache = tmp_path / "cache"

    def fetch(e0, n0, *, key, cache_dir, cell_m=elevation.CELL_M):
        assert key == "secret" and cache_dir == cache
        target = cell_path(cache_dir, e0, n0)
        return target if target.is_file() else fake_cell(target, e0, n0)

    monkeypatch.setattr(elevation, "fetch_cell", fetch)
    return cache


def test_sample_reads_the_pixel_containing_the_point(tmp_path):
    cell = fake_cell(tmp_path / "c.tif", *CELL)
    e0, n0 = CELL
    n_top = n0 + elevation.CELL_M
    assert sample(cell, e0 + 0.5, n_top - 0.5) == pytest.approx(100.0)  # column 0, row 0
    assert sample(cell, e0 + 5 * PIXEL_M + 1, n_top - 2 * PIXEL_M - 1) == pytest.approx(105.002)
    assert sample(cell, e0 + 499.9, n0 + 0.1) == pytest.approx(100 + 249 + 0.249)
    assert sample(cell, e0 + 3 * PIXEL_M + 1, n_top - 7 * PIXEL_M - 1) is None  # no-data
    assert sample(cell, e0 - 1, n_top - 1) is None  # west of the cell
    assert sample(cell, e0 + 1, n0 - 1) is None  # the south edge belongs to the next cell


def test_load_dem_rejects_a_plain_tiff(tmp_path):
    Image.new("L", (4, 4)).save(tmp_path / "plain.tif")
    with pytest.raises(ElevationError, match="georeference"):
        sample(tmp_path / "plain.tif", 0, 0)


def test_dem_cells_of_the_fixture_track():
    points = [
        to_m(p.longitude, p.latitude)
        for seg in read_track(FIXTURE / "routes" / "test-loop" / "track.gpx")
        for p in seg
    ]
    assert dem_cells(points) == {CELL}
    assert dem_cells([(443499.9, 7376000.0), (443500.0, 7375999.9)]) == {
        CELL,
        (443500, 7375500),
    }


def test_fill_elevations_fills_only_the_missing_points(offline):
    segments = read_track(FX_PARTIAL / "routes" / "bare" / "track.gpx")
    segments[0][2].elevation = 42.0  # kept: an existing elevation wins without overwrite
    report = fill_elevations(segments, key="secret", cache_dir=offline)
    assert (report.points, report.filled, report.fetched, report.cached) == (10, 9, 1, 0)
    assert report.text() == "10 points, 9 filled from MML DEM, 1 cells fetched (0 cached)"
    filled = [p.elevation for p in report.segments[0]]
    assert filled[2] == 42.0 and all(e is not None for e in filled)
    e, n = to_m(segments[0][0].longitude, segments[0][0].latitude)
    assert filled[0] == round(sample(cell_path(offline, *CELL), e, n), 1)
    assert segments[0][0].elevation is None  # the input is not mutated

    again = fill_elevations(segments, key="secret", cache_dir=offline, overwrite=True)
    assert (again.filled, again.fetched, again.cached) == (10, 0, 1)
    assert again.segments[0][2].elevation != 42.0


def test_fill_elevations_spans_cells_and_keeps_points_without_data(offline):
    e0, n0 = CELL
    points = [
        TrackPoint(lat, lon)
        for lon, lat in (to_deg(e0 + 100, n0 + 100), to_deg(e0 + 600, n0 + 100))
    ]
    report = fill_elevations([points], key="secret", cache_dir=offline)
    assert report.fetched == 2 and report.filled == 2
    assert sorted(p.name for p in (offline / "dem").iterdir()) == [
        "443000_7376000.tif",
        "443500_7376000.tif",
    ]


def test_write_track_with_elevations_makes_the_build_compute_ascent(offline, tmp_path):
    route_dir = shutil.copytree(FX_PARTIAL / "routes" / "bare", tmp_path / "bare")
    route = Route.model_validate_json((route_dir / "route.json").read_bytes())
    assert process_route(route_dir, route).ascent_m is None
    report = fill_elevations(read_track(route_dir / route.track), key="secret", cache_dir=offline)
    written = write_track_with_elevations(route_dir, route, report.segments)
    assert written.elevation_source == "mml_dem" and written.track == "track.gpx"
    card = json.loads((route_dir / "route.json").read_text())
    assert card["elevation_source"] == "mml_dem"
    result = process_route(route_dir, written)
    assert result.ascent_m is not None and result.ascent_m > 0
    assert len(result.profile) == 10
    assert (route_dir / "track.gpx").read_text().count("<ele>") == 10


def test_fill_route_keeps_a_geojson_original(offline, data):
    route_dir = data / "routes" / "test-loop"
    lines = [
        [[p.longitude, p.latitude] for p in seg] for seg in read_track(route_dir / "track.gpx")
    ]
    geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "LineString", "coordinates": lines[0]},
    }
    (route_dir / "track.geojson").write_text(json.dumps(geojson))
    route = Route.model_validate_json((route_dir / "route.json").read_bytes())
    store.save_route(data, route.model_copy(update={"track": "track.geojson"}))
    report = fill_route(data, "test-loop", key="secret", cache_dir=offline)
    assert report.filled == 10
    card = json.loads((route_dir / "route.json").read_text())
    assert card["track"] == "track.gpx" and card["elevation_source"] == "mml_dem"
    assert json.loads((route_dir / "track.geojson").read_text()) == geojson  # untouched
    with pytest.raises(ElevationError, match="no such route"):
        fill_route(data, "nope", key="secret", cache_dir=offline)


def test_cli_elevation_offline(offline, tmp_path, monkeypatch, capsys):
    data = shutil.copytree(FX_PARTIAL, tmp_path / "partial")
    monkeypatch.setenv("MML_API_KEY", "secret")
    monkeypatch.setenv("TILE_CACHE_DIR", str(offline))
    assert main(["elevation", "--data", str(data), "--route", "bare"]) == 0
    assert (
        capsys.readouterr().out == "10 points, 10 filled from MML DEM, 1 cells fetched (0 cached)\n"
    )
    assert main(["elevation", "--data", str(data), "--route", "bare"]) == 0
    assert (
        capsys.readouterr().out == "10 points, 0 filled from MML DEM, 0 cells fetched (0 cached)\n"
    )
    assert main(["elevation", "--data", str(data), "--route", "bare", "--overwrite"]) == 0
    assert (
        capsys.readouterr().out == "10 points, 10 filled from MML DEM, 0 cells fetched (1 cached)\n"
    )
    assert main(["elevation", "--data", str(data), "--route", "missing"]) == 1
    assert "no such route" in capsys.readouterr().err
    monkeypatch.delenv("MML_API_KEY")
    monkeypatch.setattr("manager.__main__.load_env", lambda *a, **k: None)  # not the repo .env
    assert main(["elevation", "--data", str(data), "--route", "bare"]) == 2
