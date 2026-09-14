"""Lipas: the municipal sports facility register as a WFS 2.0 GeoServer (chapter 7.13).

fetch() is the only function that touches the network; the rest is pure and tested offline.
"""

import json
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import gpxpy.gpx

from manager.build import write_json
from manager.build.projection import to_deg, to_m
from manager.http import ssl_context
from manager.models import Route, TextSection
from manager.slug import MAX_ID_LENGTH, slugify  # noqa: F401  (re-exported for callers)

# The only http:// source in the project: Lipas serves WFS over plain HTTP. No keys or
# secrets are sent, and the result is public data checked by the editor before use (7.13).
LIPAS_WFS_URL = "http://lipas.cc.jyu.fi/geoserver/wfs"

# Lipas type code -> WFS layer name suffix (lipas:lipas_<code>_<layer>).
LAYERS = {4411: "maastopyorailyreitti", 4412: "pyorailyreitti"}

# Lipas property names (Finnish, as served) -> our English names. The only place where the
# Finnish data keys appear; everything downstream uses the English names.
PROPERTY_KEYS = {
    "lipas_id": "id",
    "name_fi": "nimi_fi",
    "name_en": "nimi_en",
    "type_code": "tyyppikoodi",
    "surface": "pintamateriaali",
    "length_km": "reitin_pituus_km",
    "owner": "omistaja",
    "maintainer": "yllapitaja",
    "www": "www",
    "note": "lisatieto_fi",
    "modified": "muokattu_viimeksi",
}

GRAVEL_SURFACE = "Sora"  # Lipas surface value meaning gravel
TOURING_MIN_KM = 150

Point = tuple[float, float]


@dataclass
class LipasRoute:
    lipas_id: int
    name_fi: str
    name_en: str | None
    type_code: int
    surface: str | None
    length_km: float | None
    owner: str | None
    maintainer: str | None
    www: str | None
    note: str | None
    modified: str | None
    parts: list[list[Point]]  # EPSG:3067 coordinates as served


def fetch(
    bbox_3067: tuple[float, float, float, float],
    type_codes: Iterable[int] = (4411, 4412),
    *,
    base_url: str = LIPAS_WFS_URL,
    timeout_s: int = 120,
) -> list[dict]:
    """Raw GeoJSON features of every layer intersecting the bbox; one GetFeature per type."""
    features: list[dict] = []
    for code in type_codes:
        if code not in LAYERS:
            raise ValueError(f"unknown Lipas type code {code}; known: {sorted(LAYERS)}")
        query = urllib.parse.urlencode(
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": f"lipas:lipas_{code}_{LAYERS[code]}",
                "outputFormat": "application/json",
                "bbox": ",".join(str(v) for v in bbox_3067) + ",EPSG:3067",
            }
        )
        with urllib.request.urlopen(
            f"{base_url}?{query}", timeout=timeout_s, context=ssl_context()
        ) as response:
            features += json.load(response)["features"]
    return features


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _number(value: object) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def group(features: list[dict]) -> list[LipasRoute]:
    """One LipasRoute per Lipas id; the line parts keep the order they were served in."""
    routes: dict[int, LipasRoute] = {}
    for feature in features:
        p = feature["properties"]
        lipas_id = int(p[PROPERTY_KEYS["lipas_id"]])
        if lipas_id not in routes:
            routes[lipas_id] = LipasRoute(
                lipas_id=lipas_id,
                name_fi=str(p[PROPERTY_KEYS["name_fi"]]),
                name_en=_text(p.get(PROPERTY_KEYS["name_en"])),
                type_code=int(p[PROPERTY_KEYS["type_code"]]),
                surface=_text(p.get(PROPERTY_KEYS["surface"])),
                length_km=_number(p.get(PROPERTY_KEYS["length_km"])),
                owner=_text(p.get(PROPERTY_KEYS["owner"])),
                maintainer=_text(p.get(PROPERTY_KEYS["maintainer"])),
                www=_text(p.get(PROPERTY_KEYS["www"])),
                note=_text(p.get(PROPERTY_KEYS["note"])),
                modified=_text(p.get(PROPERTY_KEYS["modified"])),
                parts=[],
            )
        geometry = feature["geometry"]
        lines = (
            [geometry["coordinates"]]
            if geometry["type"] == "LineString"
            else geometry["coordinates"]
        )
        routes[lipas_id].parts += [[(x, y) for x, y, *_ in line] for line in lines]
    return list(routes.values())


def _wgs84_parts(route: LipasRoute) -> list[list[Point]]:
    return [
        [(round(lon, 6), round(lat, 6)) for lon, lat in (to_deg(x, y) for x, y in part)]
        for part in route.parts
    ]


def snapshot(routes: list[LipasRoute]) -> dict:
    """GeoJSON FeatureCollection in WGS84, one MultiLineString feature per Lipas route."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {key: getattr(r, key) for key in PROPERTY_KEYS},
                "geometry": {"type": "MultiLineString", "coordinates": _wgs84_parts(r)},
            }
            for r in routes
        ],
    }


def snapshot_path(data_dir: Path) -> Path:
    return data_dir / "sources" / "lipas.geojson"


def write_snapshot(data_dir: Path, routes: list[LipasRoute]) -> Path:
    path = snapshot_path(data_dir)
    write_json(path, snapshot(routes))
    return path


def read_snapshot(data_dir: Path) -> list[LipasRoute]:
    """Inverse of write_snapshot: the routes of sources/lipas.geojson, parts back in EPSG:3067."""
    collection = json.loads(snapshot_path(data_dir).read_text(encoding="utf-8"))
    return [
        LipasRoute(
            **feature["properties"],
            parts=[
                [to_m(lon, lat) for lon, lat in part] for part in feature["geometry"]["coordinates"]
            ],
        )
        for feature in collection["features"]
    ]


def _themes(route: LipasRoute) -> list[str]:
    # A proposal for the editor (7.13): the editor changes the themes in route.json.
    if route.type_code == 4411:
        return ["mtb"]
    themes = ["gravel" if GRAVEL_SURFACE in (route.surface or "") else "road"]
    if route.length_km is not None and route.length_km > TOURING_MIN_KM:
        themes.append("touring")
    return themes


def _gpx(route: LipasRoute) -> str:
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name=route.name_en or route.name_fi)
    gpx.tracks.append(track)
    for part in _wgs84_parts(route):
        segment = gpxpy.gpx.GPXTrackSegment()
        segment.points = [gpxpy.gpx.GPXTrackPoint(lat, lon) for lon, lat in part]
        track.segments.append(segment)
    return gpx.to_xml()


def to_route(route: LipasRoute) -> tuple[Route, str]:
    """Source route card and GPX text (WGS84, one segment per part, no elevations)."""
    name = {"fi": route.name_fi}
    if route.name_en:
        name["en"] = route.name_en
    card = Route(
        id=slugify(route.name_en or route.name_fi),
        name=name,
        themes=_themes(route),
        seasons=["summer"],
        sections=[TextSection(type="text", content={"fi": route.note})] if route.note else [],
        lipas_id=route.lipas_id,
        # Being in the municipal register is the definition of "municipal" (5.3, AP24).
        maintainer="municipal",
    )
    return card, _gpx(route)


def import_routes(data_dir: Path, routes: list[LipasRoute]) -> list[str]:
    """Create routes/<id>/{route.json,track.gpx}; never overwrites an existing directory."""
    lines = []
    used: set[str] = set()
    for lipas_route in routes:
        card, gpx_text = to_route(lipas_route)
        if card.id in used:
            card.id = f"{card.id}-{lipas_route.lipas_id}"
        used.add(card.id)
        directory = data_dir / "routes" / card.id
        if directory.exists():
            lines.append(f"skipped {card.id}: exists")
            continue
        write_json(directory / "route.json", card.model_dump(mode="json", exclude_none=True))
        (directory / "track.gpx").write_text(gpx_text, encoding="utf-8")
        lines.append(f"created {card.id}")
    return lines


def bbox_to_3067(area: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """WGS84 lon/lat bbox -> EPSG:3067 bbox covering all four transformed corners."""
    lon_min, lat_min, lon_max, lat_max = area
    corners = [to_m(lon, lat) for lon in (lon_min, lon_max) for lat in (lat_min, lat_max)]
    xs, ys = zip(*corners)
    return (min(xs), min(ys), max(xs), max(ys))
