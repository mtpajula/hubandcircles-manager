"""Service point (chapter 5.5): one normalised model for every source, plus the manual marker.

Source files are GeoJSON FeatureCollections (services/osm.geojson, services/visitfinland.geojson,
services/manual.geojson); the feature properties are the model fields and the geometry the
location. The published services.geojson uses the same shape.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from manager.models.common import LangText
from manager.models.identifiers import ServiceCategory, ServiceSource

Location = tuple[float, float]  # WGS84 (lon, lat)


class Service(BaseModel):
    """`source:original_id`; a name is absent when the source has none (P11)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: LangText | None = None
    category: ServiceCategory
    source: ServiceSource
    url: str | None = None
    opening_hours: str | None = None
    description: LangText | None = None
    fetched_at: str | None = None  # ISO UTC timestamp of the snapshot
    location: Location
    # Issue fields (category `issue`); an expired `valid_until` drops the point in the build.
    severity: str | None = None
    reported_at: str | None = None
    valid_until: str | None = None  # ISO date
    report: str | None = None  # e.g. "github#42"

    @classmethod
    def from_feature(cls, feature: dict[str, Any]) -> "Service":
        return cls.model_validate({**feature["properties"], "location": _location(feature)})

    def to_feature(self) -> dict[str, Any]:
        properties = self.model_dump(mode="json", exclude_none=True, exclude={"location"})
        return {
            "type": "Feature",
            "properties": properties,
            "geometry": {"type": "Point", "coordinates": list(self.location)},
        }


class ManualMarker(BaseModel):
    """A row of services/manual.geojson (5.5): a new point (`id` starts with `manual:`), a
    correction (`replaces` and the changed fields) or a hiding (`replaces` and `hidden`)."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: LangText | None = None
    category: ServiceCategory | None = None
    source: Literal["manual"] = "manual"
    url: str | None = None
    opening_hours: str | None = None
    description: LangText | None = None
    fetched_at: str | None = None
    location: Location | None = None
    severity: str | None = None
    reported_at: str | None = None
    valid_until: str | None = None
    report: str | None = None
    replaces: str | None = None
    hidden: bool = False

    @classmethod
    def from_feature(cls, feature: dict[str, Any]) -> "ManualMarker":
        properties = dict(feature["properties"])
        if feature.get("geometry"):
            properties["location"] = _location(feature)
        return cls.model_validate(properties)

    def overrides(self) -> dict[str, Any]:
        """The fields a correction sets on its target: what was given, minus the marker keys.
        The target keeps its id and source."""
        return self.model_dump(exclude_unset=True, exclude={"id", "replaces", "hidden", "source"})


def _location(feature: dict[str, Any]) -> Location:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") != "Point":
        raise ValueError(
            f"service {feature.get('properties', {}).get('id')!r}: geometry not a Point"
        )
    lon, lat, *_ = geometry["coordinates"]
    return (float(lon), float(lat))
