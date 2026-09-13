"""Published data (dist/): routes/<id>/route.json and catalog.json, chapters 5.3 and 5.6."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from manager.models.common import Bbox, LangText
from manager.models.identifiers import (
    Difficulty,
    Maintainer,
    NonMunicipalReason,
    WinterMaintenance,
)
from manager.models.project import Feedback
from manager.models.route import HardestSection, Itrs, Section, Segment
from manager.models.theme import Theme


class RouteSummary(BaseModel):
    """The route as listed in catalog.json: what the list card and the filters need (5.6)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: LangText
    themes: list[str]
    seasons: list[str]
    length_km: float
    ascent_m: int | None = None  # None when the track has no elevations (P11)
    bbox: Bbox
    cover_image: str | None = None
    maintainer: Maintainer | None = None
    difficulty: Difficulty | None = None
    itrs: Itrs | None = None
    winter_maintenance: WinterMaintenance | None = None
    # Computed in build/segments.py (7.11); None when the route has no segments (P11).
    dominant_surface: str | None = None  # a surface, `mixed`, or None without segments
    separated_share: float | None = None
    surface_shares: dict[str, float] | None = None


class PublishedMedia(BaseModel):
    """An image of the route (5.3): the WebP sizes and what the EXIF said, keyed by source path."""

    model_config = ConfigDict(extra="ignore")

    author: str
    license: str
    sizes: dict[str, str] = {}  # width → path relative to the route directory ("media/...webp")
    location: tuple[float, float] | None = None  # WGS84 (lon, lat) from the EXIF, else None
    taken_at: str | None = None  # ISO date from the EXIF, else None


class PublishedSegment(Segment):
    """Normalised segment (5.3): a gap is a segment whose attributes are all None."""

    model_config = ConfigDict(extra="ignore")


class PublishedRoute(RouteSummary):
    """route.json (5.3). Media rule: `cover_image` is a ready path relative to the data root
    (`routes/<id>/media/cover-<hash>-400.webp`); everything else (`hardest_section.media`, gallery
    `media` entries) is a source key into `media`, where the sizes and the location are."""

    lipas_id: int | None = None
    track: str
    profile: list[tuple[float, float]]
    sections: list[Section]
    nearby_services: list[str] = []
    media: dict[str, PublishedMedia] = {}
    maintenance_url: str | None = None
    hardest_section: HardestSection | None = None
    segments: list[PublishedSegment] = []
    non_municipal_reasons: list[NonMunicipalReason] = []
    maintenance_note: LangText | None = None
    # Computed in build/segments.py and build/gpx.py (7.11).
    traffic_shares: dict[str, float] | None = None
    itrs_technical_shares: dict[str, float] | None = None
    gpx: str | None = None
    gpx_bytes: int | None = None


class CatalogProject(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: LangText
    subtitle: LangText
    area: Bbox | None = None  # project bounding box for the initial map view
    languages: list[str]
    default_language: str
    default_theme: str
    feedback: Feedback | None = None


class Catalog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[1] = 1
    generated_at: str
    project: CatalogProject
    themes: list[Theme]
    layers: list[dict] = []  # ponytail: layer card is modelled in V3
    routes: list[RouteSummary]
    overview: str
    services: str | None = None
    coverage: dict[str, str] = {}
