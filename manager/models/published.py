"""Published data (dist/): routes/<id>/route.json and catalog.json, chapters 5.3 and 5.6."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from manager.models.common import Bbox, LangText
from manager.models.identifiers import (
    Difficulty,
    LayerSlot,
    LayerType,
    Maintainer,
    NonMunicipalReason,
    WinterMaintenance,
)
from manager.models.layer import LegendEntry, VectorStyle, VisibleIn, Wms
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
    # The hardest section's 400 px image as a data-root path, so the list can honour a theme
    # whose presentation.hero_image is `hardest_section` (5.6); None without one (P11).
    hardest_image: str | None = None
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


class NearbyService(BaseModel):
    """A service point within `nearby_services_m` of the track, at its km (5.3)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    km: float


class ServiceGap(BaseModel):
    """The longest stretch without a service of the theme's first categories (7.11)."""

    model_config = ConfigDict(extra="ignore")

    km: float
    start_km: float
    end_km: float


class PublishedRoute(RouteSummary):
    """route.json (5.3). Media rule: `cover_image` is a ready path relative to the data root
    (`routes/<id>/media/cover-<hash>-400.webp`); everything else (`hardest_section.media`, gallery
    `media` entries) is a source key into `media`, where the sizes and the location are."""

    lipas_id: int | None = None
    track: str
    profile: list[tuple[float, float]]
    sections: list[Section]
    nearby_services: list[NearbyService] = []
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
    # Computed in build/routes.py from the merged services (7.11); absent without services or
    # without a theme that lists service_categories_first (P11).
    service_gaps: dict[str, float] | None = None  # category -> longest gap km
    longest_service_gap: dict[str, ServiceGap] | None = None  # theme id -> gap


class PublishedLayer(BaseModel):
    """A layer as listed in catalog.json (5.4): the frontend side of the card. `source` and
    `publish_format` are gone; `type`, `url`, `legend` and `fetched_at` come from the build."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: LangText
    slot: LayerSlot
    type: LayerType
    url: str  # external address or template, or a path relative to the data root
    wms: Wms | None = None
    visible_in: VisibleIn
    default_on: bool = False
    minzoom: int | None = None
    maxzoom: int | None = None
    opacity: float | None = None
    attribution: str
    fetched_at: str | None = None  # ISO UTC timestamp of the newest source snapshot
    legend: list[LegendEntry] = []
    style: VectorStyle | None = None
    maplibre: dict | None = None


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
    layers: list[PublishedLayer] = []
    routes: list[RouteSummary]
    overview: str
    services: str | None = None
    coverage: dict[str, str] = {}  # ponytail: layer id -> coverage GeoJSON, filled in V4b
