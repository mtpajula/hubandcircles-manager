"""Route corridors → tile sets and coverage (7.3).

The corridor is the track buffered per zoom level in metres (EPSG:3067), narrower as the zoom
grows, and clipped to the project area so a 1 500 km touring route does not tile all of Lapland.
"""

from shapely.geometry import LineString, MultiLineString, box, mapping
from shapely.ops import transform
from shapely.prepared import prep

from manager.build.projection import to_deg, to_m
from manager.models import Bbox
from manager.tiles.mercator import Tile, tile_bounds, tiles_covering

Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)
COVERAGE_TOLERANCE_M = 20


def _corridor(lines: list[Coordinates], buffer_m: float, clip: Bbox | None):
    """The buffered track in WGS84, clipped to `clip`; empty when nothing is inside."""
    track = MultiLineString([LineString(c) for c in lines if len(c) >= 2])
    if track.is_empty:
        return track
    if clip is not None:
        # Trim the track before buffering: cheaper, and a generous margin keeps the buffer
        # exact where it matters (1° ≈ 111 km of latitude, 44 km of longitude at 66.5° N).
        track = track.intersection(box(*clip).buffer(buffer_m / 40_000))
        if track.is_empty:
            return track
    area = transform(to_deg, transform(to_m, track).buffer(buffer_m))
    return area.intersection(box(*clip)) if clip is not None else area


def corridor_tiles(
    lines: list[Coordinates], buffers_m: dict[int, int], clip: Bbox | None = None
) -> set[Tile]:
    """Tiles at each zoom of `buffers_m` ({zoom: half-width in metres}) touching the corridor."""
    tiles: set[Tile] = set()
    for z, buffer_m in buffers_m.items():
        area = _corridor(lines, buffer_m, clip)
        if area.is_empty:
            continue
        prepared = prep(area)
        tiles.update(
            t
            for t in tiles_covering(area.bounds, z)
            if prepared.intersects(box(*tile_bounds(*t[1:], z)))
        )
    return tiles


def coverage_geojson(lines: list[Coordinates], buffer_m: int, clip: Bbox | None = None) -> dict:
    """Coverage of the widest corridor as a GeoJSON Feature (Polygon or MultiPolygon, WGS84,
    simplified to 20 m); the frontend draws it as a dashed outline (chapter 8)."""
    area = _corridor(lines, buffer_m, clip)
    if not area.is_empty:
        area = transform(
            to_deg, transform(to_m, area).simplify(COVERAGE_TOLERANCE_M, preserve_topology=True)
        )
    geometry = (
        _rounded(mapping(area)) if not area.is_empty else {"type": "Polygon", "coordinates": []}
    )
    return {"type": "Feature", "properties": {"buffer_m": buffer_m}, "geometry": geometry}


def _rounded(geometry: dict) -> dict:
    def walk(value):
        if isinstance(value, float):
            return round(value, 5)
        if isinstance(value, (list, tuple)):
            return [walk(v) for v in value]
        return value

    return {"type": geometry["type"], "coordinates": walk(geometry["coordinates"])}
