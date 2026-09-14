"""Tile package (7.3, 7.5): Web Mercator math, route corridors, coverage and the MML cache."""

import io
import json
import urllib.error
from pathlib import Path

import pytest
from shapely.geometry import shape

from manager.__main__ import main
from manager.tiles.corridor import corridor_tiles, coverage_geojson
from manager.tiles.fetch import PNG_MAGIC, FetchReport, download_missing, tile_path
from manager.tiles.mercator import tile_bounds, tile_for, tiles_covering

# A short synthetic track near Rovaniemi, WGS84 (lon, lat), about 1.5 km long.
LINE = [(25.72, 66.50), (25.73, 66.502), (25.75, 66.51)]
TILE_PNG = PNG_MAGIC + b"\x00" * 8


# --- mercator ---------------------------------------------------------------------------------


def test_tile_for_known_values():
    assert tile_for(25.72, 66.50, 13) == (4681, 2048)
    assert tile_for(0, 0, 0) == (0, 0)
    assert tile_for(-180, 85, 1) == (0, 0)
    assert tile_for(179.9, -85, 1) == (1, 1)


def test_tile_bounds_round_trip():
    west, south, east, north = tile_bounds(4681, 2048, 13)
    assert west < 25.72 < east and south < 66.50 < north
    assert east - west == pytest.approx(360 / 8192)
    # The point of each corner maps back into the same tile or its neighbour.
    assert tile_for((west + east) / 2, (south + north) / 2, 13) == (4681, 2048)


def test_tiles_covering_counts_rows_and_columns():
    west, south, east, north = tile_bounds(4681, 2048, 13)
    inset = (west + 1e-6, south + 1e-6, east - 1e-6, north - 1e-6)
    tiles = list(tiles_covering(inset, 14))
    assert len(tiles) == 4 and {t[0] for t in tiles} == {14}
    assert list(tiles_covering(inset, 13)) == [(13, 4681, 2048)]


# --- corridor ---------------------------------------------------------------------------------


def test_corridor_grows_with_buffer_and_shrinks_with_clip():
    narrow = corridor_tiles([LINE], {16: 200})
    wide = corridor_tiles([LINE], {16: 800})
    assert narrow and narrow < wide
    clipped = corridor_tiles([LINE], {16: 800}, clip=(25.70, 66.49, 25.73, 66.51))
    assert clipped and clipped < wide
    assert all(z == 16 for z, _, _ in wide)


def test_corridor_zooms_follow_the_buffer_keys():
    tiles = corridor_tiles([LINE], {13: 3000, 16: 400})
    assert {z for z, _, _ in tiles} == {13, 16}
    assert (13, 4681, 2048) in tiles


def test_corridor_outside_clip_is_empty():
    assert corridor_tiles([LINE], {16: 400}, clip=(20.0, 60.0, 21.0, 61.0)) == set()


def test_coverage_geojson_is_a_valid_polygon_feature():
    feature = coverage_geojson([LINE], 3000, clip=(25.40, 66.30, 26.20, 66.70))
    assert feature["type"] == "Feature" and feature["properties"] == {"buffer_m": 3000}
    geometry = shape(feature["geometry"])
    assert geometry.geom_type in ("Polygon", "MultiPolygon") and geometry.is_valid
    assert geometry.contains(shape({"type": "Point", "coordinates": LINE[1]}))
    assert geometry.bounds[0] > 25.6 and geometry.bounds[2] < 25.9  # about 3 km around the line
    json.dumps(feature)  # rounded plain floats, serialisable


def test_coverage_geojson_without_track_is_empty():
    assert coverage_geojson([], 3000)["geometry"] == {"type": "Polygon", "coordinates": []}


# --- fetch ------------------------------------------------------------------------------------


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def fake_wmts(monkeypatch):
    """urlopen that serves a PNG for every tile except x == 99, and records the requests."""
    requests: list = []

    def urlopen(request, timeout, context):
        assert context is not None
        requests.append(request)
        _z, y, x = request.full_url.removesuffix(".png").rsplit("/", 3)[1:]
        if x == "99":
            raise urllib.error.HTTPError(request.full_url, 404, "not found", {}, None)
        if y == "7":
            return FakeResponse(b"<html>error</html>")
        return FakeResponse(TILE_PNG)

    monkeypatch.setattr("manager.tiles.fetch.urllib.request.urlopen", urlopen)
    return requests


def test_download_missing_writes_skips_and_reports(tmp_path: Path, fake_wmts):
    cache = tmp_path / "tiles"
    cached = tile_path(cache, "maastokartta", (13, 1, 2))
    cached.parent.mkdir(parents=True)
    cached.write_bytes(TILE_PNG)
    tiles = {(13, 1, 2), (13, 1, 3), (13, 99, 3), (13, 2, 7)}
    report = download_missing(tiles, cache, "maastokartta", key="secret", max_workers=2)
    assert (report.downloaded, report.cached, report.failed) == (1, 1, 2)
    assert report.text() == "4 tiles needed, 1 cached, 1 downloaded, 2 failed"
    assert tile_path(cache, "maastokartta", (13, 1, 3)).read_bytes() == TILE_PNG
    assert not tile_path(cache, "maastokartta", (13, 99, 3)).exists()
    assert not tile_path(cache, "maastokartta", (13, 2, 7)).exists()  # not a PNG: not cached
    assert sorted(report.errors) == [
        "13/2/7: not a PNG (18 bytes)",
        "13/99/3: HTTP Error 404: not found",
    ]
    # Every failure was retried once; the key travels as basic auth, never in the URL.
    urls = [r.full_url for r in fake_wmts]
    assert len(urls) == 5 and all("secret" not in u for u in urls)
    assert all(
        u.startswith("https://avoin-karttakuva.maanmittauslaitos.fi/avoin/wmts/1.0.0/")
        for u in urls
    )
    assert "/maastokartta/default/WGS84_Pseudo-Mercator/13/3/1.png" in "".join(urls)  # {z}/{y}/{x}
    assert fake_wmts[0].get_header("Authorization") == "Basic c2VjcmV0Og=="


def test_download_missing_progress_every_100(tmp_path: Path, fake_wmts):
    calls = []
    tiles = {(14, x, 1) for x in range(100, 250)}
    report = download_missing(
        tiles, tmp_path, "maastokartta", key="k", progress=lambda d, t: calls.append((d, t))
    )
    assert report == FetchReport(downloaded=150)
    assert calls == [(100, 150)]


# --- CLI --------------------------------------------------------------------------------------


def test_fetch_tiles_cli_offline(data: Path, tmp_path: Path, monkeypatch, capsys, fake_wmts):
    card = {
        "id": "topo",
        "name": {"fi": "Maastokartta", "en": "Topographic map"},
        "slot": "base",
        "source": {"method": "mml_corridor", "layer": "maastokartta", "buffers_m": {"12": 4000}},
        "publish_format": "xyz",
        "visible_in": {"themes": ["gravel"], "routes": []},
        "attribution": "© Maanmittauslaitos, CC BY 4.0",
    }
    (data / "layers" / "topo.json").write_text(json.dumps(card, ensure_ascii=False))
    monkeypatch.setenv("TILE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("MML_API_KEY", raising=False)
    monkeypatch.setattr("manager.settings.load_env", lambda *a, **k: None)
    monkeypatch.setattr("manager.__main__.load_env", lambda *a, **k: None)
    assert main(["fetch", "tiles", "--data", str(data)]) == 2
    assert "MML_API_KEY" in capsys.readouterr().err
    monkeypatch.setenv("MML_API_KEY", "k")
    assert main(["fetch", "tiles", "--data", str(data), "--layer", "nope"]) == 2
    assert main(["fetch", "tiles", "--data", str(data)]) == 0
    out = capsys.readouterr().out
    assert "layer topo: 9 tiles needed, 0 cached, estimated size 0.3 MB" in out
    assert "layer topo: 9 tiles needed, 0 cached, 9 downloaded, 0 failed" in out
    assert (tmp_path / "cache" / "maastokartta" / "12" / "2340" / "1024.png").is_file()
    # Second run: everything is cached, nothing is requested.
    requests = len(fake_wmts)
    assert main(["fetch", "tiles", "--data", str(data)]) == 0
    assert "9 tiles needed, 9 cached, 0 downloaded" in capsys.readouterr().out
    assert len(fake_wmts) == requests
