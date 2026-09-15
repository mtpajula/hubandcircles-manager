"""Elevation fill from the MML 2 m elevation model (AP40).

A digitised track (QGIS GeoJSON, Lipas GPX) has no elevations, which hides the ascent and the
profile (P11). This module samples the National Land Survey's `korkeusmalli_2m` coverage
(WCS 2.0.1 GetCoverage, float32 GeoTIFF in EPSG:3067) for every point without an elevation.
The DEM is fetched in 500 m cells cached under `TILE_CACHE_DIR/dem/`, one request per cell.

Network code follows tiles/fetch.py: the API key travels as HTTP basic auth (user = key, empty
password), never in a URL or a log line (chapter 13). Pillow reads the GeoTIFF (mode "F"); the
georeference comes from the ModelTiepoint (33922) and ModelPixelScale (33550) tags.
"""

import base64
import os
import urllib.request
from array import array
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from manager.build import write_json
from manager.build.gpx import export_gpx
from manager.build.projection import to_m
from manager.build.routes import TrackPoint, read_track
from manager.http import ssl_context
from manager.models import Route

WCS_URL = "https://avoin-karttakuva.maanmittauslaitos.fi/ortokuvat-ja-korkeusmallit/wcs/v2"
COVERAGE_ID = "korkeusmalli_2m"
CELL_M = 500
# The coverage's no-data appears as a large negative number; Finland has no land below -100 m.
NO_DATA_BELOW = -100.0
USER_AGENT = "hubandcircles-manager"
TIMEOUT_S = 60
MODEL_TIEPOINT = 33922
MODEL_PIXEL_SCALE = 33550
TIFF_MAGIC = (b"II*\x00", b"MM\x00*")

Cell = tuple[int, int]  # (e0, n0) of the cell's south-west corner in EPSG:3067 metres


class ElevationError(Exception):
    """A DEM cell could not be fetched or read; nothing was written."""


def cell_of(e: float, n: float, cell_m: int = CELL_M) -> Cell:
    return (int(e // cell_m) * cell_m, int(n // cell_m) * cell_m)


def dem_cells(points_3067: list[tuple[float, float]], cell_m: int = CELL_M) -> set[Cell]:
    """The grid cells (aligned to `cell_m`) touched by the points."""
    return {cell_of(e, n, cell_m) for e, n in points_3067}


def cell_path(cache_dir: Path, e0: int, n0: int) -> Path:
    return cache_dir / "dem" / f"{e0}_{n0}.tif"


def fetch_cell(e0: int, n0: int, *, key: str, cache_dir: Path, cell_m: int = CELL_M) -> Path:
    """The cached GeoTIFF of one cell, downloaded when the cache lacks it.

    The file is written whole or not at all, so a partial download never counts as cached.
    """
    target = cell_path(cache_dir, e0, n0)
    if target.is_file():
        return target
    url = (
        f"{WCS_URL}?service=WCS&version=2.0.1&request=GetCoverage&CoverageID={COVERAGE_ID}"
        f"&SUBSET=E({e0},{e0 + cell_m})&SUBSET=N({n0},{n0 + cell_m})&format=image/tiff"
    )
    token = base64.b64encode(f"{key}:".encode()).decode("ascii")
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Authorization": f"Basic {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S, context=ssl_context()) as response:
            content = response.read()
    except OSError as e:  # URLError is an OSError; the message never carries the key
        raise ElevationError(f"cell {e0}_{n0}: {e}") from e
    if not content.startswith(TIFF_MAGIC):
        raise ElevationError(f"cell {e0}_{n0}: not a TIFF ({len(content)} bytes)")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    partial.write_bytes(content)
    os.replace(partial, target)
    return target


@dataclass
class Dem:
    """One cell's pixels in memory: rows top-down, columns left-right, metres above sea level."""

    width: int
    height: int
    e_min: float  # easting of the left edge of column 0
    n_max: float  # northing of the top edge of row 0
    pixel_m: tuple[float, float]  # (east-west, north-south) pixel size in metres
    values: array  # float32, row-major

    def sample(self, e: float, n: float) -> float | None:
        """The pixel that contains (e, n), None outside the cell or where the DEM has no data."""
        column = int((e - self.e_min) // self.pixel_m[0])
        row = int((self.n_max - n) // self.pixel_m[1])
        if not (0 <= column < self.width and 0 <= row < self.height):
            return None
        value = self.values[row * self.width + column]
        return None if value < NO_DATA_BELOW else float(value)


def load_dem(cell_path: Path) -> Dem:
    """Read a float32 GeoTIFF with Pillow; the georeference from tags 33922 and 33550."""
    try:
        with Image.open(cell_path) as image:
            tiepoint = image.tag_v2.get(MODEL_TIEPOINT)
            scale = image.tag_v2.get(MODEL_PIXEL_SCALE)
            if image.mode != "F" or tiepoint is None or scale is None:
                raise ElevationError(f"{cell_path}: not a float GeoTIFF with a georeference")
            i, j, _, e, n = (float(v) for v in tiepoint[:5])
            width, height = image.size
            values = array("f", image.tobytes())  # mode F = native float32 per pixel
    except (OSError, ValueError) as err:
        raise ElevationError(f"{cell_path}: {err}") from err
    # The tie point maps raster (i, j) to (e, n); shift to the raster origin (0, 0).
    return Dem(
        width=width,
        height=height,
        e_min=e - i * float(scale[0]),
        n_max=n + j * float(scale[1]),
        pixel_m=(float(scale[0]), float(scale[1])),
        values=values,
    )


def sample(cell_path: Path, e: float, n: float) -> float | None:
    """Elevation at (e, n) in EPSG:3067 from a cached cell; None outside or without data."""
    return load_dem(cell_path).sample(e, n)


@dataclass
class FillReport:
    segments: list[list[TrackPoint]]
    points: int
    filled: int
    fetched: int  # cells downloaded now
    cached: int  # cells already in the cache

    def text(self) -> str:
        return (
            f"{self.points} points, {self.filled} filled from MML DEM, "
            f"{self.fetched} cells fetched ({self.cached} cached)"
        )


def fill_elevations(
    segments: list[list[TrackPoint]], *, key: str, cache_dir: Path, overwrite: bool = False
) -> FillReport:
    """The segments (WGS84) with an elevation sampled from the DEM for every point that lacks
    one (every point with `overwrite`). A point outside the data keeps what it had (P11)."""
    positions = [[to_m(p.longitude, p.latitude) for p in seg] for seg in segments]
    wanted = [
        en
        for seg, pos in zip(segments, positions, strict=True)
        for p, en in zip(seg, pos, strict=True)
        if overwrite or p.elevation is None
    ]
    dems: dict[Cell, Dem] = {}
    fetched = cached = 0
    for e0, n0 in sorted(dem_cells(wanted)):
        was_cached = cell_path(cache_dir, e0, n0).is_file()
        dems[(e0, n0)] = load_dem(fetch_cell(e0, n0, key=key, cache_dir=cache_dir))
        cached += was_cached
        fetched += not was_cached
    filled = 0
    result = []
    for seg, pos in zip(segments, positions, strict=True):
        points = []
        for p, (e, n) in zip(seg, pos, strict=True):
            elevation = p.elevation
            if overwrite or elevation is None:
                value = dems[cell_of(e, n)].sample(e, n)
                if value is not None:
                    elevation = round(value, 1)
                    filled += 1
            points.append(TrackPoint(p.latitude, p.longitude, elevation=elevation))
        result.append(points)
    return FillReport(result, sum(len(s) for s in segments), filled, fetched, cached)


def write_track_with_elevations(
    route_dir: Path, route: Route, segments: list[list[TrackPoint]]
) -> Route:
    """Write track.gpx (<ele> on every point that has one) and the card with
    `elevation_source: "mml_dem"` and `track: "track.gpx"`. A GeoJSON original stays next to
    it untouched. Returns the written card."""
    updated = route.model_copy(update={"track": "track.gpx", "elevation_source": "mml_dem"})
    name = next(iter(route.name.values()), route.id)
    (route_dir / "track.gpx").write_bytes(export_gpx(segments, name))
    write_json(route_dir / "route.json", updated.model_dump(mode="json", exclude_none=True))
    return updated


def fill_route(
    data_dir: Path, route_id: str, *, key: str, cache_dir: Path, overwrite: bool = False
) -> FillReport:
    """routes/<id>: read the track, fill the elevations from the DEM and write it back as
    track.gpx. The CLI `elevation` command and the Routes page both call this."""
    route_dir = data_dir / "routes" / route_id
    card = route_dir / "route.json"
    if not card.is_file():
        raise ElevationError(f"{route_dir}: no such route")
    route = Route.model_validate_json(card.read_bytes())
    segments = read_track(route_dir / route.track)
    report = fill_elevations(segments, key=key, cache_dir=cache_dir, overwrite=overwrite)
    if report.filled:
        write_track_with_elevations(route_dir, route, report.segments)
    return report
