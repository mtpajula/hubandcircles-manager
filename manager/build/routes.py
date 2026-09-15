"""Build stage: routes. Track → GeoJSON, simplification, length, ascent, bbox, profile, km (7.2).

The track is a GPX file (gpxpy) or a GeoJSON file (AP40: LineString/MultiLineString, WGS84,
optional third coordinate = elevation, as QGIS exports it). Both become the same segments of
TrackPoint, so everything after read_track is format-agnostic.
"""

import json
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import gpxpy
import gpxpy.gpx
from pyproj import Geod
from shapely.geometry import LineString
from shapely.ops import transform

from manager.build.errors import BuildError
from manager.build.projection import TrackProjector, km_along_lines, to_deg, to_m
from manager.build.segments import dominant, normalise, shares
from manager.models import (
    Bbox,
    NearbyService,
    PublishedMedia,
    PublishedRoute,
    Route,
    Service,
    ServiceGap,
    Theme,
)

geod = Geod(ellps="WGS84")

PROFILE_POINTS = 200
GEOJSON_SUFFIXES = (".geojson", ".json")


Coordinates = list[tuple[float, float]]  # WGS84 (lon, lat)
# gpxpy's point is the in-memory track point for both formats: latitude, longitude, elevation.
TrackPoint = gpxpy.gpx.GPXTrackPoint


@dataclass
class RouteResult:
    track: dict  # GeoJSON Feature, LineString or MultiLineString WGS84, properties.km (below)
    length_km: float
    ascent_m: int | None  # None when the track has no elevations (P11)
    bbox: Bbox
    profile: list[tuple[float, float]]  # [cumulative km, elevation m]
    points: list[list[TrackPoint]]  # source points per segment, for route.gpx


def cumulative_m(coords: Coordinates, start_m: float = 0.0) -> list[float]:
    """Geodesic distance along the coordinates, in metres; one value per point, first = start."""
    lons = [lon for lon, _ in coords]
    lats = [lat for _, lat in coords]
    result = [start_m]
    for m in geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])[2]:
        result.append(result[-1] + m)
    return result


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


def _geojson_lines(obj: object) -> list[list[list[float]]]:
    """Every LineString of a GeoJSON object, MultiLineString parts and features flattened."""
    if not isinstance(obj, dict) or "type" not in obj:
        raise ValueError("not a GeoJSON object")
    kind = obj["type"]
    if kind == "FeatureCollection":
        return [line for f in obj.get("features", []) for line in _geojson_lines(f)]
    if kind == "Feature":
        return _geojson_lines(obj.get("geometry")) if obj.get("geometry") else []
    if kind == "LineString":
        return [obj["coordinates"]]
    if kind == "MultiLineString":
        return list(obj["coordinates"])
    raise ValueError(f"geometry {kind} is not a LineString or MultiLineString")


def _geojson_segments(text: str) -> list[list[TrackPoint]]:
    try:
        lines = _geojson_lines(json.loads(text))
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"GeoJSON: {e}") from e
    segments = []
    for line in lines:
        points = []
        for position in line:
            if not isinstance(position, list) or len(position) < 2:
                raise ValueError("GeoJSON: a position needs at least lon and lat")
            elevation = (
                float(position[2]) if len(position) > 2 and position[2] is not None else None
            )
            points.append(TrackPoint(float(position[1]), float(position[0]), elevation=elevation))
        segments.append(points)
    return segments


def _gpx_segments(text: str) -> list[list[TrackPoint]]:
    try:
        gpx = gpxpy.parse(text)
    except gpxpy.gpx.GPXException as e:
        raise ValueError(f"GPX: {e}") from e
    return [seg.points for trk in gpx.tracks for seg in trk.segments]


def parse_track(text: str, suffix: str) -> list[list[TrackPoint]]:
    """Track segments of a GPX (any other suffix) or GeoJSON (.geojson, .json) text.

    Segments with fewer than 2 points are dropped; ValueError when none is left or the text
    does not parse. The store validates uploads with this, the build reads files with read_track.
    """
    parse = _geojson_segments if suffix.lower() in GEOJSON_SUFFIXES else _gpx_segments
    segments = [points for points in parse(text) if len(points) >= 2]
    if not segments:
        raise ValueError("track has fewer than 2 points")
    return segments


def read_track(path: Path) -> list[list[TrackPoint]]:
    """Track segments of a GPX or GeoJSON file; BuildError when unreadable or too short."""
    try:
        return parse_track(path.read_text(encoding="utf-8"), path.suffix)
    except OSError as e:
        raise BuildError(f"{path}: {e.strerror}") from e
    except (UnicodeDecodeError, ValueError) as e:
        raise BuildError(f"{path}: {e}") from e


def _thin[T](points: list[T], at_most: int) -> list[T]:
    if len(points) <= at_most:
        return points
    last = len(points) - 1
    return [points[round(i * last / (at_most - 1))] for i in range(at_most)]


def process_route(directory: Path, route: Route) -> RouteResult:
    segments = read_track(directory / route.track)
    # Cumulative distance continues across segments without adding the gap between them:
    # the first point of a segment has the same km as the last point of the previous one.
    km_per_point: list[float] = []
    lines: list[Coordinates] = []
    # properties.km (7.11): cumulative km, 3 decimals, for every coordinate of the published
    # (simplified) geometry. LineString → one list aligned with `coordinates`; MultiLineString →
    # one list per part aligned with `coordinates[i]`, continuing across parts like length_km.
    km_per_coordinate: list[list[float]] = []
    line_m: list[float] = []
    for points in segments:
        coords = [(p.longitude, p.latitude) for p in points]
        km_per_point += cumulative_m(coords, km_per_point[-1] if km_per_point else 0.0)
        line = simplify(LineString(coords), 2)
        lines.append(line)
        line_m = cumulative_m(line, line_m[-1] if line_m else 0.0)
        km_per_coordinate.append([round(m / 1000, 3) for m in line_m])
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
        "properties": {
            "id": route.id,
            "km": km_per_coordinate[0] if len(lines) == 1 else km_per_coordinate,
        },
        "geometry": line_geometry(lines),
    }
    return RouteResult(
        track=track,
        length_km=round(km_per_point[-1] / 1000, 1),
        ascent_m=ascent_m,
        bbox=(round(min(lons), 4), round(min(lats), 4), round(max(lons), 4), round(max(lats), 4)),
        profile=profile,
        points=segments,
    )


def nearby_services(
    lines: list[Coordinates], services: list[Service], within_m: float
) -> list[tuple[Service, float]]:
    """Services within `within_m` of the track with their km, sorted by km (5.3)."""
    projector = TrackProjector(lines)
    found = []
    for service in services:
        distance, km = projector.project(service.location)
        if distance <= within_m:
            found.append((service, km))
    return sorted(found, key=lambda pair: pair[1])


def longest_gap(kms: list[float], length_km: float) -> ServiceGap:
    """The longest stretch between consecutive positions, the start (0) and the end included."""
    positions = sorted({0.0, length_km, *(min(max(km, 0.0), length_km) for km in kms)})
    start, end = max(pairwise(positions), key=lambda pair: pair[1] - pair[0])
    return ServiceGap(km=round(end - start, 1), start_km=round(start, 1), end_km=round(end, 1))


def _service_gaps(
    nearby: list[tuple[Service, float]], length_km: float, themes: list[Theme]
) -> tuple[dict[str, float] | None, dict[str, ServiceGap] | None]:
    """service_gaps per category and longest_service_gap per theme (7.11); None, None when no
    theme of the route lists service_categories_first."""
    first = {
        t.id: t.presentation.service_categories_first
        for t in themes
        if t.presentation and t.presentation.service_categories_first
    }
    if not first:
        return None, None
    kms_by_category: dict[str, list[float]] = {}
    for service, km in nearby:
        kms_by_category.setdefault(service.category, []).append(km)
    categories = list(dict.fromkeys(c for cs in first.values() for c in cs))
    gaps = {c: longest_gap(kms_by_category.get(c, []), length_km).km for c in categories}
    per_theme = {
        theme: longest_gap([km for c in cs for km in kms_by_category.get(c, [])], length_km)
        for theme, cs in first.items()
    }
    return gaps, per_theme


def published_route(
    route: Route,
    result: RouteResult,
    gpx_bytes: int,
    media: dict[str, PublishedMedia] | None = None,
    services: list[Service] | None = None,
    nearby_m: float = 500,
    themes: list[Theme] | None = None,
) -> PublishedRoute:
    """route.json: source card + computed fields (5.3, 7.11).

    `media` is the output of build/media.py. cover_image becomes the 400 px path relative to the
    data root; hardest_section.km is projected from the image location when the source has none.
    `services` is the merged list of build/services.py and `themes` the themes of the project:
    nearby services and the service gaps are computed only when the project has services (P11).
    """
    media = media or {}
    nearby = nearby_services(geometry_lines(result.track["geometry"]), services or [], nearby_m)
    route_themes = sorted((t for t in themes or [] if t.id in route.themes), key=lambda t: t.order)
    gaps, per_theme = (
        _service_gaps(nearby, result.length_km, route_themes) if services else (None, None)
    )
    cover = media.get(route.cover_image or "")
    cover_image = f"routes/{route.id}/{cover.sizes['400']}" if cover else None
    hardest = route.hardest_section
    hardest_image = None
    if hardest is not None:
        image = media.get(hardest.media)
        if image is not None:
            hardest_image = f"routes/{route.id}/{image.sizes['400']}"
        if hardest.km is None and image is not None and image.location is not None:
            lines = geometry_lines(result.track["geometry"])
            hardest = hardest.model_copy(
                update={"km": round(km_along_lines(lines, image.location), 1)}
            )
    segments = normalise(route.segments, result.length_km)
    surface_shares = shares(segments, result.length_km, "surface")
    traffic_shares = shares(segments, result.length_km, "traffic")
    return PublishedRoute(
        id=route.id,
        name=route.name,
        themes=route.themes,
        seasons=route.seasons,
        length_km=result.length_km,
        ascent_m=result.ascent_m,
        bbox=result.bbox,
        cover_image=cover_image,
        hardest_image=hardest_image,
        maintainer=route.maintainer,
        difficulty=route.difficulty,
        itrs=route.itrs,
        winter_maintenance=route.winter_maintenance,
        lipas_id=route.lipas_id,
        track="track.geojson",
        elevation_source=route.elevation_source,
        profile=result.profile,
        sections=route.sections,
        maintenance_url=route.maintenance_url,
        media=media,
        hardest_section=hardest,
        segments=segments,
        surface_shares=surface_shares,
        traffic_shares=traffic_shares,
        itrs_technical_shares=shares(segments, result.length_km, "itrs_technical"),
        dominant_surface=dominant(surface_shares),
        # 0.0 is a known share (traffic is known, none of it separated); None = not known.
        separated_share=traffic_shares.get("separated", 0.0) if traffic_shares else None,
        non_municipal_reasons=route.non_municipal_reasons,
        maintenance_note=route.maintenance_note,
        gpx="route.gpx",
        gpx_bytes=gpx_bytes,
        nearby_services=[NearbyService(id=s.id, km=round(km, 1)) for s, km in nearby],
        service_gaps=gaps,
        longest_service_gap=per_theme,
    )
