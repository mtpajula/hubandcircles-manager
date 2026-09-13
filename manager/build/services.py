"""Build stage: services. Merge the sources, apply manual markers, drop duplicates (5.5, 7.2).

Priority manual > visitfinland > osm. Two points are the same when they lie within
DUPLICATE_M of each other and their normalised names are similar enough (or one has none).
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from difflib import SequenceMatcher

from pydantic import ValidationError
from pyproj import Geod

from manager.models import ManualMarker, Service
from manager.validate.manual_markers import marker_warnings, new_service

DUPLICATE_M = 50
NAME_SIMILARITY = 0.8
NEAR_DEG = 0.002  # about 220 m of latitude; a cheap pre-check before the geodesic distance

geod = Geod(ellps="WGS84")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)


@dataclass
class MergeResult:
    services: list[Service]
    warnings: list[str] = field(default_factory=list)


def normalised_name(service: Service) -> str:
    """Casefolded, punctuation stripped, whitespace collapsed; '' without a name."""
    if not service.name:
        return ""
    text = service.name.get("fi") or next(iter(service.name.values()))
    return " ".join(_PUNCTUATION.sub(" ", text.casefold()).split())


def same_place(a: Service, b: Service) -> bool:
    (lon_a, lat_a), (lon_b, lat_b) = a.location, b.location
    if abs(lat_a - lat_b) > NEAR_DEG or abs(lon_a - lon_b) > NEAR_DEG * 3:
        return False
    if geod.inv(lon_a, lat_a, lon_b, lat_b)[2] > DUPLICATE_M:
        return False
    name_a, name_b = normalised_name(a), normalised_name(b)
    if not name_a or not name_b:
        return True
    return SequenceMatcher(None, name_a, name_b).ratio() >= NAME_SIMILARITY


def _expired(service: Service, today: date) -> bool:
    if service.valid_until is None:
        return False
    try:
        return date.fromisoformat(service.valid_until) < today
    except ValueError:
        return False  # the schema check names the bad date; nothing is hidden silently here


def merge(
    osm: list[Service],
    visitfinland: list[Service],
    manual: list[ManualMarker],
    today: date | None = None,
) -> MergeResult:
    """Merged service list in priority order manual > visitfinland > osm."""
    today = today or datetime.now(UTC).date()
    fetched = {s.id: s for s in [*visitfinland, *osm]}
    warnings = marker_warnings(manual, set(fetched))
    new: list[Service] = []
    for marker in manual:
        if marker.replaces is None:
            try:
                new.append(new_service(marker))
            except ValidationError:
                continue  # already in the warnings
        elif marker.replaces in fetched:
            if marker.hidden:
                del fetched[marker.replaces]
            else:
                target = fetched[marker.replaces]
                fetched[marker.replaces] = target.model_copy(update=marker.overrides())
    ranked = [*new, *(fetched[s.id] for s in visitfinland if s.id in fetched)]
    ranked += [fetched[s.id] for s in osm if s.id in fetched]
    kept: list[Service] = []
    for service in ranked:
        if _expired(service, today) or any(same_place(service, k) for k in kept):
            continue
        kept.append(service)
    return MergeResult(kept, warnings)


def services_collection(services: list[Service]) -> dict:
    """The published services.geojson (chapter 6)."""
    return {"type": "FeatureCollection", "features": [s.to_feature() for s in services]}
