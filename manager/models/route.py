"""Route card, source data (routes/<id>/route.json), chapter 5.3."""

from datetime import date
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ModelWrapValidatorHandler,
    PrivateAttr,
    model_validator,
)

from manager.models.common import LangText
from manager.models.identifiers import (
    Difficulty,
    ItrsLevel,
    Maintainer,
    NonMunicipalReason,
    Season,
    Surface,
    Traffic,
    WinterMaintenance,
)


class TextSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text"]
    content: LangText


class GallerySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["gallery"]
    media: list[str]


class VideoSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["video"]
    url: str


class ElevationProfileSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["elevation_profile"]


Section = Annotated[
    TextSection | GallerySection | VideoSection | ElevationProfileSection,
    Field(discriminator="type"),
]


class MediaInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str
    license: str


class Itrs(BaseModel):
    """ITRS assessment of the whole route (5.3). Every sub-field is optional (P11)."""

    model_config = ConfigDict(extra="forbid")

    technical: ItrsLevel | None = None
    endurance: ItrsLevel | None = None
    # Scales are in project.itrs_scales; 1...max is checked in validate (7.2, ITRS values).
    exposure: int | None = Field(default=None, gt=0)
    wilderness: int | None = Field(default=None, gt=0)
    assessed_by: str | None = None
    assessed_on: date | None = None


class HardestSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media: str  # key of route.media or a file under the route directory; checked in validate
    km: float | None = None  # when None, the build projects the image EXIF location (7.11)
    description: LangText | None = None


class Segment(BaseModel):
    """Part of the route in km (5.3). A missing attribute is unknown for that part."""

    model_config = ConfigDict(extra="forbid")

    start_km: float
    end_km: float
    surface: Surface | None = None
    traffic: Traffic | None = None
    itrs_technical: ItrsLevel | None = None


# Old difficulty values, normalised when the card is read (5.3); the build reports it as info.
LEGACY_DIFFICULTY = {
    "helppo": "easy",
    "keskivaikea": "moderate",
    "keskivaativa": "moderate",
    "vaativa": "demanding",
}


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: LangText
    themes: list[str]
    seasons: list[Season]
    # None = not assessed (P11); an imported route starts without one.
    difficulty: Difficulty | None = None
    track: str = "track.gpx"
    cover_image: str | None = None
    itrs: Itrs | None = None
    winter_maintenance: WinterMaintenance | None = None
    maintenance_url: str | None = None
    hardest_section: HardestSection | None = None
    segments: list[Segment] = []
    sections: list[Section] = []
    media: dict[str, MediaInfo] = {}
    lipas_id: int | None = None  # Lipas sports facility id (properties.id), chapter 7.13
    maintainer: Maintainer | None = None  # None = unknown, no marker shown (AP24)
    non_municipal_reasons: list[NonMunicipalReason] = []
    maintenance_note: LangText | None = None

    # Names of the fields whose legacy value was normalised while reading; not part of the data.
    _normalised_fields: list[str] = PrivateAttr(default_factory=list)

    @property
    def normalised_fields(self) -> list[str]:
        return self._normalised_fields

    def media_paths(self) -> set[str]:
        """Every image path of the card: media keys, cover, hardest section and galleries."""
        paths = set(self.media)
        if self.cover_image:
            paths.add(self.cover_image)
        if self.hardest_section:
            paths.add(self.hardest_section.media)
        for section in self.sections:
            if isinstance(section, GallerySection):
                paths.update(section.media)
        return paths

    @model_validator(mode="wrap")
    @classmethod
    def _normalise_legacy_values(cls, data: Any, handler: ModelWrapValidatorHandler["Route"]):
        normalised = []
        if isinstance(data, dict) and data.get("difficulty") in LEGACY_DIFFICULTY:
            data = {**data, "difficulty": LEGACY_DIFFICULTY[data["difficulty"]]}
            normalised.append("difficulty")
        route = handler(data)
        route._normalised_fields = normalised
        return route
