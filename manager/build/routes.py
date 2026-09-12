"""Build stage: routes. GPX → GeoJSON, simplification, length, ascent, bbox, profile (7.2)."""

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import gpxpy
import gpxpy.gpx
from pyproj import Geod, Transformer
from shapely.geometry import LineString
from shapely.ops import transform

from manager.build.errors import BuildError
from manager.models import Bbox, PublishedRoute, Route

# Same as the example in chapter 7.3: metres in EPSG:3067, degrees in WGS84.
to_m = Transformer.from_crs(4326, 3067, always_xy=True).transform
to_deg = Transformer.from_crs(3067, 4326, always_xy=True).transform
geod = Geod(ellps="WGS84")

PROFILE_POINTS = 200


Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)


@dataclass
class RouteResult:
    track: dict  # GeoJSON Feature, LineString or MultiLineString WGS84
    length_km: float
    ascent_m: int | None  # None when the track has no elevations (P11)
    bbox: Bbox
    profile: list[tuple[float, float]]  # [cumulative km, elevation m]


def simplify(line: LineString, tolerance_m: float) -> list[tuple[float, float]]:
    """Douglas–Peucker in metres; returns WGS84 coordinates with 6 decimals."""
    result = transform(to_deg, transform(to_m, line).simplify(tolerance_m))
    return [(round(lon, 6), round(lat, 6)) for lon, lat in result.coords]


def line_geometry(lines: list[Coordinates]) -> dict:
    """GeoJSON geometry: LineString for one segment, MultiLineString for several."""
    if len(lines) == 1:
        return {"type": "LineString", "coordinates": lines[0]}
    return {"type": "MultiLineString", "coordinates": lines}


def geometry_lines(geometry: dict) -> list[Coordinates]:
    """Inverse of line_geometry: the segments of a LineString or MultiLineString."""
    if geometry["type"] == "LineString":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def _segments(path: Path) -> list[list[gpxpy.gpx.GPXTrackPoint]]:
    """Track segments kept separate; segments with fewer than 2 points are dropped."""
    try:
        with path.open(encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
    except OSError as e:
        raise BuildError(f"{path}: {e.strerror}") from e
    except gpxpy.gpx.GPXException as e:
        raise BuildError(f"{path}: {e}") from e
    segments = [seg.points for trk in gpx.tracks for seg in trk.segments if len(seg.points) >= 2]
    if not segments:
        raise BuildError(f"{path}: track has fewer than 2 points")
    return segments


def _thin[T](points: list[T], at_most: int) -> list[T]:
    if len(points) <= at_most:
        return points
    last = len(points) - 1
    return [points[round(i * last / (at_most - 1))] for i in range(at_most)]


def process_route(directory: Path, route: Route) -> RouteResult:
    segments = _segments(directory / route.track)
    # Cumulative distance continues across segments without adding the gap between them:
    # the first point of a segment has the same km as the last point of the previous one.
    km_per_point: list[float] = []
    lines: list[Coordinates] = []
    for points in segments:
        lons = [p.longitude for p in points]
        lats = [p.latitude for p in points]
        km_per_point.append(km_per_point[-1] if km_per_point else 0.0)
        for m in geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])[2]:
            km_per_point.append(km_per_point[-1] + m)
        lines.append(simplify(LineString(zip(lons, lats)), 2))
    points = [p for seg in segments for p in seg]
    lons = [p.longitude for p in points]
    lats = [p.latitude for p in points]

    elevations = [p.elevation for p in points]
    # A single missing <ele> must not zero the result: pairs with a None are skipped and the
    # profile is built from the points that have an elevation, keeping their cumulative km.
    with_elevation = [(km, e) for km, e in zip(km_per_point, elevations) if e is not None]
    ascent_m: int | None = None
    profile: list[tuple[float, float]] = []
    if len(with_elevation) >= 2:
        ascent_m = int(sum(max(0.0, b - a) for (_, a), (_, b) in pairwise(with_elevation)))
        profile = _thin(
            [(round(km / 1000, 3), round(e, 1)) for km, e in with_elevation], PROFILE_POINTS
        )

    track = {
        "type": "Feature",
        "properties": {"id": route.id},
        "geometry": line_geometry(lines),
    }
    return RouteResult(
        track=track,
        length_km=round(km_per_point[-1] / 1000, 1),
        ascent_m=ascent_m,
        bbox=(round(min(lons), 4), round(min(lats), 4), round(max(lons), 4), round(max(lats), 4)),
        profile=profile,
    )


def published_route(route: Route, result: RouteResult) -> PublishedRoute:
    """route.json: source card + computed fields (5.3). V0: no media, no nearby services."""
    return PublishedRoute(
        id=route.id,
        name=route.name,
        themes=route.themes,
        seasons=route.seasons,
        length_km=result.length_km,
        ascent_m=result.ascent_m,
        bbox=result.bbox,
        cover_image=None,  # ponytail: V1 media → cover-<hash>-400.webp
        maintainer=route.maintainer,
        difficulty=route.difficulty,
        lipas_id=route.lipas_id,
        track="track.geojson",
        profile=result.profile,
        sections=route.sections,
    )
