"""OSM via Overpass: the automatic main source of service points (chapter 7.6).

fetch() is the only function that touches the network; the rest is pure and tested offline.
The snapshot services/osm.geojson is written only after the result is parsed (SKILL: no data
loss); the Streamlit page lets the editor accept it, the CLI writes it directly.
"""

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from manager.build import write_json
from manager.build.read import read_features
from manager.build.services import services_collection
from manager.models import Bbox, Service

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "hubandcircles-manager"

# The fixed tag table of 7.6: (key, value) -> category. amenity=shelter needs
# shelter_type=lean_to (below); tourism=picnic_site is queried but has no category, so skipped.
TAG_CATEGORIES: dict[tuple[str, str], str] = {
    ("amenity", "cafe"): "cafe",
    ("amenity", "restaurant"): "restaurant",
    ("amenity", "fast_food"): "restaurant",
    ("amenity", "drinking_water"): "water",
    ("amenity", "toilets"): "toilet",
    ("amenity", "bicycle_repair_station"): "bike_repair",
    ("shop", "bicycle"): "bike_repair",
    ("shop", "supermarket"): "shop",
    ("shop", "convenience"): "shop",
    ("tourism", "wilderness_hut"): "hut",
    ("tourism", "camp_site"): "accommodation",
    ("tourism", "hotel"): "accommodation",
    ("tourism", "guest_house"): "accommodation",
}
QUERIED_TAGS = {
    "amenity": (
        "cafe",
        "restaurant",
        "fast_food",
        "drinking_water",
        "toilets",
        "shelter",
        "bicycle_repair_station",
    ),
    "shop": ("bicycle", "supermarket", "convenience"),
    "tourism": ("wilderness_hut", "camp_site", "picnic_site", "hotel", "guest_house"),
}


def query(area: Bbox) -> str:
    """Overpass QL of 7.6 for a WGS84 lon/lat bbox; Overpass wants south, west, north, east."""
    lon_min, lat_min, lon_max, lat_max = area
    bbox = f"({lat_min},{lon_min},{lat_max},{lon_max})"
    lines = [
        f'  nwr["{key}"~"^({"|".join(values)})$"]{bbox};' for key, values in QUERIED_TAGS.items()
    ]
    return "[out:json][timeout:90];\n(\n" + "\n".join(lines) + "\n);\nout center tags;\n"


def fetch(area: Bbox, *, base_url: str = OVERPASS_URL, timeout_s: int = 120) -> list[dict]:
    """Raw Overpass elements (`elements` of the JSON answer) for the area."""
    request = urllib.request.Request(
        base_url,
        data=query(area).encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Content-Type": "text/plain; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.load(response)["elements"]


def category(tags: dict[str, str]) -> str | None:
    """Category of the tag table, or None when the element is not a service point."""
    if tags.get("amenity") == "shelter":
        return "lean_to" if tags.get("shelter_type") == "lean_to" else None
    for key in QUERIED_TAGS:
        if (key, tags.get(key, "")) in TAG_CATEGORIES:
            return TAG_CATEGORIES[key, tags[key]]
    return None


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _service(element: dict, fetched_at: str) -> Service | None:
    tags = element.get("tags") or {}
    kind = category(tags)
    if kind is None:
        return None
    # Nodes carry lon/lat; ways and relations the centre asked for with `out center`.
    position = element if "lon" in element else element.get("center")
    if not position:
        return None
    name = {
        lang: text
        for lang, text in (("fi", _text(tags.get("name"))), ("en", _text(tags.get("name:en"))))
        if text
    }
    return Service(
        id=f"osm:{element['type']}/{element['id']}",
        name=name or None,
        category=kind,
        source="osm",
        url=_text(tags.get("website")) or _text(tags.get("contact:website")),
        opening_hours=_text(tags.get("opening_hours")),
        fetched_at=fetched_at,
        location=(round(float(position["lon"]), 6), round(float(position["lat"]), 6)),
    )


def parse(elements: list[dict], fetched_at: str | None = None) -> list[Service]:
    """Elements → services of the tag table, sorted by id. Elements without a category or a
    position are left out."""
    fetched_at = fetched_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    services = (_service(e, fetched_at) for e in elements)
    return sorted((s for s in services if s is not None), key=lambda s: s.id)


def snapshot_path(data_dir: Path) -> Path:
    return data_dir / "services" / "osm.geojson"


def write_snapshot(data_dir: Path, services: list[Service]) -> Path:
    path = snapshot_path(data_dir)
    write_json(path, services_collection(services))
    return path


def read_snapshot(data_dir: Path) -> list[Service]:
    """The services of services/osm.geojson; empty without a snapshot."""
    return read_features(snapshot_path(data_dir), Service)


@dataclass
class Diff:
    added: list[Service] = field(default_factory=list)
    removed: list[Service] = field(default_factory=list)
    changed: list[Service] = field(default_factory=list)  # the new version
    unchanged: list[Service] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"added {len(self.added)}, removed {len(self.removed)}, changed {len(self.changed)},"
            f" unchanged {len(self.unchanged)}"
        )


def _content(service: Service) -> dict:
    return service.model_dump(exclude={"fetched_at"})


def diff(old: list[Service], new: list[Service]) -> Diff:
    """Change view against the previous snapshot by id (7.6); fetched_at does not count."""
    before = {s.id: s for s in old}
    result = Diff(removed=[s for s in old if s.id not in {n.id for n in new}])
    for service in new:
        previous = before.get(service.id)
        if previous is None:
            result.added.append(service)
        elif _content(previous) != _content(service):
            result.changed.append(service)
        else:
            result.unchanged.append(service)
    return result
