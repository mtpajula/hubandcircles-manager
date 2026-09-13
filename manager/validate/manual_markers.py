"""Check: manual markers make sense (7.2, 'Manual markers', warning): a correction or a hiding
targets a service that still exists, and a new point has what a service needs.

The warnings are also what build/services.py returns from merge(); one place for both."""

from typing import TYPE_CHECKING

from pydantic import ValidationError

from manager.models import ManualMarker, Service
from manager.validate.finding import Finding

if TYPE_CHECKING:
    from manager.build.read import SourceData

MARKER_KEYS = {"replaces", "hidden"}


def new_service(marker: ManualMarker) -> Service:
    """A new manual point as a service; ValidationError when a required field is missing."""
    return Service.model_validate(marker.model_dump(exclude_none=True, exclude=MARKER_KEYS))


def marker_warnings(markers: list[ManualMarker], ids: set[str]) -> list[str]:
    """Corrections and hidings whose target is not in the snapshots, and new points that do not
    make a service (7.2, 'Manual markers', warning)."""
    warnings = []
    for m in markers:
        label = f"manual marker {m.id or '(no id)'}"
        if m.replaces is not None:
            if m.replaces not in ids:
                warnings.append(f"{label}: replaces {m.replaces!r}, which no longer exists")
            continue
        try:
            new_service(m)
        except ValidationError as e:
            problems = "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            warnings.append(f"{label}: {problems}")
    return warnings


def check_manual_markers(source: "SourceData") -> list[Finding]:
    ids = {s.id for s in [*source.osm_services, *source.visitfinland_services]}
    return [Finding("warning", message) for message in marker_warnings(source.manual_markers, ids)]
