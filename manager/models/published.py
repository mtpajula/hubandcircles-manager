"""Published data (dist/): routes/<id>/route.json and catalog.json, chapters 5.3 and 5.6."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from manager.models.common import Bbox, LangText
from manager.models.project import Feedback
from manager.models.route import Maintainer, Section
from manager.models.theme import Theme


class RouteSummary(BaseModel):
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


class PublishedMedia(BaseModel):
    model_config = ConfigDict(extra="ignore")

    author: str
    license: str
    sizes: dict[str, str] = {}
    location: tuple[float, float] | None = None


class PublishedRoute(RouteSummary):
    difficulty: str | None = None
    lipas_id: int | None = None
    track: str
    profile: list[tuple[float, float]]
    sections: list[Section]
    nearby_services: list[str] = []
    media: dict[str, PublishedMedia] = {}


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
